"""
evaluation/train.py
Trains and compares Decision Tree, Random Forest, and Gradient Boosting models
on the compatibility dataset.
Serializes the best model to models/compatibility_model.pkl and
fits the recommendation engine to models/recommendation_model.pkl.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import joblib

from models.recommendation import ComponentRecommender

EVAL_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

FEATURE_COLS = [
    "voltage_compatible",
    "current_compatible",
    "logic_compatible",
    "interface_compatible",
    "pin_compatible"
]


def train_models():
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(EVAL_DIR, exist_ok=True)

    compat_path = os.path.join(DATA_DIR, "compatibility.csv")
    if not os.path.exists(compat_path):
        raise FileNotFoundError(f"{compat_path} not found. Run preprocessing scripts first.")

    df = pd.read_csv(compat_path)
    X = df[FEATURE_COLS]
    y = df["compatible"]

    print(f"Total dataset samples: {len(df)}")
    print(f"Features: {FEATURE_COLS}")
    print(f"Target distribution:\n{y.value_counts()}")

    # 70% Train, 15% Validation, 15% Test split
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    print(f"Split sizes: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")

    candidate_models = {
        "Decision Tree": DecisionTreeClassifier(max_depth=5, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, random_state=42)
    }

    results = {}
    best_name = None
    best_f1 = -1.0
    best_clf = None

    for name, clf in candidate_models.items():
        clf.fit(X_train, y_train)

        # Validation set evaluation
        val_pred = clf.predict(X_val)
        val_acc = accuracy_score(y_val, val_pred)
        val_f1 = f1_score(y_val, val_pred)

        # Test set evaluation
        test_pred = clf.predict(X_test)
        acc = accuracy_score(y_test, test_pred)
        prec = precision_score(y_test, test_pred, zero_division=0)
        rec = recall_score(y_test, test_pred, zero_division=0)
        f1 = f1_score(y_test, test_pred, zero_division=0)
        cm = confusion_matrix(y_test, test_pred).tolist()

        results[name] = {
            "validation_accuracy": round(float(val_acc), 4),
            "validation_f1": round(float(val_f1), 4),
            "test_accuracy": round(float(acc), 4),
            "test_precision": round(float(prec), 4),
            "test_recall": round(float(rec), 4),
            "test_f1": round(float(f1), 4),
            "confusion_matrix": cm
        }

        print(f"\n[{name}]")
        print(f"  Test Accuracy:  {acc:.4f}")
        print(f"  Test Precision: {prec:.4f}")
        print(f"  Test Recall:    {rec:.4f}")
        print(f"  Test F1-Score:  {f1:.4f}")
        print(f"  Confusion Matrix: {cm}")

        # Prioritize Random Forest on ties as requested in system spec
        if f1 > best_f1 or (f1 == best_f1 and name == "Random Forest"):
            best_f1 = f1
            best_name = name
            best_clf = clf

    print(f"\nSelected Best Model: {best_name} (F1 = {best_f1:.4f})")

    # Save compatibility model
    compat_model_path = os.path.join(MODELS_DIR, "compatibility_model.pkl")
    joblib.dump(best_clf, compat_model_path)
    print(f"Saved best classifier to {compat_model_path}")

    # Save test dataset for evaluate.py
    test_data_path = os.path.join(EVAL_DIR, "test_data.pkl")
    joblib.dump({
        "X_test": X_test,
        "y_test": y_test,
        "models": candidate_models,
        "best_model_name": best_name
    }, test_data_path)

    # Save training report JSON
    report_path = os.path.join(EVAL_DIR, "training_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "best_model": best_name,
            "models_evaluated": results,
            "features": FEATURE_COLS
        }, f, indent=2)
    print(f"Saved evaluation metrics to {report_path}")

    # Train and save recommendation model
    print("\nTraining Recommendation Engine (TF-IDF)...")
    recommender = ComponentRecommender()
    recommender.fit()
    recommender.save(os.path.join(MODELS_DIR, "recommendation_model.pkl"))
    print("Recommendation Engine saved successfully.")


if __name__ == "__main__":
    train_models()
