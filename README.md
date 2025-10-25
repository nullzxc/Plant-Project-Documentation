# 🌿 Plant Watering System (Raspberry Pi + Python GUI)

Raspberry Pi reads soil moisture and drives a relay-controlled 5V pump to keep soil within a healthy range.  
Includes a **Tkinter GUI**, optional **analog mode (MCP3008)**, safety guardrails, logs, and a printable documentation website.

> Demo-ready for CMPT 2200 / “Designing with Raspberry Pi” — but generic enough for anyone building an auto-watering rig.

---

## Table of Contents
- [Features](#features)
- [Bill of Materials](#bill-of-materials)
- [System Overview](#system-overview)
- [Pin Map](#pin-map)
- [Repository Structure](#repository-structure)
- [Setup](#setup)
- [Run](#run)
- [Calibration](#calibration)
- [Safety Notes](#safety-notes)
- [Troubleshooting](#troubleshooting)
- [Screenshots](#screenshots)
- [Docs Website (Optional)](#docs-website-optional)
- [Roadmap](#roadmap)
- [License](#license)
- [Credits](#credits)

---

## Features
- ✅ **GPIO Input**: digital soil sensor (DO) or analog via **MCP3008** (SPI)
- ✅ **GPIO Output**: relay → 5V pump; optional status LED & buzzer
- ✅ **GUI**: Tkinter app with live moisture, manual water, threshold (analog), log window
- ✅ **Guardrails**: max-on seconds, cooldown, safe relay defaults, cleanup on exit
- ✅ **Stability**: designed for repeated cycles without brown-outs (separate pump PSU)
- ✅ **Docs**: single-file Tailwind site for printing/submission (see `/docs/index.html`)

---

## Bill of Materials
| Item | Notes | Qty |
|---|---|---:|
| Raspberry Pi 4 + 32GB microSD + 3A PSU | Main controller | 1
| Soil Moisture Sensor (capacitive preferred) | Digital (DO) **or** analog via MCP3008 | 1
| MCP3008 ADC (SPI) | Only if your sensor is analog-only | 1
| 5V Relay Module (optocoupled) | Controls pump safely | 1
| 5V Submersible Pump + tubing | Water delivery | 1
| External 5V supply for pump | **Separate** from Pi | 1
| Breadboard + jumper wires | Prototyping | —
| LED + 330–1kΩ resistor | Status indicator (optional) | 1
| Buzzer (active) | Optional | 1

---

## System Overview

```text
Soil Sensor (analog) → MCP3008 → SPI → Raspberry Pi → Python Logic
                                        ├─ Tkinter GUI (threshold/log)
                                        └─ Relay (BCM 23) → Pump + 5V Supply

Optional: LED (BCM 24) status, Buzzer (BCM 18)
