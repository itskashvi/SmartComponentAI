"""
app.py
Flask web server for SmartComponentAI — Electronic Component Recommendation & Compatibility Assistant.
"""

import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
import pandas as pd

from models.recommendation import ComponentRecommender
from models.compatibility import HybridCompatibilityEngine
from models.taxonomy import get_functional_kind, get_functional_kind_label

app = Flask(__name__)
app.config["SECRET_KEY"] = "smartcomponentai-secret-key-2026"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "processed")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

# Global instances for recommender and compatibility engine
recommender = None
compatibility_engine = None


def get_recommender():
    global recommender
    if recommender is None:
        rec_path = os.path.join(MODELS_DIR, "recommendation_model.pkl")
        if os.path.exists(rec_path):
            recommender = ComponentRecommender.load(rec_path)
        else:
            recommender = ComponentRecommender()
            recommender.fit()
    return recommender


def get_compatibility_engine():
    global compatibility_engine
    if compatibility_engine is None:
        compat_path = os.path.join(MODELS_DIR, "compatibility_model.pkl")
        if os.path.exists(compat_path):
            compatibility_engine = HybridCompatibilityEngine.load(compat_path)
        else:
            compatibility_engine = HybridCompatibilityEngine()
    return compatibility_engine


@app.context_processor
def inject_global_data():
    """Provides platforms and components list to all templates."""
    engine = get_compatibility_engine()
    df_comp = engine.components_df

    platforms = []
    all_components = []
    if df_comp is not None:
        mcus = df_comp[df_comp["category"].isin(["Microcontroller", "Single Board Computer"])]
        platforms = mcus[["component_id", "name"]].to_dict("records")
        all_components = df_comp[["component_id", "name", "category", "price_inr"]].to_dict("records")

    return {
        "available_platforms": platforms,
        "all_components_list": all_components
    }


@app.route("/")
def home():
    """Home page: input project description, platform, budget, and existing components."""
    # Load starter projects
    projects_csv = os.path.join(DATA_DIR, "projects.csv")
    sample_projects = []
    if os.path.exists(projects_csv):
        sample_projects = pd.read_csv(projects_csv).to_dict("records")

    return render_template("index.html", sample_projects=sample_projects)


@app.route("/recommend", methods=["POST"])
def recommend():
    """Process project requirements and display recommended components + compatibility analysis."""
    project_description = request.form.get("project_description", "").strip()
    platform = request.form.get("platform", "ESP32").strip()
    budget_raw = request.form.get("budget", "")
    existing_parts_raw = request.form.get("existing_parts", "")

    # Parse budget
    try:
        budget = float(budget_raw) if budget_raw else 1500.0
    except ValueError:
        budget = 1500.0

    # Parse existing parts
    existing_parts = [p.strip() for p in existing_parts_raw.split(",") if p.strip()]

    # 1. Run Recommendation Engine
    rec_engine = get_recommender()
    recommendations = rec_engine.recommend(
        query=project_description,
        platform=platform,
        budget=budget,
        existing_parts=existing_parts,
        top_n=6
    )

    # 2. Run Compatibility Engine
    compat_engine = get_compatibility_engine()

    # Determine platform ID
    platform_id = "esp32"
    for p in ["esp32", "arduino_uno", "rpi_pico", "raspberry_pi_4", "stm32_bluepill", "arduino_mega", "arduino_nano"]:
        if p in platform.lower() or platform.lower() in p:
            platform_id = p
            break

    # Setup components: existing parts + top non-redundant recommended components
    # Strictly ensure that no two sensors/components of the same functional kind are in the setup!
    setup_component_ids = list(existing_parts)
    used_kinds = set()

    for pid in existing_parts:
        k = get_functional_kind(pid)
        if k and k != "other":
            used_kinds.add(k)

    for r in recommendations:
        cid = r["component_id"]
        k = r.get("functional_kind") or get_functional_kind(cid)
        if cid not in setup_component_ids:
            if k == "other" or k not in used_kinds:
                setup_component_ids.append(cid)
                if k and k != "other":
                    used_kinds.add(k)
        if len(setup_component_ids) >= 4:
            break

    compatibility_report = compat_engine.check_setup_compatibility(
        platform_id=platform_id,
        component_ids=setup_component_ids
    )

    return render_template(
        "results.html",
        project_description=project_description,
        platform=platform,
        platform_id=platform_id,
        budget=budget,
        existing_parts=existing_parts,
        recommendations=recommendations,
        compatibility_report=compatibility_report,
        setup_component_ids=setup_component_ids
    )


@app.route("/component/<component_id>")
def component_details(component_id):
    """Component details datasheet page with educational notes."""
    compat_engine = get_compatibility_engine()
    comp = compat_engine.get_component(component_id)
    if not comp:
        return render_template("404.html", message=f"Component '{component_id}' not found."), 404

    # Split lists for clean template rendering
    interfaces = [i.strip() for i in str(comp.get("interfaces", "")).split(",") if i.strip()]
    platforms = [p.strip() for p in str(comp.get("compatible_platforms", "")).split(",") if p.strip()]
    applications = [a.strip() for a in str(comp.get("applications", "")).split(",") if a.strip()]

    return render_template(
        "component.html",
        comp=comp,
        interfaces=interfaces,
        platforms=platforms,
        applications=applications
    )


@app.route("/check-compatibility", methods=["POST"])
def check_compatibility_api():
    """
    JSON API for dynamic compatibility testing from frontend JavaScript.
    Accepts: { "platform_id": "esp32", "component_ids": ["bme280", "hc_sr04"] }
    """
    data = request.get_json() or {}
    platform_id = data.get("platform_id", "esp32")
    component_ids = data.get("component_ids", [])

    compat_engine = get_compatibility_engine()
    report = compat_engine.check_setup_compatibility(
        platform_id=platform_id,
        component_ids=component_ids
    )
    return jsonify(report)


@app.route("/api/components")
def api_components():
    """Returns all components in JSON format for search/autocomplete."""
    compat_engine = get_compatibility_engine()
    df = compat_engine.components_df
    if df is not None:
        data = df.to_dict("records")
        return jsonify(data)
    return jsonify([])


if __name__ == "__main__":
    print("Starting SmartComponentAI Flask Server...")
    app.run(host="0.0.0.0", port=5000, debug=True)
