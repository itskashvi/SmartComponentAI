"""
models/taxonomy.py
Functional classification and taxonomy for electronic components.
Distinguishes component roles to prevent duplicate sensors or redundant modules
of the same kind in recommendations and hardware setups.
"""

# Map each component ID to its precise functional role/kind
FUNCTIONAL_KIND_MAP = {
    # --- Environmental & Climate Sensors ---
    "bme280": "ambient_climate",
    "bmp280": "ambient_climate",
    "dht11": "ambient_climate",
    "dht22": "ambient_climate",
    "ds18b20": "ambient_climate",
    "sht31_d": "ambient_climate",
    "aht20": "ambient_climate",
    "bmp180": "ambient_climate",
    "lm35": "ambient_climate",

    # --- Soil & Water Sensors ---
    "capacitive_soil": "soil_moisture",
    "resistive_soil": "soil_moisture",
    "water_level_sensor": "water_level",

    # --- Gas & Air Quality Sensors ---
    "scd30": "air_quality_co2",
    "scd41": "air_quality_co2",
    "mq2": "gas_smoke",
    "mq135": "air_quality_hazardous",
    "mq7": "carbon_monoxide",
    "mq3": "alcohol_gas",
    "pms5003": "particulate_matter",

    # --- Distance & Proximity Sensors ---
    "hc_sr04": "ultrasonic_distance",
    "hc_sr04p": "ultrasonic_distance",
    "vl53l0x": "laser_distance",
    "vl53l1x": "laser_distance",
    "sharp_gp2y0a21": "ir_distance",

    # --- Motion, IMU & Orientation ---
    "mpu6050": "imu_motion",
    "bno055": "imu_orientation",
    "adxl345": "accelerometer",
    "sw420": "vibration_sensor",

    # --- Presence & Human Motion ---
    "hc_sr501": "pir_motion",
    "rcwl_0516": "radar_presence",

    # --- Optical & Ambient Light ---
    "ldr_module": "light_intensity",
    "bh1750": "light_intensity",
    "tsl2561": "light_intensity",
    "apds9960": "gesture_proximity",

    # --- Line Tracking & Infrared ---
    "tcrt5000": "line_tracking",

    # --- Navigation & Location ---
    "neo_6m_gps": "gps_navigation",
    "neo_m8n_gps": "gps_navigation",

    # --- Magnetic & RPM ---
    "a3144_hall": "hall_magnetic",

    # --- Biometrics & Health ---
    "max30102": "pulse_oximeter",
    "ad8232": "ecg_heart",
    "as608_fingerprint": "fingerprint",

    # --- Identification & Access ---
    "rc522_rfid": "rfid_reader",
    "pn532_nfc": "nfc_reader",

    # --- Camera & Vision ---
    "ov7670": "camera_module",
    "esp32_cam": "camera_board",

    # --- Force & Weight ---
    "hx711_loadcell": "load_cell_scale",

    # --- Sound & Acoustic ---
    "ky038_sound": "sound_microphone",

    # --- Displays: OLED ---
    "ssd1306_oled": "oled_display",
    "sh1106_oled": "oled_display",

    # --- Displays: Character LCD ---
    "lcd1602_i2c": "character_lcd",
    "lcd2004_i2c": "character_lcd",
    "lcd1602_parallel": "character_lcd",

    # --- Displays: Graphic TFT & E-Paper ---
    "ili9341_tft": "graphic_tft_display",
    "st7789_ips": "graphic_tft_display",
    "epaper_29": "epaper_display",

    # --- Displays: Segment & LED Matrix ---
    "max7219_matrix": "matrix_display",
    "tm1637_display": "segment_display",
    "ws2812b_ring": "rgb_led_strip",
    "rgb_led_module": "rgb_indicator",

    # --- Actuators: Servos ---
    "sg90_servo": "servo_motor",
    "mg996r_servo": "servo_motor",

    # --- Actuators: DC Motor Drivers ---
    "l298n_driver": "dc_motor_driver",
    "tb6612fng": "dc_motor_driver",
    "l293d_shield": "dc_motor_driver",

    # --- Actuators: Stepper Drivers & Steppers ---
    "a4988_driver": "stepper_driver",
    "drv8825_driver": "stepper_driver",
    "stepper_28byj48": "stepper_motor",

    # --- Actuators: Relays & Switches ---
    "relay_1ch_5v": "relay_switch",
    "relay_2ch_5v": "relay_switch",
    "relay_4ch_5v": "relay_switch",
    "relay_1ch_3v": "relay_switch",
    "solenoid_valve_12v": "solenoid_valve",
    "irf520_mosfet": "mosfet_switch",

    # --- Audio & Sound Generation ---
    "active_buzzer": "piezo_buzzer",
    "passive_buzzer": "piezo_buzzer",
    "vibration_motor": "vibration_actuator",
    "dfplayer_mini": "audio_player",
    "max98357a_amp": "audio_amplifier",

    # --- Wireless & Communication ---
    "nrf24l01": "rf_transceiver",
    "nrf24l01_pa_lna": "rf_transceiver",
    "hc05_bluetooth": "bluetooth_serial",
    "hc06_bluetooth": "bluetooth_serial",
    "hm10_ble": "bluetooth_ble",
    "sim800l_gsm": "gsm_cellular",
    "sim900a_gsm": "gsm_cellular",
    "sx1278_lora": "lora_wireless",
    "esp01_wifi": "wifi_serial",
    "w5500_ethernet": "wired_ethernet",
    "enc28j60_ethernet": "wired_ethernet",
    "mcp2515_can": "can_bus",

    # --- Power Management ---
    "tp4056_charger": "battery_charger",
    "lm2596_buck": "step_down_regulator",
    "xl6009_boost": "step_up_converter",
    "mt3608_boost": "step_up_converter",
    "ams1117_3v3": "ldo_regulator",
    "mb102_breadboard_power": "breadboard_power",

    # --- Converters & Expansion ---
    "logic_level_converter": "level_converter",
    "ads1115_adc": "adc_module",
    "mcp4725_dac": "dac_module",
    "pcf8574_io": "io_expander",
    "tca9548a_mux": "i2c_multiplexer",
    "ds3231_rtc": "rtc_timer",
    "ds1307_rtc": "rtc_timer",
    "ky040_encoder": "rotary_encoder",
    "keypad_4x4": "matrix_keypad",
    "sd_card_module": "sd_storage"
}

FUNCTIONAL_KIND_LABELS = {
    "ambient_climate": "Ambient Climate & Temperature",
    "soil_moisture": "Soil Moisture",
    "water_level": "Liquid Level",
    "air_quality_co2": "NDIR CO2 & Air Quality",
    "gas_smoke": "Combustible Gas & Smoke",
    "air_quality_hazardous": "Hazardous Gas & Air Quality",
    "carbon_monoxide": "Carbon Monoxide (CO)",
    "alcohol_gas": "Alcohol Vapor",
    "particulate_matter": "Laser Dust PM2.5",
    "ultrasonic_distance": "Ultrasonic Distance",
    "laser_distance": "Laser ToF Distance",
    "ir_distance": "Optical IR Distance",
    "imu_motion": "6-DOF IMU Motion",
    "imu_orientation": "9-DOF Absolute Orientation",
    "accelerometer": "3-Axis Accelerometer",
    "vibration_sensor": "Vibration & Shock",
    "pir_motion": "PIR Infrared Motion",
    "radar_presence": "Doppler Radar Presence",
    "light_intensity": "Ambient Light / Lux",
    "gesture_proximity": "Gesture & Proximity",
    "line_tracking": "Infrared Line Tracking",
    "gps_navigation": "GPS / Satellite Navigation",
    "hall_magnetic": "Hall Effect Magnetic",
    "pulse_oximeter": "Heart Pulse & SpO2",
    "ecg_heart": "Single Lead ECG",
    "fingerprint": "Optical Fingerprint",
    "rfid_reader": "RFID Reader",
    "nfc_reader": "NFC Reader",
    "camera_module": "Camera Video Module",
    "camera_board": "ESP32 Camera DevBoard",
    "load_cell_scale": "Strain Gauge Load Cell",
    "sound_microphone": "Acoustic Microphone",
    "oled_display": "OLED Display",
    "character_lcd": "Character LCD Display",
    "graphic_tft_display": "Color Graphic TFT/IPS Display",
    "epaper_display": "E-Paper Display",
    "matrix_display": "Dot Matrix Display",
    "segment_display": "7-Segment Display",
    "rgb_led_strip": "Addressable RGB LED",
    "rgb_indicator": "RGB Indicator LED",
    "servo_motor": "Servo Motor",
    "dc_motor_driver": "DC Motor Driver",
    "stepper_driver": "Stepper Motor Driver",
    "stepper_motor": "Stepper Motor",
    "relay_switch": "Relay Switch Module",
    "solenoid_valve": "Solenoid Valve",
    "mosfet_switch": "MOSFET Switch Driver",
    "piezo_buzzer": "Piezo Buzzer",
    "vibration_actuator": "Haptic Vibration Motor",
    "audio_player": "MP3 Sound Player",
    "audio_amplifier": "I2S Audio Amplifier",
    "rf_transceiver": "2.4GHz RF Transceiver",
    "bluetooth_serial": "Bluetooth Serial (SPP)",
    "bluetooth_ble": "Bluetooth Low Energy (BLE)",
    "gsm_cellular": "GSM / GPRS Cellular",
    "lora_wireless": "LoRa Long-Range Wireless",
    "wifi_serial": "Serial WiFi Addon",
    "wired_ethernet": "Wired SPI Ethernet",
    "can_bus": "CAN Bus Transceiver",
    "battery_charger": "Lithium Battery Charger",
    "step_down_regulator": "Buck Step-Down Regulator",
    "step_up_converter": "Boost Step-Up Converter",
    "ldo_regulator": "3.3V LDO Voltage Regulator",
    "breadboard_power": "Breadboard Power Supply",
    "level_converter": "Logic Level Converter (3.3V-5V)",
    "adc_module": "16-Bit I2C ADC",
    "dac_module": "12-Bit I2C DAC",
    "io_expander": "I2C I/O Expander",
    "i2c_multiplexer": "I2C Bus Multiplexer",
    "rtc_timer": "Real-Time Clock (RTC)",
    "rotary_encoder": "Rotary Encoder Knob",
    "matrix_keypad": "Matrix Keypad",
    "sd_storage": "MicroSD Storage Module"
}


def get_functional_kind(component_id):
    """Returns the standardized functional role/kind for a component ID."""
    if not component_id:
        return "other"
    cid = str(component_id).strip().lower()
    return FUNCTIONAL_KIND_MAP.get(cid, "other")


def get_functional_kind_label(component_id):
    """Returns human-readable role name for a component."""
    kind = get_functional_kind(component_id)
    return FUNCTIONAL_KIND_LABELS.get(kind, kind.replace("_", " ").title())


def are_same_functional_kind(comp_a_id, comp_b_id):
    """Returns True if two components fulfill the exact same primary functional role."""
    kind_a = get_functional_kind(comp_a_id)
    kind_b = get_functional_kind(comp_b_id)
    if kind_a == "other" or kind_b == "other":
        return False
    return kind_a == kind_b
