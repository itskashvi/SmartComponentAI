"""
scratch/demo_run.py
Demonstrates the full end-to-end user scenario requested in Section 15.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.recommendation import ComponentRecommender
from models.compatibility import HybridCompatibilityEngine

print("==================================================")
print("DEMO STEP 1: Student Requirements")
print("==================================================")
query = "I want to build an IoT temperature monitor using ESP32 with an OLED display."
platform = "ESP32"
budget = 1000
print(f"Query: \"{query}\"")
print(f"Platform: {platform}")
print(f"Budget: Rs.{budget}")

print("\n==================================================")
print("DEMO STEP 2 & 3: Recommendation Engine (TF-IDF)")
print("==================================================")
rec = ComponentRecommender.load()
recommendations = rec.recommend(query, platform=platform, budget=budget, top_n=5)
for i, r in enumerate(recommendations, 1):
    print(f"{i}. {r['name']} ({r['category']}) - Match: {r['match_percentage']}% | Price: Rs.{r['price_inr']}")

print("\n==================================================")
print("DEMO STEP 4, 5 & 6: Student Setup Compatibility")
print("Setup: ESP32 + BME280 + SSD1306 OLED")
print("==================================================")
engine = HybridCompatibilityEngine.load()
setup = engine.check_setup_compatibility("esp32", ["bme280", "ssd1306_oled"])
print(f"Overall Setup Status: {setup['overall_status'].upper()}")
print(f"Pin Budget: {setup['pin_budget']['used']}/{setup['pin_budget']['available']} pins ({setup['pin_budget']['percentage']}%)")
print(f"Total Current: {setup['power_budget']['total_ma']} mA (Exceeds USB: {setup['power_budget']['exceeds_usb']})")

for p in setup['pair_results']:
    print(f"\n* {p['component_a']} <-> {p['component_b']}")
    print(f"  Status: {p['status'].upper()} (ML confidence: {p['ml_compatible_probability']}%)")
    print(f"  Features: Voltage={p['features']['voltage']}, Logic={p['features']['logic']}, Interface={p['features']['interface']}")
    print(f"  Reason: {p['reason']}")

print("\n==================================================")
print("DEMO WARNING SCENARIO: ESP32 + HC-SR04")
print("==================================================")
warn_setup = engine.check_setup_compatibility("esp32", ["hc_sr04"])
print(f"Overall Setup Status: {warn_setup['overall_status'].upper()}")
for p in warn_setup['pair_results']:
    print(f"\n* {p['component_a']} <-> {p['component_b']}")
    print(f"  Status: {p['status'].upper()}")
    print(f"  Reason: {p['reason']}")
    print(f"  Solution: {p['solution']}")
