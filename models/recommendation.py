"""
models/recommendation.py
Content-based recommendation engine for electronic components using TF-IDF and Cosine Similarity.
Enforces functional diversity to suggest multiple distinct sensor/module types
without duplicate components of the same kind.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import joblib
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from models.taxonomy import get_functional_kind, get_functional_kind_label

MODELS_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


class ComponentRecommender:
    def __init__(self):
        self.vectorizer = None
        self.tfidf_matrix = None
        self.components_df = None

    def fit(self, components_df=None):
        if components_df is None:
            csv_path = os.path.join(DATA_DIR, "components.csv")
            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"{csv_path} does not exist.")
            self.components_df = pd.read_csv(csv_path)
        else:
            self.components_df = components_df.copy()

        # Weighted corpus gives primary emphasis to name, keywords, and project applications
        self.components_df["corpus_text"] = (
            (self.components_df["name"].fillna("") + " ") * 4 +
            (self.components_df["tags"].fillna("") + " ") * 3 +
            (self.components_df["applications"].fillna("") + " ") * 3 +
            (self.components_df["category"].fillna("") + " ") * 2 +
            (self.components_df["subcategory"].fillna("") + " ") * 2 +
            self.components_df["interfaces"].fillna("") + " " +
            self.components_df["description"].fillna("")
        )

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=6000,
            sublinear_tf=True
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.components_df["corpus_text"])
        return self

    def save(self, filepath=None):
        if filepath is None:
            filepath = os.path.join(MODELS_DIR, "recommendation_model.pkl")
        joblib.dump({
            "vectorizer": self.vectorizer,
            "tfidf_matrix": self.tfidf_matrix,
            "components_df": self.components_df
        }, filepath)
        print(f"Recommendation model saved to {filepath}")

    @classmethod
    def load(cls, filepath=None):
        if filepath is None:
            filepath = os.path.join(MODELS_DIR, "recommendation_model.pkl")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"{filepath} not found. Please train model first.")
        data = joblib.load(filepath)
        rec = cls()
        rec.vectorizer = data["vectorizer"]
        rec.tfidf_matrix = data["tfidf_matrix"]
        rec.components_df = data["components_df"]
        return rec

    def recommend(self, query, platform=None, budget=None, existing_parts=None, top_n=6):
        """
        Ranks and returns the most relevant components for a student project.
        Enforces functional diversity so recommendations include multiple complementary sensors
        and peripherals, with NO redundant sensors of the exact same kind.
        """
        if self.vectorizer is None or self.tfidf_matrix is None:
            raise RuntimeError("Recommender model is not fitted or loaded.")

        clean_query = query.strip() if query else "sensor microcontroller display"

        # Transform query into TF-IDF vector
        query_vec = self.vectorizer.transform([clean_query])
        raw_similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Parse existing parts to avoid duplicate recommendations
        existing_ids = set()
        existing_kinds = set()
        if existing_parts:
            if isinstance(existing_parts, str):
                parts_list = [p.strip().lower() for p in existing_parts.split(",") if p.strip()]
            else:
                parts_list = [str(p).strip().lower() for p in existing_parts]
            for p in parts_list:
                matched = self.components_df[
                    (self.components_df["component_id"].str.lower() == p) |
                    (self.components_df["name"].str.lower().str.contains(p, regex=False))
                ]["component_id"].tolist()
                existing_ids.update(matched)
                existing_ids.add(p)
                for m in matched:
                    k = get_functional_kind(m)
                    if k != "other":
                        existing_kinds.add(k)

        # Build scored candidate list
        candidates = []
        max_raw_sim = max(raw_similarities) if len(raw_similarities) > 0 and max(raw_similarities) > 0 else 1.0

        for idx, row in self.components_df.iterrows():
            cid = row["component_id"]
            if cid in existing_ids:
                continue

            raw_sim = float(raw_similarities[idx])
            cat = row["category"]

            # Filter out other MCUs if a platform MCU is already chosen
            if platform and platform.lower() != "any":
                if cat in ["Microcontroller", "Single Board Computer"]:
                    continue

                # Platform compatibility check
                plat_str = str(row["compatible_platforms"]).lower()
                is_plat_compat = ("universal" in plat_str or platform.lower() in plat_str)
                if not is_plat_compat:
                    raw_sim *= 0.5

            norm_sim = raw_sim / max_raw_sim
            match_pct = int(np.clip(norm_sim * 35 + 60, 50, 96))

            price = float(row.get("price_inr", 0))
            within_budget = True if budget is None or budget <= 0 else (price <= budget)

            func_kind = get_functional_kind(cid)
            func_label = get_functional_kind_label(cid)

            candidates.append({
                "component_id": cid,
                "name": row["name"],
                "category": cat,
                "subcategory": row["subcategory"],
                "functional_kind": func_kind,
                "functional_kind_label": func_label,
                "raw_sim": raw_sim,
                "match_percentage": match_pct,
                "operating_voltage": f"{row['operating_voltage_min']} - {row['operating_voltage_max']}V",
                "logic_voltage": f"{row['logic_voltage']}V",
                "interfaces": row["interfaces"],
                "price_inr": int(price),
                "within_budget": within_budget,
                "description": row["description"],
                "applications": row["applications"],
                "recommended_because": row["recommended_because"]
            })

        # Sort candidates by raw similarity score descending
        candidates.sort(key=lambda x: x["raw_sim"], reverse=True)

        query_lower = clean_query.lower()
        wants_display = any(w in query_lower for w in ["display", "screen", "oled", "lcd", "tft", "show", "readout"])
        wants_actuator = any(w in query_lower for w in ["motor", "servo", "relay", "valve", "stepper", "pump", "drive"])

        balanced_results = []
        seen_kinds = set(existing_kinds)

        # 1. Best overall functional match
        for i, c in enumerate(candidates):
            k = c["functional_kind"]
            if k not in seen_kinds or k == "other":
                balanced_results.append(candidates.pop(i))
                if k != "other":
                    seen_kinds.add(k)
                break

        # 2. If display requested and not yet included, select highest-ranking display of a new kind
        if wants_display and not any(r["category"] == "Display" for r in balanced_results):
            for i, c in enumerate(candidates):
                k = c["functional_kind"]
                if c["category"] == "Display" and (k not in seen_kinds or k == "other"):
                    balanced_results.append(candidates.pop(i))
                    if k != "other":
                        seen_kinds.add(k)
                    break

        # 3. If actuator requested and not yet included, select highest-ranking actuator of a new kind
        if wants_actuator and not any(r["category"] == "Actuator" for r in balanced_results):
            for i, c in enumerate(candidates):
                k = c["functional_kind"]
                if c["category"] == "Actuator" and (k not in seen_kinds or k == "other"):
                    balanced_results.append(candidates.pop(i))
                    if k != "other":
                        seen_kinds.add(k)
                    break

        # 4. Fill remaining spots with diverse functional kinds (NO duplicate sensor types!)
        remaining_candidates = []
        for c in candidates:
            k = c["functional_kind"]
            if k not in seen_kinds or k == "other":
                balanced_results.append(c)
                if k != "other":
                    seen_kinds.add(k)
                if len(balanced_results) >= top_n:
                    break
            else:
                remaining_candidates.append(c)

        # 5. If we still need more items up to top_n, add from remaining candidates
        if len(balanced_results) < top_n:
            for c in remaining_candidates:
                if c not in balanced_results:
                    balanced_results.append(c)
                if len(balanced_results) >= top_n:
                    break

        # Sort the final selected recommendations by match percentage descending
        balanced_results.sort(key=lambda x: x["match_percentage"], reverse=True)
        return balanced_results[:top_n]


if __name__ == "__main__":
    recommender = ComponentRecommender()
    recommender.fit()
    recommender.save()

    test_query = "I want to build a temperature monitoring system using ESP32 with an OLED display."
    recs = recommender.recommend(test_query, platform="ESP32", budget=1000)
    print(f"\nTop recommendations for '{test_query}':")
    for r in recs:
        print(f"[{r['match_percentage']}%] {r['name']} ({r['functional_kind_label']}) - Rs.{r['price_inr']}")
