# 🌱 PPWS - Pi Plant Watering System

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-red?style=for-the-badge&logo=raspberry-pi)

**PPWS** is an automated gardening assistant powered by the Raspberry Pi. It monitors soil moisture levels in real-time, automatically waters your plant when it gets thirsty, and creates beautiful timelapse videos of your plant's growth using the Pi Camera.

The project features a modern, touch-friendly **Tkinter GUI** optimized for Raspberry Pi touchscreens.

---

## ✨ Features

* **💧 Auto-Watering:** Continuously monitors soil moisture sensors and activates the pump relay when the soil is dry.
* **🎮 Manual Control:** "Hold-to-water" button for manual care.
* **📸 Timelapse Engine:** Captures photos at set intervals and renders them into a video to track plant growth.
* **💡 Light Simulation:** Controls RGB LEDs to simulate growth lights (or status indicators).
* **🌙 Dark Mode GUI:** A polished, eye-friendly interface built with Python Tkinter.

---

## 🛠️ Hardware Required

* **Raspberry Pi 4** (or 3B+)
* **Capacitive Soil Moisture Sensor** (v1.2 recommended)
* **5V Relay Module** (Active LOW)
* **Mini Submersible Water Pump** (3V-5V) + Tubing
* **Raspberry Pi Camera Module**
* **External Power Supply** (For the pump - **Important!**)
* **Breadboard & Jumper Wires**
* **LEDs + Resistors** (Optional, for status)

---

## 🔌 Circuit Diagram & Wiring

Below is the wiring diagram for the system.

> **⚠️ SAFETY WARNING:** Do not power the water pump directly from the Raspberry Pi's 5V pin. Motors draw high current and can damage your Pi. Use an external power source (like a battery pack) for the pump, connecting the **Grounds** together.

![Wiring Diagram](assets/Circuit_Diagram.png)

### Pin Mapping (BCM)

| Component | BCM Pin | Physical Pin | Note |
| :--- | :--- | :--- | :--- |
| **Moisture Sensor** | GPIO 16 | Pin 36 | Input (High = Dry) |
| **Pump Relay** | GPIO 20 | Pin 38 | Output (Active Low) |
| **LED 1** | GPIO 5 | Pin 29 | Status Light |
| **LED 2** | GPIO 6 | Pin 31 | Status Light |
| **LED 3** | GPIO 13 | Pin 33 | Status Light |

---

## 🚀 Installation

### 1. System Prerequisites
Update your Raspberry Pi and install the necessary system packages for Python Tkinter and GPIO control.

```bash
sudo apt update
sudo apt install python3-tk python3-pip
