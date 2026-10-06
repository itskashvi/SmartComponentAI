"""
models/compatibility.py
Hybrid hardware compatibility engine combining a trained Scikit-learn Classifier
with deterministic engineering safety rules for student guidance.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import joblib
import pandas as pd
import numpy as np

from models.taxonomy import get_functional_kind, get_functional_kind_label

MODELS_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

FEATURE_COLUMNS = [
    "voltage_compatible",
    "current_compatible",
    "logic_compatible",
    "interface_compatible",
    "pin_compatible"
]


class HybridCompatibilityEngine:
    def __init__(self, classifier=None):
        self.classifier = classifier
        self.components_df = None
        self._load_components()

    def _load_components(self):
        csv_path = os.path.join(DATA_DIR, "components.csv")
        if os.path.exists(csv_path):
            self.components_df = pd.read_csv(csv_path).set_index("component_id", drop=False)

    def save(self, filepath=None):
        if filepath is None:
            filepath = os.path.join(MODELS_DIR, "compatibility_model.pkl")
        joblib.dump(self.classifier, filepath)
        print(f"Compatibility classifier saved to {filepath}")

    @classmethod
    def load(cls, filepath=None):
        if filepath is None:
            filepath = os.path.join(MODELS_DIR, "compatibility_model.pkl")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"{filepath} not found. Please train model first.")
        classifier = joblib.load(filepath)
        engine = cls(classifier=classifier)
        return engine

    def get_component(self, component_id):
        if self.components_df is None or component_id not in self.components_df.index:
            return None
        return self.components_df.loc[component_id].to_dict()

    def extract_pair_features(self, comp_a, comp_b):
        """
        Computes the 5 fundamental engineering compatibility features for a pair.
        """
        is_mcu_a = comp_a.get("category") in ["Microcontroller", "Single Board Computer"]
        is_mcu_b = comp_b.get("category") in ["Microcontroller", "Single Board Computer"]

        if not is_mcu_a and is_mcu_b:
            comp_a, comp_b = comp_b, comp_a
            is_mcu_a, is_mcu_b = is_mcu_b, is_mcu_a

        int_a = {x.strip().upper() for x in str(comp_a.get("interfaces", "")).split(",") if x.strip()}
        int_b = {x.strip().upper() for x in str(comp_b.get("interfaces", "")).split(",") if x.strip()}

        v_min_a = float(comp_a.get("operating_voltage_min", 3.3))
        v_max_a = float(comp_a.get("operating_voltage_max", 3.3))
        logic_a = float(comp_a.get("logic_voltage", 3.3))

        v_min_b = float(comp_b.get("operating_voltage_min", 3.3))
        v_max_b = float(comp_b.get("operating_voltage_max", 3.3))
        logic_b = float(comp_b.get("logic_voltage", 3.3))

        current_b = float(comp_b.get("max_current_ma", 10.0))
        pins_b = int(comp_b.get("pins_required", 1))
        gpio_a = int(comp_a.get("total_gpio", 20)) if is_mcu_a else 20

        # Feature 1: Interface
        interface_compatible = 1
        if is_mcu_a:
            needed = int_b - {"POWER", "EXTERNAL RELAY/MOSFET"}
            has_match = any(p in int_a or (p in {"1-WIRE", "PWM", "GPIO"} and "GPIO" in int_a) for p in needed)
            if "ANALOG" in int_b and "ADC" not in int_a:
                interface_compatible = 0
            elif needed and not has_match and "POWER" not in int_b:
                interface_compatible = 0

        # Feature 2: Pins
        pin_compatible = 1
        if is_mcu_a and pins_b > (gpio_a - 2):
            pin_compatible = 0

        # Feature 3: Voltage
        voltage_compatible = 1
        if is_mcu_a:
            if v_min_b > 5.5:
                voltage_compatible = 0
            elif v_min_b >= 4.5 and v_max_a <= 3.6 and comp_a.get("component_id") not in ["esp32", "esp32_s3", "rpi_pico", "raspberry_pi_4"]:
                voltage_compatible = 0
        else:
            if v_max_a < v_min_b or v_max_b < v_min_a:
                voltage_compatible = 0

        # Feature 4: Logic
        logic_compatible = 1
        if is_mcu_a:
            # 5V sensor out to 3.3V MCU
            if logic_b >= 4.5 and logic_a <= 3.6 and comp_b.get("category") in ["Sensor", "Display", "Communication"]:
                logic_compatible = 0
            # 5V MCU to 3.3V rated device
            elif logic_a >= 4.5 and logic_b <= 3.6 and logic_b > 0:
                logic_compatible = 0
        else:
            if abs(logic_a - logic_b) > 1.2 and logic_a > 0 and logic_b > 0:
                logic_compatible = 0

        # Feature 5: Current
        current_compatible = 1
        if is_mcu_a and current_b > 200.0:
            current_compatible = 0

        return {
            "voltage_compatible": voltage_compatible,
            "current_compatible": current_compatible,
            "logic_compatible": logic_compatible,
            "interface_compatible": interface_compatible,
            "pin_compatible": pin_compatible
        }

    def evaluate_pair(self, comp_a_id, comp_b_id):
        """
        Performs hybrid evaluation: ML model prediction combined with deterministic engineering rules.
        """
        comp_a = self.get_component(comp_a_id)
        comp_b = self.get_component(comp_b_id)

        if not comp_a or not comp_b:
            return {
                "pair": f"{comp_a_id} + {comp_b_id}",
                "status": "incompatible",
                "ml_probability": 0.0,
                "reason": f"One or both components not found in knowledgebase: {comp_a_id}, {comp_b_id}",
                "solution": "Verify component identifiers."
            }

        # Normalize MCU as first element
        is_mcu_a = comp_a.get("category") in ["Microcontroller", "Single Board Computer"]
        is_mcu_b = comp_b.get("category") in ["Microcontroller", "Single Board Computer"]
        if not is_mcu_a and is_mcu_b:
            comp_a, comp_b = comp_b, comp_a

        features = self.extract_pair_features(comp_a, comp_b)
        feat_df = pd.DataFrame([features])[FEATURE_COLUMNS]

        # ML Model prediction
        ml_prediction = 1
        ml_proba = 1.0
        if self.classifier is not None:
            try:
                ml_prediction = int(self.classifier.predict(feat_df)[0])
                probas = self.classifier.predict_proba(feat_df)[0]
                ml_proba = float(probas[1]) if len(probas) > 1 else float(probas[0])
            except Exception as e:
                print(f"ML inference error: {e}")

        # Deterministic Engineering Rules Evaluation
        status = "compatible"
        reasons = []
        solutions = []

        # Rule 1: Protocol / Interface Mismatch
        if features["interface_compatible"] == 0:
            status = "incompatible"
            if "ANALOG" in str(comp_b.get("interfaces", "")).upper() and "ADC" not in str(comp_a.get("interfaces", "")).upper():
                reasons.append(f"{comp_a['name']} does not have onboard Analog-to-Digital Converter (ADC) channels to read analog sensor data from {comp_b['name']}.")
                solutions.append("Add an ADS1115 16-bit I2C ADC module to read the analog signal.")
            else:
                reasons.append(f"{comp_a['name']} lacks the hardware interface required by {comp_b['name']}.")
                solutions.append("Choose a platform that supports this interface natively or use a protocol converter.")

        # Rule 2: Insufficient Pin Capacity
        if features["pin_compatible"] == 0:
            status = "incompatible"
            reasons.append(f"{comp_b['name']} demands {comp_b.get('pins_required')} pins, which exceeds the available free pins on {comp_a['name']}.")
            solutions.append("Use a PCF8574 I2C I/O expander or upgrade to a board with more GPIOs (e.g. ESP32 or Arduino Mega).")

        # Rule 3: High Voltage Supply Mismatch
        if features["voltage_compatible"] == 0:
            if comp_b.get("operating_voltage_min", 3.3) > 5.5:
                status = "warning" if status != "incompatible" else "incompatible"
                reasons.append(f"{comp_b['name']} requires {comp_b.get('operating_voltage_min')}V, which cannot be directly supplied by {comp_a['name']}.")
                solutions.append(f"Power {comp_b['name']} from an external DC supply and switch it using a Relay or MOSFET module.")
            else:
                status = "warning" if status != "incompatible" else "incompatible"
                reasons.append(f"{comp_b['name']} requires a 5V supply, whereas {comp_a['name']} supplies only 3.3V.")
                solutions.append("Use an external 5V regulator or step-up boost converter to power the component.")

        # Rule 4: Logic Level Voltage Hazard (Crucial Student Safety Rule!)
        if features["logic_compatible"] == 0:
            status = "warning" if status != "incompatible" else "incompatible"
            if comp_b.get("logic_voltage") >= 4.5 and comp_a.get("logic_voltage") <= 3.6:
                reasons.append(
                    f"{comp_b['name']} outputs a 5V logic signal, while {comp_a['name']} GPIO pins are only 3.3V tolerant. "
                    "Connecting 5V directly to a 3.3V GPIO can damage the microcontroller."
                )
                solutions.append(
                    "Insert a simple voltage divider (1k-ohm and 2k-ohm resistors) or a 4-channel bi-directional 3.3V-5V logic level shifter on the signal line."
                )
            elif comp_a.get("logic_voltage") >= 4.5 and comp_b.get("logic_voltage") <= 3.6:
                reasons.append(
                    f"{comp_a['name']} drives signals at 5V logic, but {comp_b['name']} inputs are rated for 3.3V logic."
                )
                solutions.append("Use a 3.3V-5V logic level converter to protect the 3.3V component inputs.")

        # Rule 5: Overcurrent on Onboard Regulator
        if features["current_compatible"] == 0:
            status = "warning" if status != "incompatible" else "incompatible"
            reasons.append(
                f"{comp_b['name']} can draw up to {comp_b.get('max_current_ma')}mA, which exceeds the safe current rating of {comp_a['name']}'s onboard linear regulator."
            )
            solutions.append(
                f"Power {comp_b['name']} from an external 5V power supply (adapter or battery), sharing only the ground (GND) and control signal lines with {comp_a['name']}."
            )

        # Decision Engine Override
        # If deterministic rules indicate danger/warning, rule strictly overrides an optimistic ML classification
        if status in ["warning", "incompatible"] and ml_prediction == 1:
            decision_source = "Engineering Rule Safety Override (Overrode Optimistic ML Prediction)"
        else:
            decision_source = "Hybrid Consensus (ML Classifier + Engineering Verification)"

        final_reason = " ".join(reasons) if reasons else "Seamless electrical and protocol match. Logic levels, voltage supplies, and pin capacity are fully satisfied."
        final_solution = " ".join(solutions) if solutions else "Direct connection supported with standard jumper wires."

        return {
            "component_a": comp_a["name"],
            "component_a_id": comp_a["component_id"],
            "component_b": comp_b["name"],
            "component_b_id": comp_b["component_id"],
            "status": status,  # "compatible", "warning", "incompatible"
            "features": {
                "voltage": features["voltage_compatible"] == 1,
                "logic": features["logic_compatible"] == 1,
                "interface": features["interface_compatible"] == 1,
                "pins": features["pin_compatible"] == 1,
                "current": features["current_compatible"] == 1
            },
            "ml_compatible_probability": round(ml_proba * 100, 1),
            "decision_source": decision_source,
            "reason": final_reason,
            "solution": final_solution
        }

    def check_setup_compatibility(self, platform_id, component_ids):
        """
        Evaluates the entire student hardware setup:
        Checks the chosen platform against each selected peripheral,
        and computes cumulative pin usage and total power requirements.
        """
        platform = self.get_component(platform_id)
        if not platform:
            return {
                "overall_status": "incompatible",
                "summary": f"Unknown platform: {platform_id}",
                "pair_results": [],
                "pin_budget": {"used": 0, "available": 0},
                "power_budget": {"total_ma": 0}
            }

        pair_results = []
        total_pins = 0
        total_current_ma = float(platform.get("max_current_ma", 100.0))
        has_warning = False
        has_incompatible = False

        for cid in component_ids:
            if cid == platform_id:
                continue
            res = self.evaluate_pair(platform_id, cid)
            pair_results.append(res)
            if res["status"] == "incompatible":
                has_incompatible = True
            elif res["status"] == "warning":
                has_warning = True

            comp = self.get_component(cid)
            if comp:
                total_pins += int(comp.get("pins_required", 1))
                total_current_ma += float(comp.get("max_current_ma", 10.0))

        # Check for duplicate / redundant sensors of the exact same kind in setup
        kind_map = {}
        for cid in component_ids:
            if cid == platform_id:
                continue
            k = get_functional_kind(cid)
            if k and k != "other":
                kind_map.setdefault(k, []).append(cid)

        for k, duplicate_ids in kind_map.items():
            if len(duplicate_ids) > 1:
                has_warning = True
                c1 = self.get_component(duplicate_ids[0]) or {}
                c2 = self.get_component(duplicate_ids[1]) or {}
                c1_name = c1.get("name", duplicate_ids[0])
                c2_name = c2.get("name", duplicate_ids[1])
                k_label = get_functional_kind_label(duplicate_ids[0])
                pair_results.append({
                    "component_a": c1_name,
                    "component_a_id": duplicate_ids[0],
                    "component_b": c2_name,
                    "component_b_id": duplicate_ids[1],
                    "status": "warning",
                    "features": {"voltage": True, "logic": True, "interface": True, "pins": True, "current": True},
                    "ml_compatible_probability": 75.0,
                    "decision_source": "Engineering Redundancy Rule",
                    "reason": f"Redundant Sensors Detected: Both '{c1_name}' and '{c2_name}' serve the '{k_label}' role. A standard embedded hardware setup typically requires only one sensor for this parameter.",
                    "solution": f"Remove '{c2_name}' to avoid wasting GPIO pins and power, or verify if your project specifically requires dual {k_label} sensing."
                })

        # Check total cumulative pin budget
        available_gpio = int(platform.get("total_gpio", 20))
        if total_pins > available_gpio:
            has_warning = True
            pair_results.append({
                "component_a": platform["name"],
                "component_a_id": platform["component_id"],
                "component_b": "Total System Setup",
                "component_b_id": "system_total",
                "status": "warning",
                "features": {"voltage": True, "logic": True, "interface": True, "pins": False, "current": True},
                "ml_compatible_probability": 30.0,
                "decision_source": "System Cumulative Pin Check",
                "reason": f"Your selected components collectively require {total_pins} pins, which exceeds the {available_gpio} available GPIOs on {platform['name']}.",
                "solution": "Use I2C multiplexers (TCA9548A) or I/O port expanders (PCF8574), or choose a board with more pins like ESP32 or Arduino Mega."
            })

        overall_status = "incompatible" if has_incompatible else ("warning" if has_warning else "compatible")

        return {
            "overall_status": overall_status,
            "platform_name": platform["name"],
            "platform_id": platform["component_id"],
            "pair_results": pair_results,
            "pin_budget": {
                "used": total_pins,
                "available": available_gpio,
                "percentage": min(100, int((total_pins / max(1, available_gpio)) * 100))
            },
            "power_budget": {
                "total_ma": round(total_current_ma, 1),
                "exceeds_usb": total_current_ma > 500.0
            }
        }


if __name__ == "__main__":
    # Test evaluation without ML model (pure rules fallback)
    engine = HybridCompatibilityEngine()
    
    print("Testing ESP32 + BME280:")
    res1 = engine.evaluate_pair("esp32", "bme280")
    print(f"Status: {res1['status']}")
    print(f"Reason: {res1['reason']}\n")

    print("Testing ESP32 + HC-SR04 (5V Ultrasonic):")
    res2 = engine.evaluate_pair("esp32", "hc_sr04")
    print(f"Status: {res2['status']}")
    print(f"Features: {res2['features']}")
    print(f"Reason: {res2['reason']}")
    print(f"Solution: {res2['solution']}\n")

    print("Testing Raspberry Pi 4 + MQ-2 (Analog):")
    res3 = engine.evaluate_pair("raspberry_pi_4", "mq2")
    print(f"Status: {res3['status']}")
    print(f"Reason: {res3['reason']}\n")
