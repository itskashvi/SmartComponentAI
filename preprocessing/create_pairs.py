"""
preprocessing/create_pairs.py
Generates pairwise component compatibility records with engineered electrical features:
voltage_compatible, current_compatible, logic_compatible, interface_compatible, pin_compatible.
Applies ground-truth labeling and realistic engineering rules.
Exports to data/processed/compatibility.csv.
"""

import os
import pandas as pd
import numpy as np

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

def parse_interfaces(interface_str):
    if not isinstance(interface_str, str):
        return set()
    return {x.strip().upper() for x in interface_str.replace(";", ",").split(",") if x.strip()}

def check_pairwise_compatibility(comp_a, comp_b):
    """
    Evaluates electrical and interface compatibility between Component A (typically MCU/Host or Component 1)
    and Component B (Peripheral, Sensor, Actuator, or Component 2).
    """
    is_mcu_a = comp_a["category"] in ["Microcontroller", "Single Board Computer"]
    is_mcu_b = comp_b["category"] in ["Microcontroller", "Single Board Computer"]

    # Normalize roles: If B is MCU and A is not, swap for uniform analysis
    if not is_mcu_a and is_mcu_b:
        comp_a, comp_b = comp_b, comp_a
        is_mcu_a, is_mcu_b = is_mcu_b, is_mcu_a

    int_a = parse_interfaces(comp_a.get("interfaces", ""))
    int_b = parse_interfaces(comp_b.get("interfaces", ""))

    v_min_a = float(comp_a.get("operating_voltage_min", 3.3))
    v_max_a = float(comp_a.get("operating_voltage_max", 3.3))
    logic_a = float(comp_a.get("logic_voltage", 3.3))

    v_min_b = float(comp_b.get("operating_voltage_min", 3.3))
    v_max_b = float(comp_b.get("operating_voltage_max", 3.3))
    logic_b = float(comp_b.get("logic_voltage", 3.3))

    current_b = float(comp_b.get("max_current_ma", 10.0))
    pins_b = int(comp_b.get("pins_required", 1))
    gpio_a = int(comp_a.get("total_gpio", 20)) if is_mcu_a else 20

    warnings = []
    solutions = []
    status = "compatible"

    # 1. Interface Compatibility
    interface_compatible = 1
    if is_mcu_a:
        # Check specific protocol demands
        needed_protocols = int_b - {"POWER", "EXTERNAL RELAY/MOSFET"}
        has_common = False
        for p in needed_protocols:
            if p in int_a:
                has_common = True
                break
            # 1-Wire, PWM, Digital can run on generic GPIO
            if p in {"1-WIRE", "PWM", "GPIO"} and "GPIO" in int_a:
                has_common = True
                break
        
        # Special case: Analog requires ADC
        if "ANALOG" in int_b and "ADC" not in int_a:
            interface_compatible = 0
            warnings.append(f"{comp_a['name']} does not have built-in Analog ADC pins to read analog output from {comp_b['name']}.")
            solutions.append(f"Add an external I2C ADC module like ADS1115 to read analog signals on {comp_a['name']}.")
            status = "incompatible"
        elif needed_protocols and not has_common and "POWER" not in int_b:
            interface_compatible = 0
            warnings.append(f"{comp_a['name']} lacks the required interfaces ({', '.join(needed_protocols)}) for {comp_b['name']}.")
            solutions.append("Select a microcontroller that natively provides this communication protocol or use an adapter.")
            status = "incompatible"
    else:
        # Peripheral to peripheral: compatible if sharing bus or power
        interface_compatible = 1

    # 2. Pin Compatibility
    pin_compatible = 1
    if is_mcu_a and pins_b > 0:
        if pins_b > (gpio_a - 2): # leave at least 2 pins
            pin_compatible = 0
            warnings.append(f"{comp_b['name']} requires {pins_b} pins, exceeding available GPIO capacity of {comp_a['name']}.")
            solutions.append("Use an I2C I/O expander like PCF8574 or choose a microcontroller with higher pin count (e.g. ESP32 or Arduino Mega).")
            status = "incompatible"

    # 3. Voltage Supply Compatibility
    voltage_compatible = 1
    if is_mcu_a:
        # MCU boards typically expose 3.3V and/or 5V rails (via USB)
        # If peripheral requires > 5.5V or min voltage > 5.0V (e.g. 12V solenoid)
        if v_min_b > 5.5:
            voltage_compatible = 0
            warnings.append(f"{comp_b['name']} operates at {v_min_b}V-{v_max_b}V, which cannot be supplied directly by {comp_a['name']}.")
            solutions.append(f"Use an external {v_min_b}V DC power supply and switch it using a Relay or MOSFET module.")
            if status != "incompatible":
                status = "warning"
        # If peripheral strictly requires 5.0V (e.g. MQ gas sensors or 5V-only sensors) and MCU is 3.3V only
        elif v_min_b >= 4.5 and v_max_a <= 3.6 and comp_a["component_id"] not in ["esp32", "esp32_s3", "rpi_pico", "raspberry_pi_4"]:
            voltage_compatible = 0
            warnings.append(f"{comp_b['name']} requires at least 4.5V-5V, while {comp_a['name']} supplies only 3.3V.")
            solutions.append("Supply 5V to the sensor using an external step-up boost converter or powered 5V rail.")
            if status != "incompatible":
                status = "warning"
    else:
        # Both peripherals
        overlap = not (v_max_a < v_min_b or v_max_b < v_min_a)
        if not overlap:
            voltage_compatible = 0

    # 4. Logic Level Compatibility
    logic_compatible = 1
    if is_mcu_a:
        # Dangerous case 1: 5V logic output from peripheral into 3.3V MCU GPIO (e.g. HC-SR04 Echo into ESP32)
        if logic_b >= 4.5 and logic_a <= 3.6:
            # Check if peripheral outputs a signal
            if comp_b["category"] in ["Sensor", "Display", "Communication"]:
                logic_compatible = 0
                warnings.append(f"{comp_b['name']} outputs a {logic_b}V logic signal, whereas {comp_a['name']} GPIO is only {logic_a}V tolerant.")
                solutions.append("Use a resistive voltage divider (e.g. 1k-ohm and 2k-ohm resistors) or a 4-channel bi-directional logic level converter (3.3V <-> 5V).")
                if status != "incompatible":
                    status = "warning"
        # Dangerous case 2: 5V MCU driving 3.3V logic peripheral without level shifter (e.g. Arduino Uno 5V SPI into NRF24L01 or SD Card or 3.3V OLED)
        elif logic_a >= 4.5 and logic_b <= 3.6 and logic_b > 0:
            logic_compatible = 0
            warnings.append(f"{comp_a['name']} outputs 5V logic pulses, while {comp_b['name']} inputs are rated for {logic_b}V maximum.")
            solutions.append("Use a 3.3V-5V logic level converter module to step down the 5V signals before entering the sensor.")
            if status != "incompatible":
                status = "warning"
    else:
        if abs(logic_a - logic_b) > 1.2 and logic_a > 0 and logic_b > 0:
            logic_compatible = 0

    # 5. Current Draw Compatibility
    current_compatible = 1
    if is_mcu_a:
        # Typical onboard regulators can supply ~150-250mA for external components safely
        # High current consumers: Servos (>500mA), Motor drivers (>1000mA), Solenoids (>400mA), WS2812B (>500mA), SIM800L (2A bursts)
        if current_b > 200.0:
            current_compatible = 0
            warnings.append(f"{comp_b['name']} draws up to {current_b}mA, exceeding the safe current limit of {comp_a['name']}'s onboard regulator.")
            solutions.append(f"Power {comp_b['name']} from a dedicated external power supply (e.g. 5V 2A adapter or battery), sharing common ground with the MCU.")
            if status != "incompatible":
                status = "warning"

    # Overall binary label for ML training
    # Compatible = 1 only if all 5 pass without warning/incompatibility
    label_compatible = 1 if (voltage_compatible and logic_compatible and interface_compatible and pin_compatible and current_compatible) else 0

    explanation = " ".join(warnings) if warnings else "Directly compatible. Voltage rails, logic levels, pin allocations, and interfaces match seamlessly."
    solution_text = " ".join(solutions) if solutions else "No additional conditioning components required."

    return {
        "component_a_id": comp_a["component_id"],
        "component_a_name": comp_a["name"],
        "component_b_id": comp_b["component_id"],
        "component_b_name": comp_b["name"],
        "voltage_compatible": voltage_compatible,
        "current_compatible": current_compatible,
        "logic_compatible": logic_compatible,
        "interface_compatible": interface_compatible,
        "pin_compatible": pin_compatible,
        "compatible": label_compatible,
        "status": status,
        "warning_reason": explanation,
        "suggested_solution": solution_text
    }


def generate_compatibility_dataset():
    components_path = os.path.join(PROCESSED_DIR, "components.csv")
    if not os.path.exists(components_path):
        raise FileNotFoundError(f"{components_path} not found. Run clean_components.py first.")

    df_comp = pd.read_csv(components_path)
    records = []

    mcus = df_comp[df_comp["category"].isin(["Microcontroller", "Single Board Computer"])].to_dict("records")
    peripherals = df_comp[~df_comp["category"].isin(["Microcontroller", "Single Board Computer"])].to_dict("records")

    print(f"Generating pairs across {len(mcus)} MCUs and {len(peripherals)} Peripherals...")

    # Pair each MCU with all peripherals
    for mcu in mcus:
        for p in peripherals:
            res = check_pairwise_compatibility(mcu, p)
            records.append(res)

    # Also pair MCUs with MCUs (e.g. ESP32 + Arduino Uno or RPi + Arduino over UART/I2C)
    for i in range(len(mcus)):
        for j in range(i + 1, len(mcus)):
            res = check_pairwise_compatibility(mcus[i], mcus[j])
            records.append(res)

    # Also pair representative peripherals with each other (e.g. Sensor with Display on I2C bus)
    for i in range(len(peripherals)):
        for j in range(i + 1, min(i + 20, len(peripherals))):
            res = check_pairwise_compatibility(peripherals[i], peripherals[j])
            records.append(res)

    df_compat = pd.DataFrame(records)
    compat_csv_path = os.path.join(PROCESSED_DIR, "compatibility.csv")
    df_compat.to_csv(compat_csv_path, index=False)

    print(f"Generated {len(df_compat)} compatibility pairs exported to {compat_csv_path}")
    print("Class distribution:")
    print(df_compat["status"].value_counts())
    print("\nBinary compatible distribution (1=Fully Compatible, 0=Warning/Incompatible):")
    print(df_compat["compatible"].value_counts())


if __name__ == "__main__":
    generate_compatibility_dataset()
