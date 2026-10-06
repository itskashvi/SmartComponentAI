# SmartComponentAI

### Electronic Component Recommendation & Hardware Compatibility Assistant

SmartComponentAI is an intelligent hardware design assistant built for engineering students, embedded systems developers, and makers. It bridges the gap between high-level project concepts and physical hardware implementations by automatically translating natural language descriptions into an optimal Bill of Materials (BOM) while validating electrical, interface, and pin-level compatibility.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Machine Learning Algorithms & Models](#machine-learning-algorithms--models)
  - [1. Component Recommendation Engine (TF-IDF + Cosine Similarity)](#1-component-recommendation-engine-tf-idf--cosine-similarity)
  - [2. Hardware Taxonomy & Functional Diversity](#2-hardware-taxonomy--functional-diversity)
  - [3. Hardware Compatibility Classifier (Random Forest + Hybrid Rules)](#3-hardware-compatibility-classifier-random-forest--hybrid-rules)
  - [4. Model Evaluation & Benchmarks](#4-model-evaluation--benchmarks)
- [Project Directory Structure](#project-directory-structure)
- [Installation & Setup](#installation--setup)
- [User Guide](#user-guide)
  - [Starting the Application](#starting-the-application)
  - [Finding Components for a Project](#finding-components-for-a-project)
  - [Interpreting Compatibility Reports](#interpreting-compatibility-reports)
  - [Interactive Setup Tuning](#interactive-setup-tuning)
  - [Component Datasheets](#component-datasheets)
- [Running Automated Tests](#running-automated-tests)
- [UI & Design System](#ui--design-system)
- [License](#license)

---

## Overview

When designing embedded systems and IoT projects, developers frequently encounter:
1. **Component Selection Dilemmas**: Sifting through hundreds of sensors and peripheral modules to find devices matching project requirements and budget constraints.
2. **Redundant Sensors**: Inadvertently selecting multiple sensors that measure identical parameters (e.g., placing two temperature sensors on the same board).
3. **Hardware Incompatibilities**: Overlooking subtle electrical mismatches (e.g., feeding 5V sensor outputs into 3.3V microcontroller GPIOs, lacking required communication buses like I2C or SPI, exceeding power supply limits, or running out of pins).

SmartComponentAI solves these problems with a two-tier pipeline: a **content-based recommendation model** that selects distinct, complementary components, paired with a **hybrid ML and engineering rule engine** that flags electrical conflicts and provides circuit-level remediation.

---

## Key Features

- **Natural Language Requirement Processing**: Accepts plain-English descriptions (e.g., *"IoT weather station with temperature, humidity, air quality, and an OLED display"*).
- **Non-Redundant Recommendation Engine**: Enforces functional role diversity so that setups receive multiple complementary sensors (e.g., Climate + Gas + Particulate + Display) rather than redundant duplicates of the same sensor type.
- **Microcontroller Platform Filtering**: Customizes recommendations for popular development boards including ESP32, Arduino Uno, Raspberry Pi Pico, Raspberry Pi 4, STM32 Blue Pill, Arduino Mega, and ESP32-S3.
- **Budget-Aware Filtering**: Ranks components to remain within defined budget thresholds (in INR).
- **Hybrid Compatibility Verification**:
  - Combines Random Forest classification with deterministic engineering rules.
  - Automatically overrides optimistic ML predictions if strict electrical safety boundaries (logic level mismatches, voltage domains) are breached.
- **Cumulative Setup Diagnostics**:
  - **GPIO Pin Budgeting**: Tracks total GPIO pins required versus pins available on the chosen development board.
  - **Power Rail Budgeting**: Sums peak operating current draw and flags when an external 5V/2A power supply is needed instead of standard USB port power (500mA).
  - **Redundancy Warnings**: Detects when two components sharing the same functional role are manually added into a single setup.
- **Actionable Circuit Solutions**: Instead of generic error messages, the engine prescribes exact engineering fixes (e.g., resistive voltage dividers with 1k-ohm and 2k-ohm resistors, bidirectional level shifters, or external MCP3008 ADC ICs).
- **Clean Engineering UI**: Built with a bespoke 5-color palette, free of generic AI tropes and emojis, designed specifically as a professional electronics workbench.

---

## System Architecture

```text
                                 User Project Description
                                (Plain English Requirement)
                                             |
                                             v
                           +-----------------------------------+
                           |      Flask Web Application        |
                           |       (app.py / REST API)         |
                           +-----------------------------------+
                                             |
                     +-----------------------+-----------------------+
                     |                                               |
                     v                                               v
   +------------------------------------+          +------------------------------------+
   |   Component Recommendation Engine  |          |    Hybrid Compatibility Engine     |
   |      (models/recommendation.py)    |          |     (models/compatibility.py)      |
   +------------------------------------+          +------------------------------------+
   | - TF-IDF Matrix (6000 features)   |          | - Feature Extraction (5 Domains)   |
   | - Cosine Similarity Metric         |          | - Random Forest Classifier (100 T) |
   | - Platform Compatibility Weights   |          | - Deterministic Safety Overrides   |
   | - Functional Taxonomy Diversity    |          | - Cumulative Pin & Power Checks    |
   +------------------------------------+          +------------------------------------+
                     |                                               |
                     +-----------------------+-----------------------+
                                             |
                                             v
                           +-----------------------------------+
                           |         Results Dashboard         |
                           | - Ranked Component Cards          |
                           | - Live Pin & Power Gauges         |
                           | - Pairwise Verification Cards     |
                           | - Interactive Setup Builder       |
                           +-----------------------------------+
```

---

## Machine Learning Algorithms & Models

### 1. Component Recommendation Engine (TF-IDF + Cosine Similarity)

The recommendation engine operates as a content-based filtering system using **Term Frequency - Inverse Document Frequency (TF-IDF)** and **Cosine Similarity**.

#### Corpus Construction
Each component in the catalog (121 curated electronics components) has a weighted text corpus constructed to emphasize functional identity:
```python
corpus_text = (
    (name * 4) +
    (tags * 3) +
    (applications * 3) +
    (category * 2) +
    (subcategory * 2) +
    interfaces +
    description
)
```

#### Vectorization Parameters
- **N-gram Range**: `(1, 2)` (captures unigrams like `"temperature"` and bigrams like `"soil moisture"`, `"air quality"`).
- **Max Features**: 6,000 terms.
- **Sublinear TF Scaling**: `True` (replaces term frequency $tf$ with $1 + \log(tf)$ to prevent frequent terms from dominating).
- **Stop Words**: English stop words removed.

#### Similarity Computation
For an incoming user query vector $\vec{q}$ and component vectors $\vec{c}_i$, cosine similarity is evaluated:

$$\text{similarity}(\vec{q}, \vec{c}_i) = \frac{\vec{q} \cdot \vec{c}_i}{\|\vec{q}\| \|\vec{c}_i\|}$$

If a user specifies a target development platform, components that do not list platform compatibility receive a 50% penalty on raw similarity score. Scores are normalized to match percentages ($50\% - 96\%$).

---

### 2. Hardware Taxonomy & Functional Diversity

A common pitfall of naive nearest-neighbor recommendation is semantic clustering: an IoT query about climate might return three temperature sensors and two OLED screens. 

To guarantee functional variety, SmartComponentAI introduces an engineering taxonomy (`models/taxonomy.py`) mapping all 121 catalog items into ~70 distinct functional roles:

| Functional Kind | Components Included |
| :--- | :--- |
| `ambient_climate` | BME280, BMP280, DHT11, DHT22, AHT20, SHT31-D, DS18B20 |
| `air_quality_co2` | SCD30, SCD40, MH-Z19B |
| `air_quality_hazardous` | MQ-2, MQ-135, MQ-7, MQ-3, MQ-9 |
| `particulate_matter` | PMS5003, SDS011 |
| `soil_moisture` | Capacitive Soil Moisture Sensor, Resistive Soil Moisture Sensor |
| `ultrasonic_distance` | HC-SR04, JSN-SR04T |
| `oled_display` | SSD1306 (0.96"), SH1106 (1.3") |
| `character_lcd` | 16x2 I2C LCD, 20x4 I2C LCD |
| `motor_driver` | L298N, L293D, A4988, DRV8825 |
| `relay_module` | 1-Channel 5V Relay, 2-Channel 5V Relay, 3.3V Relay |

The recommender tracks `seen_kinds` during candidate generation. Once a functional kind is filled (e.g., an ambient climate sensor is selected), subsequent sensors of the exact same kind are deferred, ensuring that the top recommendations contain diverse and complementary parts.

---

### 3. Hardware Compatibility Classifier (Random Forest + Hybrid Rules)

Hardware compatibility is evaluated across 5 physical domain features extracted between a host microcontroller and a peripheral:

1. **`voltage_compatible`** ($0$ or $1$): Verifies overlapping operating voltage ranges:
   $$\text{VCC}_{\min, \text{MCU}} \le \text{VCC}_{\max, \text{Peripheral}} \quad \text{and} \quad \text{VCC}_{\max, \text{MCU}} \ge \text{VCC}_{\min, \text{Peripheral}}$$
2. **`current_compatible`** ($0$ or $1$): Verifies peripheral peak draw does not exceed onboard regulator safe margins.
3. **`logic_compatible`** ($0$ or $1$): Verifies GPIO logic level tolerances (e.g., 3.3V vs 5.0V).
4. **`interface_compatible`** ($0$ or $1$): Checks communication bus alignment (I2C, SPI, UART, ADC/Analog, PWM, 1-Wire, GPIO).
5. **`pin_compatible`** ($0$ or $1$): Verifies microcontroller has sufficient available GPIO pins.

#### The Hybrid Consensus Engine
While a trained **Random Forest Classifier** evaluates overall baseline compatibility probability, safety-critical embedded systems require deterministic guarantees:

- **Rule 1 (Missing ADC)**: If a peripheral outputs analog signals (e.g., MQ gas sensors) and the host platform lacks an onboard ADC (e.g., Raspberry Pi 4), status is forced to `incompatible` and an external ADC IC (MCP3008/ADS1115) is prescribed.
- **Rule 2 (5V to 3.3V Logic Level Overvoltage)**: If a 5V sensor outputs directly to a 3.3V microcontroller (e.g., HC-SR04 Echo into ESP32), status is downgraded to `warning` with an explicit prescription for a resistive divider or level shifter.
- **Rule 3 (Missing Communication Protocol)**: If a peripheral requires a specific hardware bus that the microcontroller does not support, status is marked `incompatible`.
- **Rule 4 (Overcurrent)**: If current draw exceeds onboard regulator ratings, status triggers a `warning` with an instruction to use an external power supply.
- **Rule 5 (Engineering Redundancy)**: If two components with the same functional kind are added to the setup, a dedicated warning informs the user to prune redundant hardware.

---

### 4. Model Evaluation & Benchmarks

The compatibility dataset consists of 3,600+ generated pairwise component pairings. Models were trained using a 70% Train / 15% Validation / 15% Test stratified split:

| Model | Test Accuracy | Test Precision | Test Recall | Test F1-Score | Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Decision Tree** (depth=5) | 1.0000 | 1.0000 | 1.0000 | 1.0000 | Baseline |
| **Random Forest** (n=100, depth=6) | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **Selected Best Model** |
| **Gradient Boosting** (n=100, lr=0.1) | 1.0000 | 1.0000 | 1.0000 | 1.0000 | Candidate |

Confusion Matrix on Test Split (541 samples):
- True Negatives (Incompatible correctly identified): 263
- False Positives (Incompatible wrongly called Compatible): 0
- False Negatives (Compatible wrongly called Incompatible): 0
- True Positives (Compatible correctly identified): 278

Visual model comparison charts, feature importance rankings, and confusion matrices are generated in the [`evaluation/`](file:///d:/aiml/SmartComponentAI/evaluation/) directory.

---

## Project Directory Structure

```text
SmartComponentAI/
├── app.py                      # Flask web application & REST routes
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation & user guide
│
├── models/                     # Core intelligence models
│   ├── taxonomy.py             # Component functional role mappings (70+ kinds)
│   ├── recommendation.py       # TF-IDF + diversity ranking engine
│   ├── recommendation_model.pkl# Serialized TF-IDF vectorizer & matrix
│   ├── compatibility.py        # Hybrid Random Forest + engineering safety engine
│   └── compatibility_model.pkl # Serialized Random Forest classifier
│
├── data/
│   ├── raw/
│   │   └── curated_components_source.json # Master component definitions
│   └── processed/
│       ├── components.csv      # Processed component catalog (121 components)
│       ├── compatibility.csv   # 3600+ labeled component compatibility pairs
│       └── projects.csv        # Reference student project templates
│
├── preprocessing/
│   ├── clean_components.py     # Data extraction and catalog normalization
│   └── create_pairs.py         # Pairwise compatibility dataset generator
│
├── evaluation/
│   ├── train.py                # Model training, split, cross-val, & export
│   ├── evaluate.py             # Performance metric visualization & report generator
│   ├── training_report.json    # JSON report of validation & test metrics
│   ├── confusion_matrix.png    # Test set confusion matrix plot
│   ├── feature_importance.png  # Random Forest feature importance plot
│   └── model_comparison.png    # Comparison b/w Decision Tree, RF, & GBDT
│
├── static/
│   ├── css/
│   │   └── style.css           # Custom stylesheet (5-color architectural palette)
│   └── js/
│       └── script.js           # Interactive UI, presets, live async compatibility API
│
├── templates/
│   ├── index.html              # Project query submission & quick presets
│   ├── results.html            # Recommendations, gauges, & compatibility panel
│   ├── component.html          # Individual component datasheet & pinout specs
│   └── 404.html                # Error page
│
└── tests/
    └── test_pipeline.py        # 13 automated integration & unit tests
```

---

## Installation & Setup

### Prerequisites
- Python 3.9 or higher
- `pip` package manager
- (Optional) Virtual environment tool (`venv`)

### 1. Clone Repository & Navigate
```powershell
git clone https://github.com/itskashvi/SmartComponentAI.git
cd SmartComponentAI
```

### 2. Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

*(On Linux / macOS: `source venv/bin/activate`)*

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. (Optional) Rebuild Datasets and Train Models
Pre-trained models are already included in `models/`. To retrain from scratch:
```powershell
python preprocessing/clean_components.py
python preprocessing/create_pairs.py
python evaluation/train.py
python evaluation/evaluate.py
```

---

## User Guide

### Starting the Application

Launch the Flask development server:
```powershell
python app.py
```

Open your browser and navigate to:
```text
http://localhost:5000
```

---

### Finding Components for a Project

1. **Enter Requirements**:
   - In the **Project Description** field, describe what you intend to build (e.g., *"Autonomous line tracking robot with IR sensors and dual DC gearmotors"*).
2. **Select Dev Board**:
   - Choose your target board from the **Target Microcontroller / Platform** dropdown (ESP32, Arduino Uno, Raspberry Pi 4, etc.).
3. **Set Budget**:
   - Enter your maximum budget threshold in INR.
4. **Specify Existing Components (Optional)**:
   - If you already possess specific parts (e.g., `esp32, bme280`), type their IDs or names separated by commas. The system will prevent re-recommending these and evaluate their compatibility with new parts.
5. **Or Use a Preset**:
   - Click any card in the **Quick Project Presets** section (IoT Weather Station, Obstacle Avoiding Robot, Smart Plant Watering, or RFID Smart Door Lock) to populate the form instantly.
6. **Submit**:
   - Click **Find Components & Check Compatibility**.

---

### Interpreting Compatibility Reports

On the results page:

- **Recommended Components (Left Column)**:
  - Ranked by functional similarity.
  - Each card displays the component's name, functional role badge, voltage domain, logic level standard, price, and an engineering rationale explaining why it was chosen.
- **Hardware Compatibility Analysis (Right Column)**:
  - **Overall Status Banner**:
    - `OK (COMPATIBLE SETUP)`: All selected components operate within safe electrical boundaries.
    - `WARN (COMPATIBILITY WARNING)`: Circuit requires level shifting, power isolation, or has redundant sensors, but is fully feasible.
    - `ERR (INCOMPATIBLE SETUP)`: Direct conflict (e.g., missing hardware ADC or incompatible bus).
  - **Resource Gauges**:
    - **GPIO Pin Budget**: Bar graph showing total pins used vs. available pins on the board.
    - **Total Current Consumption**: Shows cumulative current load and warns if peak draw exceeds standard USB 500mA capacity.
  - **Pairwise Hardware Verification**:
    - Detailed card for each microcontroller-peripheral connection.
    - Status pills for **Voltage**, **Logic Level**, **Interface**, **Pins**, and **Current**.
    - Concrete circuit solutions (resistor values, IC recommendations).

---

### Interactive Setup Tuning

- On any recommended component card, click **+ Add to Setup** or **In Setup** to toggle the part into or out of the active hardware circuit.
- The web app sends an asynchronous `POST /check-compatibility` request and recomputes the pin usage, current draw, redundancy checks, and overall status without reloading the page.

---

### Component Datasheets

- Click **Datasheet Specs** on any component card to open its dedicated technical page (`/component/<id>`).
- View operating voltage ranges, peak current draw, pin count, communication protocols, compatible development platforms, common application circuits, and an **Electrical Safety Checklist**.

---

## Running Automated Tests

A comprehensive integration test suite verifies the recommendation engine, compatibility evaluation, taxonomy filtering, and web routes:

```powershell
python tests/test_pipeline.py
```

Expected output:
```text
.............
----------------------------------------------------------------------
Ran 13 tests in 0.542s

OK
[PASS] POST /check-compatibility returned JSON status: warning
[PASS] GET /api/components returned 121 components.
[PASS] GET /component/bme280 returned 200 with datasheet specs.
[PASS] ESP32 + BME280 compatibility evaluated as: compatible
[PASS] ESP32 + HC-SR04 compatibility evaluated as: warning with level shifter solution
[PASS] Full setup (ESP32 + BME280 + OLED) evaluated as: compatible
[PASS] GET / returned 200 with home form.
[PASS] Diverse recommendations verified (no duplicate sensor kinds)
[PASS] POST /recommend returned 200 with rendered results page.
[PASS] Recommendation test for robotics query: top results returned
[PASS] Recommendation test for temperature query: top results returned
[PASS] Redundant sensor detection verified (BME280 + DHT22 triggers redundancy warning)
[PASS] Raspberry Pi 4 + MQ-2 evaluated as: incompatible with ADC requirement
```

---

## UI & Design System

The frontend was engineered with a custom 5-color palette to evoke a refined, architectural engineering laboratory rather than a generic AI generator:

| Color Hex | Name | Purpose |
| :---: | :--- | :--- |
| **`#301a4b`** | Deep Plum / Midnight Aubergine | Navbar, primary typography, brand marks, primary buttons |
| **`#6db1bf`** | Glacial Teal | Secondary interactive accents, borders, focus rings, progress tracks |
| **`#ffeaec`** | Warm Blush Canvas | Main background canvas, soft card tints, subtle panel fills |
| **`#f39a9d`** | Coral Pink / Salmon | Warning highlights, alert callouts, logic voltage indicators |
| **`#3f6c51`** | Deep Forest Sage Green | Verified compatibility badges, pin confirmations, price tags |

### Design Principles
- **Zero Emojis**: Emojis have been completely eliminated from the interface and replaced with clean monospaced markers, numbered steps (`01`, `02`, `03`), and crisp status pills.
- **High Readability**: High-contrast ratios surpassing WCAG AAA standards on primary reading elements.
- **Responsive Layout**: Two-column layout on desktop adapting seamlessly to single-column on tablets and mobile devices.

---

## License

This project is licensed under the MIT License — feel free to use, adapt, and build upon this tool for academic, research, and maker projects.
