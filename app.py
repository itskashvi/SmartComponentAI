"""
app.py
Flask web server for SmartComponentAI — Electronic Component Recommendation & Compatibility Assistant.
"""

import os
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
import pandas as pd

from models.recommendation import ComponentRecommender
from models.compatibility import HybridCompatibilityEngine
from models.taxonomy import get_functional_kind, get_functional_kind_label
from models.wiring import generate_wiring_guide


# ==============================================================================
# Platform Detection: Maps user-facing platform strings to internal component_ids
# ==============================================================================

# Canonical mapping from known input variations to internal component_id
PLATFORM_ALIAS_MAP = {
    # ESP32 family
    "esp32": "esp32",
    "esp32devkit": "esp32",
    "espwroom32": "esp32",
    "esp32wroom": "esp32",
    "esp32devkitv1": "esp32",
    "esp32s3": "esp32_s3",
    "esp32s3devkit": "esp32_s3",
    "esp8266": "esp8266_nodemcu",
    "nodemcu": "esp8266_nodemcu",
    "nodemcuesp8266": "esp8266_nodemcu",
    "esp8266nodemcu": "esp8266_nodemcu",
    "esp01": "esp8266_nodemcu",
    "esp32cam": "esp32_cam",
    "esp32camera": "esp32_cam",
    # Arduino family
    "arduinouno": "arduino_uno",
    "arduinounor3": "arduino_uno",
    "uno": "arduino_uno",
    "unor3": "arduino_uno",
    "atmega328p": "arduino_uno",
    "arduinonano": "arduino_nano",
    "arduinonanov3": "arduino_nano",
    "nano": "arduino_nano",
    "nanov3": "arduino_nano",
    "arduinomega": "arduino_mega",
    "arduinomega2560": "arduino_mega",
    "mega": "arduino_mega",
    "mega2560": "arduino_mega",
    # Raspberry Pi family
    "raspberrypipico": "rpi_pico",
    "rpipico": "rpi_pico",
    "pico": "rpi_pico",
    "rp2040": "rpi_pico",
    "raspberrypipicow": "rpi_pico_w",
    "rpipicow": "rpi_pico_w",
    "picow": "rpi_pico_w",
    "raspberrypi4": "raspberry_pi_4",
    "rpi4": "raspberry_pi_4",
    "raspberrypi4b": "raspberry_pi_4",
    "raspberrypizero2w": "rpi_zero_2w",
    "rpizero2w": "rpi_zero_2w",
    "rpizero": "rpi_zero_2w",
    # STM32
    "stm32": "stm32_bluepill",
    "stm32bluepill": "stm32_bluepill",
    "bluepill": "stm32_bluepill",
    "stm32f103": "stm32_bluepill",
    "stm32f103c8t6": "stm32_bluepill",
    # Others
    "teensy40": "teensy_40",
    "teensy": "teensy_40",
    "microbitv2": "microbit_v2",
    "microbit": "microbit_v2",
    "bbcmicrobit": "microbit_v2",
    "attiny85": "attiny85_digispark",
    "digispark": "attiny85_digispark",
    "xiaoesp32c3": "seeed_xiao_esp32c3",
    "xiao": "seeed_xiao_esp32c3",
    "seeedxiao": "seeed_xiao_esp32c3",
}

# All valid platform component_ids in the system
VALID_PLATFORM_IDS = {
    "esp32", "esp32_s3", "esp8266_nodemcu", "esp32_cam",
    "arduino_uno", "arduino_nano", "arduino_mega",
    "rpi_pico", "rpi_pico_w", "raspberry_pi_4", "rpi_zero_2w",
    "stm32_bluepill",
    "teensy_40", "microbit_v2", "attiny85_digispark", "seeed_xiao_esp32c3",
}


def normalize_platform_input(raw_input):
    """
    Normalizes a user-provided platform string to a canonical component_id.
    Strips whitespace, hyphens, underscores, and converts to lowercase.
    Returns the matched platform_id or None if no match is found.
    """
    if not raw_input:
        return None
    # Normalize: lowercase, strip all spaces/hyphens/underscores/colons/dots
    norm = re.sub(r'[\s_\-\.:]+', '', raw_input.strip().lower())

    # 1. Direct alias match
    if norm in PLATFORM_ALIAS_MAP:
        return PLATFORM_ALIAS_MAP[norm]

    # 2. Check if it's already a valid platform_id (with underscores stripped)
    for pid in VALID_PLATFORM_IDS:
        pid_norm = pid.replace('_', '')
        if norm == pid_norm:
            return pid

    # 3. Substring match: check if any alias is contained in the input
    for alias, pid in sorted(PLATFORM_ALIAS_MAP.items(), key=lambda x: -len(x[0])):
        if alias in norm:
            return pid

    return None

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

    # Determine platform ID using robust normalization
    platform_id = normalize_platform_input(platform)
    if not platform_id:
        # Fallback: if no match found, default to esp32 but log warning
        platform_id = "esp32"

    # Filter existing parts: remove any MCU/SBC components from the peripheral list.
    # The platform MCU is already selected via the platform dropdown — having another
    # MCU (e.g. "esp32") in existing_parts creates a confusing MCU-vs-MCU compatibility
    # check that doesn't apply to a real circuit setup.
    if compat_engine.components_df is not None:
        mcu_ids = set(
            compat_engine.components_df[
                compat_engine.components_df["category"].isin(["Microcontroller", "Single Board Computer"])
            ]["component_id"].tolist()
        )
        existing_parts = [p for p in existing_parts if p not in mcu_ids]

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

    # Filter out MCU/SBC components from the peripheral list
    if compat_engine.components_df is not None:
        mcu_ids = set(
            compat_engine.components_df[
                compat_engine.components_df["category"].isin(["Microcontroller", "Single Board Computer"])
            ]["component_id"].tolist()
        )
        component_ids = [c for c in component_ids if c not in mcu_ids]

    report = compat_engine.check_setup_compatibility(
        platform_id=platform_id,
        component_ids=component_ids
    )
    return jsonify(report)


@app.route("/export-wiring", methods=["POST"])
def export_wiring():
    """Returns downloadable plain text wiring guide for reports and lab files."""
    data = request.get_json() or {}
    platform_id = data.get("platform_id", "esp32")
    component_ids = data.get("component_ids", [])
    compat_engine = get_compatibility_engine()
    guide = generate_wiring_guide(platform_id, component_ids, compat_engine.components_df)
    return Response(
        guide["export_text"],
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename=wiring_guide_{platform_id}.txt"}
    )


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
