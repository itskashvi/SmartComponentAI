"""
tests/test_pipeline.py
Automated end-to-end integration and smoke tests for SmartComponentAI:
- Recommendation Engine test
- Hybrid Compatibility Engine test
- Flask Web App routes and API responses
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
import json
from models.recommendation import ComponentRecommender
from models.compatibility import HybridCompatibilityEngine
from app import app


class TestSmartComponentAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recommender = ComponentRecommender.load()
        cls.compat_engine = HybridCompatibilityEngine.load()
        cls.client = app.test_client()

    # -------------------------------------------------------------
    # 1. Recommendation Engine Tests
    # -------------------------------------------------------------
    def test_recommendation_temperature_esp32(self):
        query = "I want to build a temperature monitoring system using ESP32 with an OLED display."
        recs = self.recommender.recommend(query, platform="ESP32", budget=1000)
        self.assertGreater(len(recs), 0)
        rec_ids = [r["component_id"] for r in recs]
        
        # A temperature sensor (DS18B20, BME280, DHT22) or OLED display (SSD1306, SH1106) should be recommended
        self.assertTrue(
            any(k in rec_ids for k in ["bme280", "ds18b20", "dht22", "ssd1306_oled", "sh1106_oled"]),
            f"Expected a temperature sensor or OLED display in recommendations, got: {rec_ids}"
        )
        print(f"\n[PASS] Recommendation test for query '{query}': top results = {rec_ids[:4]}")

    def test_recommendation_obstacle_robot(self):
        query = "obstacle avoiding robot car with ultrasonic sensor and motor driver"
        recs = self.recommender.recommend(query, platform="Arduino Uno", budget=1500)
        rec_ids = [r["component_id"] for r in recs]
        self.assertTrue(
            "hc_sr04" in rec_ids or "l298n_driver" in rec_ids or "sg90_servo" in rec_ids,
            f"Expected robot parts in recommendations, got: {rec_ids}"
        )
        print(f"[PASS] Recommendation test for robotics query: top results = {rec_ids[:4]}")

    # -------------------------------------------------------------
    # 2. Hybrid Compatibility Engine Tests
    # -------------------------------------------------------------
    def test_esp32_bme280_compatible(self):
        res = self.compat_engine.evaluate_pair("esp32", "bme280")
        self.assertEqual(res["status"], "compatible")
        self.assertTrue(res["features"]["voltage"])
        self.assertTrue(res["features"]["logic"])
        self.assertTrue(res["features"]["interface"])
        print(f"[PASS] ESP32 + BME280 compatibility evaluated as: {res['status']}")

    def test_esp32_hcsr04_warning(self):
        # 5V ultrasonic echo into 3.3V ESP32 GPIO must trigger WARNING with level shifting solution
        res = self.compat_engine.evaluate_pair("esp32", "hc_sr04")
        self.assertEqual(res["status"], "warning")
        self.assertFalse(res["features"]["logic"], "Expected logic_compatible to be False due to 5V echo vs 3.3V GPIO")
        self.assertIn("3.3V", res["reason"])
        self.assertIn("voltage divider", res["solution"].lower())
        print(f"[PASS] ESP32 + HC-SR04 compatibility evaluated as: {res['status']} with reason: {res['reason'][:60]}...")

    def test_rpi4_mq2_incompatible_adc(self):
        # Raspberry Pi 4 has no built-in ADC for analog MQ sensors
        res = self.compat_engine.evaluate_pair("raspberry_pi_4", "mq2")
        self.assertEqual(res["status"], "incompatible")
        self.assertFalse(res["features"]["interface"])
        self.assertIn("ADC", res["solution"])
        print(f"[PASS] Raspberry Pi 4 + MQ-2 evaluated as: {res['status']} with ADC requirement")

    def test_full_setup_compatibility(self):
        setup = self.compat_engine.check_setup_compatibility(
            platform_id="esp32",
            component_ids=["bme280", "ssd1306_oled"]
        )
        self.assertEqual(setup["overall_status"], "compatible")
        self.assertGreater(setup["pin_budget"]["available"], 0)
        self.assertGreater(setup["pin_budget"]["used"], 0)
        print(f"[PASS] Full setup (ESP32 + BME280 + OLED) evaluated as: {setup['overall_status']}")

    def test_redundant_sensor_detection(self):
        # When two ambient climate sensors (BME280 and DHT22) are placed in the same setup
        setup = self.compat_engine.check_setup_compatibility(
            platform_id="esp32",
            component_ids=["bme280", "dht22"]
        )
        self.assertEqual(setup["overall_status"], "warning")
        reasons = [p["reason"] for p in setup["pair_results"]]
        self.assertTrue(
            any("Redundant Sensors Detected" in r for r in reasons),
            f"Expected 'Redundant Sensors Detected' warning in setup reasons: {reasons}"
        )
        print("[PASS] Redundant sensor detection verified (BME280 + DHT22 triggers redundancy warning).")

    def test_no_duplicate_functional_kinds_in_recommendations(self):
        query = "I want to build an IoT weather station using ESP32 with temperature, humidity, and air quality sensors and an OLED display."
        recs = self.recommender.recommend(query, platform="ESP32", top_n=6)
        kinds = [r["functional_kind"] for r in recs if r["functional_kind"] != "other"]
        self.assertEqual(len(kinds), len(set(kinds)), f"Found duplicate functional kinds in recommendations: {kinds}")
        print(f"[PASS] Diverse recommendations verified (no duplicate sensor kinds): {kinds}")

    # -------------------------------------------------------------
    # 3. Flask Web Application Route Tests
    # -------------------------------------------------------------
    def test_home_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SmartComponent", response.data)
        self.assertIn(b"Project Description", response.data)
        print("[PASS] GET / returned 200 with home form.")

    def test_recommend_route(self):
        response = self.client.post("/recommend", data={
            "project_description": "I want to build a temperature monitoring system using ESP32 with an OLED display.",
            "platform": "ESP32",
            "budget": "1000",
            "existing_parts": "esp32"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Recommendation & Compatibility Results", response.data)
        self.assertIn(b"Recommended Components", response.data)
        self.assertIn(b"Compatibility Analysis", response.data)
        print("[PASS] POST /recommend returned 200 with rendered results page.")

    def test_component_details_route(self):
        response = self.client.get("/component/bme280")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"BME280", response.data)
        self.assertIn(b"Operating Voltage", response.data)
        self.assertIn(b"Logic Level", response.data)
        print("[PASS] GET /component/bme280 returned 200 with datasheet specs.")

    def test_api_check_compatibility(self):
        payload = {
            "platform_id": "esp32",
            "component_ids": ["bme280", "hc_sr04"]
        }
        response = self.client.post(
            "/check-compatibility",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("overall_status", data)
        self.assertEqual(data["overall_status"], "warning")
        self.assertEqual(len(data["pair_results"]), 2)
        print(f"[PASS] POST /check-compatibility returned JSON status: {data['overall_status']}")

    def test_api_components_list(self):
        response = self.client.get("/api/components")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertGreaterEqual(len(data), 100)
        print(f"[PASS] GET /api/components returned {len(data)} components.")


if __name__ == "__main__":
    unittest.main()
