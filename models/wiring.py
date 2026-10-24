"""
models/wiring.py
Automated Pinout & Wiring Table Generator for SmartComponentAI.
Dynamically assigns microcontroller pins, maps communication buses (I2C, SPI, UART, ADC, PWM, GPIO),
detects pin conflicts, and generates circuit-level electrical wiring instructions.
"""

import os
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

# ==============================================================================
# 1. Microcontroller Hardware Pinout Profiles
# ==============================================================================

MCU_PINOUT_PROFILES = {
    "esp32": {
        "name": "ESP32 DevKit V1 (ESP-WROOM-32)",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3V3 (Pin 1)",
            "5v": "VIN (5V Rail)",
            "gnd": "GND"
        },
        "i2c": {"sda": "GPIO 21", "scl": "GPIO 22"},
        "spi": {"mosi": "GPIO 23", "miso": "GPIO 19", "sck": "GPIO 18"},
        "spi_cs_pool": ["GPIO 5", "GPIO 15", "GPIO 2", "GPIO 4"],
        "uart": {"tx": "GPIO 17 (TX2)", "rx": "GPIO 16 (RX2)"},
        "adc_pool": ["GPIO 32 (ADC1_CH4)", "GPIO 33 (ADC1_CH5)", "GPIO 34 (ADC1_CH6)", "GPIO 35 (ADC1_CH7)", "GPIO 36 (VP)", "GPIO 39 (VN)"],
        "pwm_pool": ["GPIO 4", "GPIO 13", "GPIO 14", "GPIO 27", "GPIO 25", "GPIO 26"],
        "gpio_pool": ["GPIO 12", "GPIO 13", "GPIO 14", "GPIO 27", "GPIO 25", "GPIO 26", "GPIO 32", "GPIO 33"],
        "has_onboard_adc": True
    },
    "esp32_s3": {
        "name": "ESP32-S3 DevKit",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3V3",
            "5v": "5V (VBUS)",
            "gnd": "GND"
        },
        "i2c": {"sda": "GPIO 8", "scl": "GPIO 9"},
        "spi": {"mosi": "GPIO 11", "miso": "GPIO 13", "sck": "GPIO 12"},
        "spi_cs_pool": ["GPIO 10", "GPIO 14", "GPIO 15"],
        "uart": {"tx": "GPIO 43", "rx": "GPIO 44"},
        "adc_pool": ["GPIO 1 (ADC1_CH0)", "GPIO 2 (ADC1_CH1)", "GPIO 3 (ADC1_CH2)", "GPIO 4 (ADC1_CH3)", "GPIO 5 (ADC1_CH4)"],
        "pwm_pool": ["GPIO 7", "GPIO 15", "GPIO 16", "GPIO 17", "GPIO 18"],
        "gpio_pool": ["GPIO 7", "GPIO 15", "GPIO 16", "GPIO 17", "GPIO 18", "GPIO 19", "GPIO 20"],
        "has_onboard_adc": True
    },
    "arduino_uno": {
        "name": "Arduino Uno R3",
        "logic_voltage": 5.0,
        "power_rails": {
            "3v3": "3.3V (Max 50mA)",
            "5v": "5V",
            "gnd": "GND"
        },
        "i2c": {"sda": "A4 (SDA)", "scl": "A5 (SCL)"},
        "spi": {"mosi": "D11 (MOSI)", "miso": "D12 (MISO)", "sck": "D13 (SCK)"},
        "spi_cs_pool": ["D10", "D9", "D8", "D7"],
        "uart": {"tx": "D1 (TX)", "rx": "D0 (RX)"},
        "adc_pool": ["A0", "A1", "A2", "A3"],
        "pwm_pool": ["D3 (PWM)", "D5 (PWM)", "D6 (PWM)", "D9 (PWM)", "D10 (PWM)"],
        "gpio_pool": ["D2", "D4", "D7", "D8", "D12", "D13"],
        "has_onboard_adc": True
    },
    "arduino_nano": {
        "name": "Arduino Nano",
        "logic_voltage": 5.0,
        "power_rails": {
            "3v3": "3.3V",
            "5v": "5V",
            "gnd": "GND"
        },
        "i2c": {"sda": "A4 (SDA)", "scl": "A5 (SCL)"},
        "spi": {"mosi": "D11 (MOSI)", "miso": "D12 (MISO)", "sck": "D13 (SCK)"},
        "spi_cs_pool": ["D10", "D9", "D8", "D7"],
        "uart": {"tx": "D1 (TX)", "rx": "D0 (RX)"},
        "adc_pool": ["A0", "A1", "A2", "A3", "A6", "A7"],
        "pwm_pool": ["D3 (PWM)", "D5 (PWM)", "D6 (PWM)", "D9 (PWM)", "D10 (PWM)"],
        "gpio_pool": ["D2", "D4", "D7", "D8", "D12", "D13"],
        "has_onboard_adc": True
    },
    "arduino_mega": {
        "name": "Arduino Mega 2560",
        "logic_voltage": 5.0,
        "power_rails": {
            "3v3": "3.3V",
            "5v": "5V",
            "gnd": "GND"
        },
        "i2c": {"sda": "D20 (SDA)", "scl": "D21 (SCL)"},
        "spi": {"mosi": "D51 (MOSI)", "miso": "D50 (MISO)", "sck": "D52 (SCK)"},
        "spi_cs_pool": ["D53 (SS)", "D49", "D48", "D47", "D46"],
        "uart": {"tx": "D18 (TX1)", "rx": "D19 (RX1)"},
        "adc_pool": [f"A{i}" for i in range(16)],
        "pwm_pool": [f"D{i} (PWM)" for i in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]],
        "gpio_pool": [f"D{i}" for i in range(22, 50)],
        "has_onboard_adc": True
    },
    "rpi_pico": {
        "name": "Raspberry Pi Pico (RP2040)",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3V3 (Pin 36)",
            "5v": "VBUS (5V, Pin 40)",
            "gnd": "GND (Pin 38)"
        },
        "i2c": {"sda": "GP4 (Pin 6)", "scl": "GP5 (Pin 7)"},
        "spi": {"mosi": "GP19 (Pin 25)", "miso": "GP16 (Pin 21)", "sck": "GP18 (Pin 24)"},
        "spi_cs_pool": ["GP17 (Pin 22)", "GP13 (Pin 17)", "GP9 (Pin 12)"],
        "uart": {"tx": "GP0 (Pin 1)", "rx": "GP1 (Pin 2)"},
        "adc_pool": ["GP26 (ADC0, Pin 31)", "GP27 (ADC1, Pin 32)", "GP28 (ADC2, Pin 34)"],
        "pwm_pool": ["GP2 (Pin 4)", "GP3 (Pin 5)", "GP6 (Pin 9)", "GP7 (Pin 10)", "GP8 (Pin 11)"],
        "gpio_pool": ["GP10 (Pin 14)", "GP11 (Pin 15)", "GP12 (Pin 16)", "GP14 (Pin 19)", "GP15 (Pin 20)"],
        "has_onboard_adc": True
    },
    "rpi_pico_w": {
        "name": "Raspberry Pi Pico W",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3V3 (Pin 36)",
            "5v": "VBUS (5V, Pin 40)",
            "gnd": "GND (Pin 38)"
        },
        "i2c": {"sda": "GP4 (Pin 6)", "scl": "GP5 (Pin 7)"},
        "spi": {"mosi": "GP19 (Pin 25)", "miso": "GP16 (Pin 21)", "sck": "GP18 (Pin 24)"},
        "spi_cs_pool": ["GP17 (Pin 22)", "GP13 (Pin 17)", "GP9 (Pin 12)"],
        "uart": {"tx": "GP0 (Pin 1)", "rx": "GP1 (Pin 2)"},
        "adc_pool": ["GP26 (ADC0, Pin 31)", "GP27 (ADC1, Pin 32)", "GP28 (ADC2, Pin 34)"],
        "pwm_pool": ["GP2 (Pin 4)", "GP3 (Pin 5)", "GP6 (Pin 9)", "GP7 (Pin 10)", "GP8 (Pin 11)"],
        "gpio_pool": ["GP10 (Pin 14)", "GP11 (Pin 15)", "GP12 (Pin 16)", "GP14 (Pin 19)", "GP15 (Pin 20)"],
        "has_onboard_adc": True
    },
    "raspberry_pi_4": {
        "name": "Raspberry Pi 4 Model B (40-Pin Header)",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3V3 (Pin 1)",
            "5v": "5V (Pin 2)",
            "gnd": "GND (Pin 6)"
        },
        "i2c": {"sda": "GPIO 2 / SDA (Pin 3)", "scl": "GPIO 3 / SCL (Pin 5)"},
        "spi": {"mosi": "GPIO 10 / MOSI (Pin 19)", "miso": "GPIO 9 / MISO (Pin 21)", "sck": "GPIO 11 / SCLK (Pin 23)"},
        "spi_cs_pool": ["GPIO 8 / CE0 (Pin 24)", "GPIO 7 / CE1 (Pin 26)"],
        "uart": {"tx": "GPIO 14 / TXD (Pin 8)", "rx": "GPIO 15 / RXD (Pin 10)"},
        "adc_pool": [],  # Raspberry Pi 4 has NO onboard ADC!
        "pwm_pool": ["GPIO 18 / PWM0 (Pin 12)", "GPIO 19 / PWM1 (Pin 35)", "GPIO 12 (Pin 32)"],
        "gpio_pool": ["GPIO 4 (Pin 7)", "GPIO 17 (Pin 11)", "GPIO 27 (Pin 13)", "GPIO 22 (Pin 15)", "GPIO 23 (Pin 16)", "GPIO 24 (Pin 18)", "GPIO 25 (Pin 22)"],
        "has_onboard_adc": False
    },
    "stm32_bluepill": {
        "name": "STM32 Blue Pill (STM32F103C8T6)",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3.3V Rail",
            "5v": "5V Rail",
            "gnd": "GND"
        },
        "i2c": {"sda": "PB7 (I2C1 SDA)", "scl": "PB6 (I2C1 SCL)"},
        "spi": {"mosi": "PA7 (SPI1 MOSI)", "miso": "PA6 (SPI1 MISO)", "sck": "PA5 (SPI1 SCK)"},
        "spi_cs_pool": ["PA4 (NSS)", "PB0", "PB1"],
        "uart": {"tx": "PA9 (USART1 TX)", "rx": "PA10 (USART1 RX)"},
        "adc_pool": ["PA0 (ADC1)", "PA1 (ADC2)", "PA2 (ADC3)", "PA3 (ADC4)"],
        "pwm_pool": ["PA8 (PWM)", "PA1 (PWM)", "PA2 (PWM)", "PB6 (PWM)", "PB7 (PWM)"],
        "gpio_pool": ["PB10", "PB11", "PB12", "PB13", "PB14", "PB15", "PA11", "PA12"],
        "has_onboard_adc": True
    },
    "esp8266_nodemcu": {
        "name": "ESP8266 NodeMCU V2",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3V3",
            "5v": "VIN (5V)",
            "gnd": "GND"
        },
        "i2c": {"sda": "D2 (GPIO 4)", "scl": "D1 (GPIO 5)"},
        "spi": {"mosi": "D7 (GPIO 13)", "miso": "D6 (GPIO 12)", "sck": "D5 (GPIO 14)"},
        "spi_cs_pool": ["D8 (GPIO 15)", "D4 (GPIO 2)"],
        "uart": {"tx": "D4 (GPIO 2)", "rx": "D3 (GPIO 0)"},
        "adc_pool": ["A0 (ADC0, Max 1.0V/3.3V)"],
        "pwm_pool": ["D2 (GPIO 4)", "D5 (GPIO 14)", "D6 (GPIO 12)", "D7 (GPIO 13)"],
        "gpio_pool": ["D0 (GPIO 16)", "D3 (GPIO 0)", "D4 (GPIO 2)"],
        "has_onboard_adc": True
    },
    "esp32_cam": {
        "name": "ESP32-CAM (with OV2640)",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3V3",
            "5v": "5V",
            "gnd": "GND"
        },
        "i2c": {"sda": "GPIO 14", "scl": "GPIO 15"},
        "spi": {"mosi": "GPIO 13", "miso": "GPIO 12", "sck": "GPIO 14"},
        "spi_cs_pool": ["GPIO 15"],
        "uart": {"tx": "U0TXD (GPIO 1)", "rx": "U0RXD (GPIO 3)"},
        "adc_pool": ["GPIO 2 (ADC)", "GPIO 4 (ADC)"],
        "pwm_pool": ["GPIO 2", "GPIO 4", "GPIO 12", "GPIO 13"],
        "gpio_pool": ["GPIO 2", "GPIO 4", "GPIO 12", "GPIO 13", "GPIO 14", "GPIO 15", "GPIO 16"],
        "has_onboard_adc": True
    },
    "rpi_zero_2w": {
        "name": "Raspberry Pi Zero 2 W (40-Pin Header)",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3V3 (Pin 1)",
            "5v": "5V (Pin 2)",
            "gnd": "GND (Pin 6)"
        },
        "i2c": {"sda": "GPIO 2 / SDA (Pin 3)", "scl": "GPIO 3 / SCL (Pin 5)"},
        "spi": {"mosi": "GPIO 10 / MOSI (Pin 19)", "miso": "GPIO 9 / MISO (Pin 21)", "sck": "GPIO 11 / SCLK (Pin 23)"},
        "spi_cs_pool": ["GPIO 8 / CE0 (Pin 24)", "GPIO 7 / CE1 (Pin 26)"],
        "uart": {"tx": "GPIO 14 / TXD (Pin 8)", "rx": "GPIO 15 / RXD (Pin 10)"},
        "adc_pool": [],
        "pwm_pool": ["GPIO 18 / PWM0 (Pin 12)", "GPIO 19 / PWM1 (Pin 35)"],
        "gpio_pool": ["GPIO 4 (Pin 7)", "GPIO 17 (Pin 11)", "GPIO 27 (Pin 13)", "GPIO 22 (Pin 15)", "GPIO 23 (Pin 16)", "GPIO 24 (Pin 18)", "GPIO 25 (Pin 22)"],
        "has_onboard_adc": False
    },
    "teensy_40": {
        "name": "Teensy 4.0 (ARM Cortex-M7)",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3.3V",
            "5v": "VIN (5V USB)",
            "gnd": "GND"
        },
        "i2c": {"sda": "Pin 18 (SDA0)", "scl": "Pin 19 (SCL0)"},
        "spi": {"mosi": "Pin 11 (MOSI0)", "miso": "Pin 12 (MISO0)", "sck": "Pin 13 (SCK0)"},
        "spi_cs_pool": ["Pin 10 (CS0)", "Pin 9", "Pin 0"],
        "uart": {"tx": "Pin 1 (TX1)", "rx": "Pin 0 (RX1)"},
        "adc_pool": ["Pin 14 (A0)", "Pin 15 (A1)", "Pin 16 (A2)", "Pin 17 (A3)", "Pin 18 (A4)", "Pin 19 (A5)", "Pin 20 (A6)", "Pin 21 (A7)", "Pin 22 (A8)", "Pin 23 (A9)"],
        "pwm_pool": ["Pin 2 (PWM)", "Pin 3 (PWM)", "Pin 4 (PWM)", "Pin 5 (PWM)", "Pin 6 (PWM)", "Pin 7 (PWM)", "Pin 8 (PWM)", "Pin 9 (PWM)"],
        "gpio_pool": ["Pin 2", "Pin 3", "Pin 4", "Pin 5", "Pin 6", "Pin 7", "Pin 8", "Pin 9", "Pin 10", "Pin 20", "Pin 21", "Pin 22", "Pin 23"],
        "has_onboard_adc": True
    },
    "microbit_v2": {
        "name": "BBC micro:bit v2",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3V (Edge Pad)",
            "5v": "USB (5V, regulated to 3.3V internally)",
            "gnd": "GND (Edge Pad)"
        },
        "i2c": {"sda": "Pin 20 (I2C SDA)", "scl": "Pin 19 (I2C SCL)"},
        "spi": {"mosi": "Pin 15 (MOSI)", "miso": "Pin 14 (MISO)", "sck": "Pin 13 (SCK)"},
        "spi_cs_pool": ["Pin 16"],
        "uart": {"tx": "Pin 0 (TX)", "rx": "Pin 1 (RX)"},
        "adc_pool": ["Pin 0 (ADC)", "Pin 1 (ADC)", "Pin 2 (ADC)"],
        "pwm_pool": ["Pin 0 (PWM)", "Pin 1 (PWM)", "Pin 2 (PWM)"],
        "gpio_pool": ["Pin 0", "Pin 1", "Pin 2", "Pin 8", "Pin 9", "Pin 12"],
        "has_onboard_adc": True
    },
    "attiny85_digispark": {
        "name": "Digispark ATtiny85",
        "logic_voltage": 5.0,
        "power_rails": {
            "3v3": "N/A (5V only board)",
            "5v": "5V (USB)",
            "gnd": "GND"
        },
        "i2c": {"sda": "PB0 (Pin 0 / SDA)", "scl": "PB2 (Pin 2 / SCL)"},
        "spi": {"mosi": "PB0 (Pin 0 / MOSI)", "miso": "PB1 (Pin 1 / MISO)", "sck": "PB2 (Pin 2 / SCK)"},
        "spi_cs_pool": ["PB3 (Pin 3)"],
        "uart": {"tx": "PB1 (Pin 1, Software Serial)", "rx": "PB0 (Pin 0, Software Serial)"},
        "adc_pool": ["PB2 (ADC1)", "PB3 (ADC3)", "PB4 (ADC2)"],
        "pwm_pool": ["PB0 (PWM)", "PB1 (PWM)"],
        "gpio_pool": ["PB0 (Pin 0)", "PB1 (Pin 1)", "PB2 (Pin 2)", "PB3 (Pin 3)", "PB4 (Pin 4)", "PB5 (Pin 5, Reset)"],
        "has_onboard_adc": True
    },
    "seeed_xiao_esp32c3": {
        "name": "Seeed Studio XIAO ESP32-C3",
        "logic_voltage": 3.3,
        "power_rails": {
            "3v3": "3V3",
            "5v": "5V (VUSB)",
            "gnd": "GND"
        },
        "i2c": {"sda": "D4 (GPIO 6, SDA)", "scl": "D5 (GPIO 7, SCL)"},
        "spi": {"mosi": "D10 (GPIO 10, MOSI)", "miso": "D9 (GPIO 9, MISO)", "sck": "D8 (GPIO 8, SCK)"},
        "spi_cs_pool": ["D7 (GPIO 20, CS)"],
        "uart": {"tx": "D6 (GPIO 21, TX)", "rx": "D7 (GPIO 20, RX)"},
        "adc_pool": ["D0 (GPIO 2, ADC)", "D1 (GPIO 3, ADC)", "D2 (GPIO 4, ADC)", "D3 (GPIO 5, ADC)"],
        "pwm_pool": ["D0 (GPIO 2)", "D1 (GPIO 3)", "D2 (GPIO 4)"],
        "gpio_pool": ["D0 (GPIO 2)", "D1 (GPIO 3)", "D2 (GPIO 4)", "D3 (GPIO 5)", "D4 (GPIO 6)", "D5 (GPIO 7)"],
        "has_onboard_adc": True
    }
}


# ==============================================================================
# 2. Curated Peripheral Module Pinout Definitions
# ==============================================================================

PERIPHERAL_PINOUT_DB = {
    # Climate & Environmental
    "bme280": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "Supply 3.3V (tolerant up to 3.6V)."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C Data line with pull-up."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C Clock line."}
    ],
    "bmp280": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "Supply 3.3V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C Data line."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C Clock line."}
    ],
    "aht20": [
        {"pin": "VIN", "type": "POWER_FLEX", "notes": "Supply 2.0V - 5.5V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C Data line."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C Clock line."}
    ],
    "sht31_d": [
        {"pin": "VIN", "type": "POWER_FLEX", "notes": "Supply 2.4V - 5.5V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C Data line."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C Clock line."}
    ],
    "dht11": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "Supply 3.3V or 5V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "DATA", "type": "DIGITAL_INOUT", "notes": "Requires 10k-ohm pull-up resistor to VCC if not built into PCB module."}
    ],
    "dht22": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "Supply 3.3V or 5V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "DATA", "type": "DIGITAL_INOUT", "notes": "Requires 10k-ohm pull-up resistor to VCC."}
    ],
    "ds18b20": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "Supply 3.0V - 5.5V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "DATA", "type": "ONE_WIRE", "notes": "Requires a 4.7k-ohm pull-up resistor connected between DATA and VCC."}
    ],

    # Distance & Proximity
    "hc_sr04": [
        {"pin": "VCC", "type": "POWER_5V", "notes": "Requires 5V power supply rail for ultrasonic transducer."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "Trig", "type": "DIGITAL_IN", "notes": "Trigger pulse output from MCU (10 microsecond HIGH pulse)."},
        {"pin": "Echo", "type": "DIGITAL_OUT_5V", "notes": "Echo pulse 5V output. MUST use voltage divider (1k/2k) on 3.3V MCUs!"}
    ],
    "jsn_sr04t": [
        {"pin": "5V", "type": "POWER_5V", "notes": "Waterproof ultrasonic transducer; requires 5V rail."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "Trig", "type": "DIGITAL_IN", "notes": "Trigger pulse from MCU."},
        {"pin": "Echo", "type": "DIGITAL_OUT_5V", "notes": "Echo signal. Step down to 3.3V logic on ESP32/Pico/RPi4."}
    ],
    "vl53l0x": [
        {"pin": "VIN", "type": "POWER_FLEX", "notes": "ToF Laser Ranging sensor; 2.8V - 5V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C Data line."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C Clock line."}
    ],

    # Displays
    "ssd1306_oled": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "Supply 3.3V (recommended) or 5V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C bus. Address 0x3C."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C bus clock."}
    ],
    "sh1106_oled": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "Supply 3.3V or 5V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C bus. Address 0x3C."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C bus clock."}
    ],
    "lcd1602_i2c": [
        {"pin": "VCC", "type": "POWER_5V", "notes": "Standard HD44780 LCD display requires 5V for backlight & contrast."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "PCF8574 I2C backpack. Address typically 0x27 or 0x3F."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C Clock line."}
    ],
    "lcd2004_i2c": [
        {"pin": "VCC", "type": "POWER_5V", "notes": "Requires 5V rail for 20x4 display & backlight."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C backpack interface."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C bus clock."}
    ],

    # Gas & Air Quality
    "mq2": [
        {"pin": "VCC", "type": "POWER_5V", "notes": "Requires 5V rail to drive internal gas heating coil (~150mA)."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "AO", "type": "ANALOG_OUT", "notes": "Analog concentration voltage output (0V - 5V). Connect to ADC pin."}
    ],
    "mq135": [
        {"pin": "VCC", "type": "POWER_5V", "notes": "Requires 5V rail for internal sensor heating element."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "AO", "type": "ANALOG_OUT", "notes": "Analog air quality signal. Connect to dedicated ADC pin."}
    ],
    "scd30": [
        {"pin": "VDD", "type": "POWER_FLEX", "notes": "NDIR CO2 Sensor; 3.3V - 5.5V supply."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C Data line. Default address 0x61."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C Clock line."}
    ],
    "pms5003": [
        {"pin": "VCC", "type": "POWER_5V", "notes": "Laser particulate sensor requires 5V for internal fan."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "TX", "type": "UART_TX", "notes": "Sensor UART TX (3.3V logic) connects to MCU RX."},
        {"pin": "RX", "type": "UART_RX", "notes": "Sensor UART RX connects to MCU TX."}
    ],

    # Soil & Environmental
    "capacitive_soil": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "Supply 3.3V to 5V (corrosion resistant 555-timer circuit)."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "AOUT", "type": "ANALOG_OUT", "notes": "Analog moisture reading. Connect to ADC pin."}
    ],
    "resistive_soil": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "Supply 3.3V or 5V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "AO", "type": "ANALOG_OUT", "notes": "Analog moisture level to ADC pin."}
    ],
    "water_level_sensor": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "Supply 3.3V - 5V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SIGNAL", "type": "ANALOG_OUT", "notes": "Analog liquid level depth to ADC pin."}
    ],

    # Actuators & Motor Drivers
    "sg90_servo": [
        {"pin": "VCC (+)", "type": "POWER_EXT", "notes": "Power from dedicated 5V external rail (do not draw peak 500mA from MCU 3.3V!)."},
        {"pin": "GND (-)", "type": "GROUND", "notes": "Tie external GND to MCU GND."},
        {"pin": "PWM (Signal)", "type": "PWM_IN", "notes": "50Hz PWM control signal (1ms - 2ms duty cycle)."}
    ],
    "mg996r_servo": [
        {"pin": "VCC (+)", "type": "POWER_EXT", "notes": "High-torque servo draws up to 1.5A stall. MUST use dedicated external 5V-6V supply!"},
        {"pin": "GND (-)", "type": "GROUND", "notes": "Connect external supply GND to MCU GND."},
        {"pin": "Signal", "type": "PWM_IN", "notes": "PWM position control."}
    ],
    "l298n_driver": [
        {"pin": "12V", "type": "POWER_EXT", "notes": "External DC motor battery/adapter supply (7V - 35V)."},
        {"pin": "GND", "type": "GROUND", "notes": "Common GND tied to MCU GND."},
        {"pin": "5V Out", "type": "POWER_5V", "notes": "5V regulated output (can power MCU if 5V regulator jumper is fitted)."},
        {"pin": "IN1", "type": "DIGITAL_IN", "notes": "Motor A Direction control GPIO."},
        {"pin": "IN2", "type": "DIGITAL_IN", "notes": "Motor A Direction control GPIO."},
        {"pin": "ENA", "type": "PWM_IN", "notes": "Motor A Speed control (PWM). Remove jumper to enable PWM control."},
        {"pin": "IN3", "type": "DIGITAL_IN", "notes": "Motor B Direction control GPIO."},
        {"pin": "IN4", "type": "DIGITAL_IN", "notes": "Motor B Direction control GPIO."}
    ],
    "relay_1ch": [
        {"pin": "VCC", "type": "POWER_5V", "notes": "Relay coil requires 5V supply."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "IN", "type": "DIGITAL_IN", "notes": "Active LOW / HIGH relay control signal from GPIO."}
    ],
    "relay_2ch": [
        {"pin": "VCC", "type": "POWER_5V", "notes": "5V supply for relay coils and optocouplers."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "IN1", "type": "DIGITAL_IN", "notes": "Channel 1 trigger GPIO."},
        {"pin": "IN2", "type": "DIGITAL_IN", "notes": "Channel 2 trigger GPIO."}
    ],

    # Communication & RFID
    "rc522_rfid": [
        {"pin": "3.3V", "type": "POWER_3V3", "notes": "Strict 3.3V supply! (5V will destroy the MFRC522 IC)."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "RST", "type": "DIGITAL_IN", "notes": "Reset pin connected to MCU GPIO."},
        {"pin": "SDA (SS)", "type": "SPI_CS", "notes": "Dedicated SPI Chip Select line."},
        {"pin": "SCK", "type": "SPI_SCK", "notes": "Shared SPI Clock line."},
        {"pin": "MOSI", "type": "SPI_MOSI", "notes": "Shared SPI Master-Out line."},
        {"pin": "MISO", "type": "SPI_MISO", "notes": "Shared SPI Master-In line."}
    ],
    "nrf24l01": [
        {"pin": "VCC", "type": "POWER_3V3", "notes": "Requires clean 3.3V supply. Add 10uF capacitor across VCC/GND to prevent packet loss."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "CE", "type": "DIGITAL_IN", "notes": "Chip Enable for TX/RX mode."},
        {"pin": "CSN", "type": "SPI_CS", "notes": "Dedicated SPI Chip Select line."},
        {"pin": "SCK", "type": "SPI_SCK", "notes": "Shared SPI Clock line."},
        {"pin": "MOSI", "type": "SPI_MOSI", "notes": "Shared SPI MOSI line."},
        {"pin": "MISO", "type": "SPI_MISO", "notes": "Shared SPI MISO line."}
    ],
    "hc05_bluetooth": [
        {"pin": "VCC", "type": "POWER_5V", "notes": "Onboard 3.3V LDO requires 5V input."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "TXD", "type": "UART_TX", "notes": "HC-05 TXD (3.3V) connects to MCU RX."},
        {"pin": "RXD", "type": "UART_RX", "notes": "HC-05 RXD is 3.3V! On 5V Arduino, use a 1k/2k voltage divider."}
    ],
    "mpu6050": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "6-DOF IMU. Supply 3.3V or 5V (onboard LDO)."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C bus. Address 0x68."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C Clock."}
    ],
    "ds3231_rtc": [
        {"pin": "VCC", "type": "POWER_FLEX", "notes": "High precision RTC with CR2032 coin cell backup; 3.3V - 5.5V."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C bus. Address 0x68."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C Clock."}
    ],
    "ads1115_adc": [
        {"pin": "VDD", "type": "POWER_FLEX", "notes": "16-bit 4-channel ADC IC; 2.0V - 5.5V supply."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C Data line."},
        {"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C Clock line."},
        {"pin": "ADDR", "type": "GROUND", "notes": "Connect ADDR to GND for base I2C address 0x48."}
    ],
    "pir_sensor": [
        {"pin": "VCC", "type": "POWER_5V", "notes": "Requires 5V supply."},
        {"pin": "GND", "type": "GROUND", "notes": "Common ground."},
        {"pin": "OUT", "type": "DIGITAL_OUT", "notes": "Outputs 3.3V HIGH signal upon motion detection (safe for 3.3V GPIOs)."}
    ],
    "buzzer_active": [
        {"pin": "VCC (+)", "type": "DIGITAL_IN", "notes": "Connect to MCU GPIO pin for tone trigger."},
        {"pin": "GND (-)", "type": "GROUND", "notes": "Common ground."}
    ]
}


# ==============================================================================
# 3. Dynamic Wiring Allocation Engine
# ==============================================================================

def get_mcu_profile(platform_id):
    """Retrieves a pinout profile for the given platform ID."""
    clean_id = (platform_id or "esp32").lower().strip()
    # Direct key match (fastest path)
    if clean_id in MCU_PINOUT_PROFILES:
        return MCU_PINOUT_PROFILES[clean_id]
    # Normalize: strip spaces, hyphens, underscores
    import re
    norm = re.sub(r'[\s_\-]+', '', clean_id)
    for key, profile in MCU_PINOUT_PROFILES.items():
        key_norm = key.replace('_', '')
        if key_norm == norm or norm in key_norm or key_norm in norm:
            return profile
    # Default to ESP32 profile if unspecified
    return MCU_PINOUT_PROFILES["esp32"]


def synthesize_fallback_pinout(comp):
    """
    Synthesizes physical pinout mapping for any component in the catalog
    based on its interface, voltage, and category attributes.
    """
    interfaces = str(comp.get("interfaces", "")).upper()
    v_min = float(comp.get("operating_voltage_min", 3.3))
    v_max = float(comp.get("operating_voltage_max", 5.0))
    cat = str(comp.get("category", ""))

    pins = []
    
    # Power & Ground
    if v_max <= 3.6:
        p_type = "POWER_3V3"
    elif v_min >= 4.5:
        p_type = "POWER_5V"
    elif cat in ["Actuator", "Power"]:
        p_type = "POWER_EXT"
    else:
        p_type = "POWER_FLEX"

    pins.append({"pin": "VCC", "type": p_type, "notes": f"Operating rail {v_min}V - {v_max}V."})
    pins.append({"pin": "GND", "type": "GROUND", "notes": "Common reference ground."})

    # Interfaces
    if "I2C" in interfaces:
        pins.append({"pin": "SDA", "type": "I2C_SDA", "notes": "Shared I2C serial data line."})
        pins.append({"pin": "SCL", "type": "I2C_SCL", "notes": "Shared I2C serial clock line."})
    elif "SPI" in interfaces:
        pins.append({"pin": "CS", "type": "SPI_CS", "notes": "Dedicated SPI chip select."})
        pins.append({"pin": "SCK", "type": "SPI_SCK", "notes": "Shared SPI clock."})
        pins.append({"pin": "MOSI", "type": "SPI_MOSI", "notes": "Shared SPI data out."})
        pins.append({"pin": "MISO", "type": "SPI_MISO", "notes": "Shared SPI data in."})
    elif "UART" in interfaces:
        pins.append({"pin": "TX", "type": "UART_TX", "notes": "Serial transmit line to MCU RX."})
        pins.append({"pin": "RX", "type": "UART_RX", "notes": "Serial receive line from MCU TX."})
    elif "ANALOG" in interfaces or "ADC" in interfaces:
        pins.append({"pin": "AO", "type": "ANALOG_OUT", "notes": "Analog signal to MCU ADC pin."})
    elif "PWM" in interfaces:
        pins.append({"pin": "PWM", "type": "PWM_IN", "notes": "Pulse Width Modulation control pin."})
    else:
        # Default digital GPIO
        pins.append({"pin": "SIG", "type": "DIGITAL_INOUT", "notes": "Digital signal pin."})

    return pins


def generate_wiring_guide(platform_id, component_ids, components_df=None):
    """
    Generates a full, collision-free pin-to-pin wiring table and circuit advisories.
    
    Parameters:
        platform_id (str): Target microcontroller ID (e.g. 'esp32', 'arduino_uno')
        component_ids (list): List of active peripheral component IDs
        components_df (DataFrame, optional): Pre-loaded components DataFrame
    
    Returns:
        dict: Complete wiring guide with table, buses, advisories, and export texts.
    """
    if components_df is None:
        csv_path = os.path.join(DATA_DIR, "components.csv")
        if os.path.exists(csv_path):
            components_df = pd.read_csv(csv_path).set_index("component_id", drop=False)

    mcu = get_mcu_profile(platform_id)
    mcu_logic = mcu["logic_voltage"]

    # Resource pools
    adc_pool = list(mcu.get("adc_pool", []))
    pwm_pool = list(mcu.get("pwm_pool", []))
    gpio_pool = list(mcu.get("gpio_pool", []))
    spi_cs_pool = list(mcu.get("spi_cs_pool", []))

    wiring_rows = []
    advisories = []
    i2c_devices = []
    spi_devices = []
    allocated_pins_summary = []

    # Common GND entry for star-grounding
    wiring_rows.append({
        "component_id": platform_id,
        "component_name": mcu["name"],
        "pin_label": "GND",
        "mcu_pin": mcu["power_rails"]["gnd"],
        "signal_type": "Ground Reference",
        "wire_color": "Black",
        "wire_hex": "#1e293b",
        "circuit_notes": "Main system ground. All modules and external power supplies must connect here."
    })

    for cid in component_ids:
        if cid == platform_id:
            continue

        comp = {}
        if components_df is not None and cid in components_df.index:
            comp = components_df.loc[cid].to_dict()

        comp_name = comp.get("name", cid)
        comp_cat = comp.get("category", "")
        comp_logic = float(comp.get("logic_voltage", mcu_logic))

        # Retrieve pinout template
        pin_defs = PERIPHERAL_PINOUT_DB.get(cid)
        if not pin_defs:
            pin_defs = synthesize_fallback_pinout(comp)

        for p in pin_defs:
            p_pin = p["pin"]
            p_type = p["type"]
            p_notes = p.get("notes", "")
            
            mcu_pin = "TBD"
            signal_type = "Signal"
            wire_color = "Blue"
            wire_hex = "#2563eb"
            final_note = p_notes

            # 1. Power Pin Allocation
            if p_type == "POWER_3V3":
                mcu_pin = mcu["power_rails"].get("3v3", "3.3V")
                signal_type = "Power (3.3V Rail)"
                wire_color = "Red"
                wire_hex = "#dc2626"
                final_note = "3.3V regulated power rail."

            elif p_type == "POWER_5V":
                mcu_pin = mcu["power_rails"].get("5v", "5V Rail")
                signal_type = "Power (5V Rail)"
                wire_color = "Red"
                wire_hex = "#dc2626"
                final_note = "5V power supply rail."

            elif p_type == "POWER_EXT":
                mcu_pin = "External Power (+5V / Adapter)"
                signal_type = "External Power Supply"
                wire_color = "Red"
                wire_hex = "#dc2626"
                final_note = "Power directly from external 5V/adapter supply to prevent MCU regulator thermal overload. Share common GND!"
                advisories.append(f"External Supply: Power '{comp_name}' from a separate 5V adapter and tie its GND to the microcontroller GND.")

            elif p_type == "POWER_FLEX":
                # Matches MCU logic rail
                if mcu_logic == 3.3:
                    mcu_pin = mcu["power_rails"].get("3v3", "3.3V")
                    signal_type = "Power (3.3V)"
                else:
                    mcu_pin = mcu["power_rails"].get("5v", "5V")
                    signal_type = "Power (5V)"
                wire_color = "Red"
                wire_hex = "#dc2626"

            elif p_type == "GROUND":
                mcu_pin = mcu["power_rails"]["gnd"]
                signal_type = "Ground"
                wire_color = "Black"
                wire_hex = "#1e293b"

            # 2. I2C Bus Allocation (Shared bus!)
            elif p_type == "I2C_SDA":
                mcu_pin = mcu["i2c"]["sda"]
                signal_type = "I2C Bus (SDA Data)"
                wire_color = "Blue"
                wire_hex = "#2563eb"
                final_note = "Shared I2C bus: connect in parallel with other I2C peripherals."
                if comp_name not in i2c_devices:
                    i2c_devices.append(comp_name)

            elif p_type == "I2C_SCL":
                mcu_pin = mcu["i2c"]["scl"]
                signal_type = "I2C Bus (SCL Clock)"
                wire_color = "Yellow"
                wire_hex = "#d97706"
                final_note = "Shared I2C clock line."

            # 3. SPI Bus Allocation
            elif p_type == "SPI_MOSI":
                mcu_pin = mcu["spi"]["mosi"]
                signal_type = "SPI Bus (MOSI)"
                wire_color = "Green"
                wire_hex = "#16a34a"
                final_note = "Shared SPI Master-Out Data line."
                if comp_name not in spi_devices:
                    spi_devices.append(comp_name)

            elif p_type == "SPI_MISO":
                mcu_pin = mcu["spi"]["miso"]
                signal_type = "SPI Bus (MISO)"
                wire_color = "Teal"
                wire_hex = "#0891b2"
                final_note = "Shared SPI Master-In Data line."

            elif p_type == "SPI_SCK":
                mcu_pin = mcu["spi"]["sck"]
                signal_type = "SPI Bus (SCK Clock)"
                wire_color = "Orange"
                wire_hex = "#ea580c"
                final_note = "Shared SPI Clock line."

            elif p_type == "SPI_CS":
                if spi_cs_pool:
                    mcu_pin = spi_cs_pool.pop(0)
                else:
                    mcu_pin = gpio_pool.pop(0) if gpio_pool else "GPIO (Exhausted)"
                signal_type = "SPI Chip Select (Dedicated)"
                wire_color = "Purple"
                wire_hex = "#9333ea"
                final_note = "Dedicated SPI Chip Select line for this device."

            # 4. UART Bus Allocation
            elif p_type == "UART_TX":
                mcu_pin = mcu["uart"]["rx"]
                signal_type = "Serial (TX -> MCU RX)"
                wire_color = "Purple"
                wire_hex = "#9333ea"
                final_note = "Transmit pin connects to microcontroller Serial RX."

            elif p_type == "UART_RX":
                mcu_pin = mcu["uart"]["tx"]
                signal_type = "Serial (RX <- MCU TX)"
                wire_color = "Blue"
                wire_hex = "#2563eb"
                if mcu_logic == 5.0 and comp_logic <= 3.6:
                    final_note = "Insert 1k/2k-ohm voltage divider between 5V MCU TX and 3.3V module RX."
                    advisories.append(f"Level Shift: '{comp_name}' RX line requires a voltage divider to protect from 5V Arduino signals.")
                else:
                    final_note = "Receive pin connects to microcontroller Serial TX."

            # 5. Analog ADC Channel Allocation
            elif p_type == "ANALOG_OUT":
                if adc_pool:
                    mcu_pin = adc_pool.pop(0)
                    signal_type = "Analog Voltage Input"
                    wire_color = "Cyan"
                    wire_hex = "#0284c7"
                    final_note = "Connect to dedicated Analog-to-Digital Converter (ADC) input channel."
                else:
                    mcu_pin = "NO ONBOARD ADC"
                    signal_type = "Analog Input (Conflict)"
                    wire_color = "Red"
                    wire_hex = "#dc2626"
                    final_note = f"{mcu['name']} has no available onboard ADC! Use an external ADS1115 (I2C) or MCP3008 (SPI) ADC IC."
                    advisories.append(f"ADC Conflict: {mcu['name']} has no analog input channels for '{comp_name}'. Add an ADS1115 ADC module.")

            # 6. PWM Speed / Servo Control
            elif p_type == "PWM_IN":
                if pwm_pool:
                    mcu_pin = pwm_pool.pop(0)
                elif gpio_pool:
                    mcu_pin = gpio_pool.pop(0)
                else:
                    mcu_pin = "PWM (Exhausted)"
                signal_type = "PWM Signal Output"
                wire_color = "Orange"
                wire_hex = "#ea580c"
                final_note = "Hardware PWM pin for motor speed or servo pulse width control."

            # 7. 5V Digital Output to 3.3V MCU (HC-SR04 Echo case)
            elif p_type == "DIGITAL_OUT_5V":
                if gpio_pool:
                    mcu_pin = gpio_pool.pop(0)
                else:
                    mcu_pin = "GPIO (Exhausted)"
                signal_type = "Digital Input (5V -> 3.3V)"
                wire_color = "Yellow"
                wire_hex = "#d97706"
                if mcu_logic <= 3.6:
                    final_note = "CRITICAL: Sensor outputs 5V. Insert 1k-ohm & 2k-ohm resistors (voltage divider) to step down to 3.3V before MCU pin."
                    advisories.append(f"Safety Divider: '{comp_name}' Echo line sends 5V logic. Connect a 1k-ohm resistor in series with Echo, and 2k-ohm from GPIO to GND.")
                else:
                    final_note = "Direct digital connection (safe on 5V Arduino Uno/Mega)."

            # 8. 1-Wire Bus (DS18B20)
            elif p_type == "ONE_WIRE":
                if gpio_pool:
                    mcu_pin = gpio_pool.pop(0)
                else:
                    mcu_pin = "GPIO (Exhausted)"
                signal_type = "1-Wire Bidirectional Bus"
                wire_color = "Green"
                wire_hex = "#16a34a"
                final_note = "1-Wire bus: Connect a 4.7k-ohm pull-up resistor between this pin and VCC."
                advisories.append(f"Pull-Up Resistor: '{comp_name}' requires a 4.7k-ohm pull-up resistor between DATA and 3.3V/5V.")

            # 9. General Digital I/O
            else:
                if gpio_pool:
                    mcu_pin = gpio_pool.pop(0)
                else:
                    mcu_pin = "GPIO (Exhausted)"
                signal_type = "Digital GPIO"
                wire_color = "Green"
                wire_hex = "#16a34a"

            # Track pin summary
            if "GPIO" in mcu_pin or "D" in mcu_pin or "A" in mcu_pin:
                allocated_pins_summary.append(f"{mcu_pin} -> {comp_name} ({p_pin})")

            wiring_rows.append({
                "component_id": cid,
                "component_name": comp_name,
                "pin_label": p_pin,
                "mcu_pin": mcu_pin,
                "signal_type": signal_type,
                "wire_color": wire_color,
                "wire_hex": wire_hex,
                "circuit_notes": final_note
            })

    # Summary of shared buses
    bus_summary = {
        "i2c_bus": {
            "sda": mcu["i2c"]["sda"],
            "scl": mcu["i2c"]["scl"],
            "devices": i2c_devices
        },
        "spi_bus": {
            "mosi": mcu["spi"]["mosi"],
            "miso": mcu["spi"]["miso"],
            "sck": mcu["spi"]["sck"],
            "devices": spi_devices
        },
        "total_allocated_pins": len(allocated_pins_summary)
    }

    # Generate Markdown export table
    md_lines = [
        f"### Hardware Pinout & Wiring Guide for {mcu['name']}",
        "",
        "| Component | Pin Label | Target MCU Pin | Signal Type | Wire Color | Electrical Notes |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    for row in wiring_rows:
        md_lines.append(
            f"| **{row['component_name']}** | `{row['pin_label']}` | `{row['mcu_pin']}` | {row['signal_type']} | {row['wire_color']} | {row['circuit_notes']} |"
        )
    
    if advisories:
        md_lines.append("")
        md_lines.append("#### Circuit Implementation Advisories:")
        for adv in advisories:
            md_lines.append(f"- {adv}")

    export_markdown = "\n".join(md_lines)

    # Generate ASCII plain text table for download
    text_lines = [
        "=" * 110,
        f"SMARTCOMPONENTAI - HARDWARE WIRING SPECIFICATION",
        f"Platform: {mcu['name']} (Logic: {mcu_logic}V)",
        "=" * 110,
        f"{'COMPONENT':<28} | {'PIN':<8} | {'TARGET MCU PIN':<20} | {'SIGNAL TYPE':<22} | {'NOTES':<25}",
        "-" * 110
    ]
    for row in wiring_rows:
        text_lines.append(
            f"{row['component_name'][:28]:<28} | {row['pin_label']:<8} | {row['mcu_pin'][:20]:<20} | {row['signal_type'][:22]:<22} | {row['circuit_notes']}"
        )
    text_lines.append("=" * 110)
    if advisories:
        text_lines.append("CIRCUIT ADVISORIES & SAFETY RECOMMENDATIONS:")
        for i, adv in enumerate(advisories, 1):
            text_lines.append(f"  [{i}] {adv}")
        text_lines.append("=" * 110)

    export_text = "\n".join(text_lines)

    return {
        "mcu_name": mcu["name"],
        "mcu_logic_voltage": mcu_logic,
        "wiring_table": wiring_rows,
        "bus_summary": bus_summary,
        "advisories": advisories,
        "export_markdown": export_markdown,
        "export_text": export_text
    }


if __name__ == "__main__":
    # Test execution
    test_guide = generate_wiring_guide("esp32", ["bme280", "hc_sr04", "ssd1306_oled"])
    print(f"Generated wiring guide for {test_guide['mcu_name']}:")
    print(test_guide["export_markdown"])
