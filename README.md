<div align="center">
  
  # 🌍 Earthquake Data Processor Suite
  
  *A comprehensive, modular web application designed for the extraction, processing, conversion, and visualization of high-frequency seismic and structural monitoring data.*
  
  ![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)
  ![Flask](https://img.shields.io/badge/Flask-Web_UI-black?style=for-the-badge&logo=flask&logoColor=white)
  ![Pandas](https://img.shields.io/badge/Pandas-Data_Processing-150458?style=for-the-badge&logo=pandas&logoColor=white)
  ![AWS S3](https://img.shields.io/badge/AWS_S3-Cloud_Storage-569A31?style=for-the-badge&logo=amazons3&logoColor=white)
  ![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
</div>

---

## 📖 Overview

This repository contains a modular, web-based analytics dashboard engineered for civil, structural, and seismological researchers. Built on a robust Flask backend, it seamlessly integrates local file processing, AWS S3 cloud archiving, and direct FDSNWS server querying. 

The suite automates complex analytical pipelines including Fast Fourier Transform (FFT) analysis, numerical integration, mathematical differentiation of velocity to acceleration, multi-damping response spectrum generation, and multi-profile comparative analysis.

<img width="1889" height="891" alt="Screenshot 2026-06-10 154227" src="https://github.com/user-attachments/assets/c91fe1da-7c09-40cf-b16e-0fec7c9f0364" />

<p align="center">
  <img width="49%" alt="Compare Plot 1" src="https://github.com/user-attachments/assets/f9038e57-b77e-4e1e-bec9-c5ab8d8cf450" />
  <img width="49%" alt="Compare Plot 2" src="https://github.com/user-attachments/assets/66917bfd-71e8-4e85-9e4f-34fa2a4df051" />
</p>

---

## ✨ Comprehensive Features

### 📡 1. Data Acquisition & Networking
* **Dual-Source Cloud & Local Extraction:** Simultaneously query and pull data from local archive directories and AWS S3 cloud storage buckets.
* **Direct FDSNWS Integration:** Download continuous waveforms directly from Raspberry Shake FDSN servers via `dataselect` queries based on precise event time windows.
* **Smart Caching:** Prevents redundant downloads by checking local directories before executing AWS S3 queries.

### 🧮 2. Signal Processing & Mathematical Analysis
* **Response Spectrum Generation:** Computes highly accurate Pseudo-Spectral Acceleration (PSA) across customizable damping ratios and time periods. *(See Methodology section below)*.
* **Fast Fourier Transform (FFT):** Transforms time-domain acceleration into frequency-domain amplitude data utilizing NumPy's `rfft` routines to identify dominant frequencies and isolate sensor noise.
* **Band-Pass Filtering:** Apply dynamic low-cut and high-cut frequency filters. Transforms signals into the frequency domain, applies spectral masks, and utilizes inverse FFT (`irfft`) to reconstruct clean time-series data.
* **Geophone Differentiation:** Automatically differentiates velocity data (EHZ channels) to acceleration ($m/s^2$) using exact finite difference calculations.

### ⚡ 3. Efficeint Data Conversion
* **miniSEED to Parquet Conversion:** Scans massive unorganized directories of `.mseed` files, processes the waveforms via `obspy` (demean, detrend, interpolate), and outputs highly compressed, timestamped `.parquet` files.
* **Multi-Threaded Batch Processing:** Operations run on concurrent CPU threads, maximizing utilization for massive directory conversions.
* **Hardware Calibration Overrides:** Apply distinct sensitivity factors for MEMS Accelerometers (V4/V5 nodes) and Geophones to output accurate physical units.

### 🖥️ 4. Interactive Visualization & UI
* **Dual-Rendering Engine:** Outputs both static, publication-ready Matplotlib SVG graphics and highly interactive Plotly HTML dashboards supporting infinite drag-zoom, hovering, and data sub-sampling.
* **Dynamic Title Editor:** Edit generated Matplotlib SVG titles directly within the browser UI without re-running backend DSP algorithms.
* **Dark Mode & State Persistence:** CSS variable-driven dark/light mode toggle. Save and load exact GUI configurations (including filters, dampings, and offsets) via JSON config files.
* **Live Status Stream:** Real-time terminal output, progress bars, and pagination sent directly to the web interface via Server-Sent Events (SSE).

---

## 🔬 Methodology: Response Spectrum Calculation

The application utilizes the **Exact Analytical Method** (often referred to as the piecewise linear exact method) to calculate the response spectrum of a Single Degree of Freedom (SDOF) system. 

The governing differential equation of motion for an SDOF system subjected to ground acceleration $\ddot{u}_g(t)$ is:

$$\ddot{u}(t) + 2\xi\omega\dot{u}(t) + \omega^2 u(t) = -\ddot{u}_g(t)$$

Where:
* $u(t)$, $\dot{u}(t)$, $\ddot{u}(t)$ are the relative displacement, velocity, and acceleration of the mass.
* $\xi$ is the damping ratio.
* $\omega = 2\pi/T$ is the natural circular frequency for a given time period $T$.

Because raw earthquake data is discrete, the algorithm assumes the ground acceleration varies linearly between any two adjacent time steps ($t_i$ and $t_{i+1}$). By applying linear interpolation to the forcing function, the differential equation can be solved exactly at each time increment without the truncation errors found in standard numerical methods (like central difference).

For each step $\Delta t$, the slope of the acceleration is:

$$s = \frac{\ddot{u}_g(t_{i+1}) - \ddot{u}_g(t_i)}{\Delta t}$$

The exact relative displacement $u_{i+1}$ and velocity $v_{i+1}$ are computed iteratively using precise exponential decay terms ($e^{-\xi\omega\Delta t}$) and damped trigonometric responses ($\cos(\omega_d\Delta t)$ and $\sin(\omega_d\Delta t)$), where $\omega_d = \omega\sqrt{1-\xi^2}$.

Finally, the **Pseudo-Spectral Acceleration (PSA)** is calculated by scaling the maximum absolute displacement by the square of the natural frequency:

$$PSA = \omega^2 \cdot \max(|u|)$$

---

## 💻 Usage Guide: The 6 Core Modules

### 🔍 App 1: Global Archive Search
**Purpose:** Automates the precise retrieval and immediate visualization of earthquake events from massive global datasets.
* **Smart Tri-Source Fetching:** Paste a list of earthquake timestamps, and the engine will intelligently hunt for data. It checks local directories first, pulls from AWS S3 if missing locally, or connects directly to FDSNWS Dataselect servers for live Raspberry Shake waveforms.
* **Automated Window Extraction:** Define a lead-in and lag-out time (e.g., 10 seconds before, 90 seconds after). The app will automatically slice the massive daily datasets down to the exact event window.
* **Seamless Handoff:** App 1 can automatically generate `.json` configuration files for each discovered event, allowing you to instantly load them into App 2 for granular tweaking.

### 📈 App 2: Direct CSV/Parquet Visualization
**Purpose:** A highly granular visual analysis dashboard for deep-diving into specific, targeted datasets.
* **Multi-Stage Processing:** Apply multiple band-pass filters simultaneously to clean raw data. 
* **Dynamic Analytics:** Toggle side-by-side comparative plots (Raw vs. Filtered), frequency-domain FFT plots (per axis), and Pseudo-Spectral Acceleration (PSA) response plots across multiple damping ratios.
* **Unit Calibration Matrix:** Features a built-in mathematical unit converter. Instantly multiply sensor data by scalar fractions (e.g., multiply by `1/9.81` to convert $m/s^2$ to standard gravity *g*) and automatically update all axis labels.

### 📅 App 3: BLCA Data Availability Dashboard
**Purpose:** A diagnostic reporting tool designed to track sensor uptime and identify critical data gaps across entire networks.
* **Deep Directory Scanning:** Provide an S3 prefix or local drive letter, and App 3 will recursively crawl the entire archive structure (`YYYY/MM/DD/HH`).
* **Visual Health Mapping:** Generates clean, color-coded SVG calendar heatmaps indicating exact hours of operation, missing hours, and complete network dropouts for every individual station over multiple years.

### 🗄️ App 4: High-Speed Format Converter
**Purpose:** A brute-force, high-throughput batch processing engine for translating data formats.
* **Lossless Translation:** Converts highly compressed, binary `.parquet` files back into human-readable `.csv` formats, or vice versa, to save disk space.
* **Architecture Preservation:** Recursively traverses the input directory and perfectly mimics the nested folder structure (`Station/Archive/Year/Month/...`) in the destination directory, preventing data spillage.
* **Multi-Threaded:** Automatically parallelizes the conversion tasks across your available CPU cores to handle thousands of files in minutes.

### ⚖️ App 5: Multi-Station Comparative Analysis
**Purpose:** The ultimate tool for cross-analyzing structural responses across different sensors during the exact same seismic event.
* **Multi-Profile Stacking:** Load unlimited independent datasets (from different floors of a building or different geographic stations) and stack them on unified, synchronized timelines.
* **Physical Correction Overrides:** Swap structural axes (e.g., plot Station A's X-axis against Station B's Y-axis) or invert the polarity (multiply by -1) to dynamically correct physical sensor misalignments in the field without editing the source data.
* **Amplification Tracking:** Overlay FFT amplitudes and Response Spectrums from multiple stations on a single, color-coded Plotly graph to visually prove structural amplification or frequency shifts.

### 📡 App 6: Raspberry Shake to BLCA Converter
**Purpose:** The ingestion pipeline that bridges the gap between raw hardware traces and the analytical database.
* **miniSEED Parsing:** Reads raw, unorganized `.mseed` files downloaded from nodes or FDSN servers.
* **Automated Data Cleaning:** Utilizes `obspy` to automatically merge broken traces, demean the signal to remove DC offsets, and linearly detrend the data.
* **Sensor Math:** Applies strict sensitivity calibrations. Automatically differentiates raw Geophone velocity data (EHZ channels) into usable acceleration data ($m/s^2$) via time-step gradient calculations.
* **Archive Formatting:** Interpolates all data to a uniform target frequency (e.g., 100Hz) and outputs perfectly structured hourly `.parquet` files ready for Apps 1 and 2.

---

## 🛠️ Prerequisites & Installation

### Requirements
* **Operating System:** Windows 10/11 (Required for the `run_master.bat` automated setup script).
* **Python:** [Python 3.8+](https://www.python.org/downloads/) installed and added to your system `PATH`.
* **AWS Credentials:** Required *only* if accessing S3 cloud archive functionalities.

### Quick Start
Deployment is streamlined via an automated Windows batch script. 

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/mr-tanvirx/Earthquake-Data-Processor-Master-App.git](https://github.com/mr-tanvirx/Earthquake-Data-Processor-Master-App.git)
   cd earthquake-data-processor
2. **Run the Automated Setup:**
   Double-click the `run_master.bat` file in the project root.
   
   *What happens next?*
   * Creates a dedicated Python virtual environment (`venv`).
   * Upgrades `pip` and installs essential scientific packages (`pandas`, `numpy`, `obspy`, `pyarrow`, `fastparquet`).
   * Installs web and cloud dependencies (`flask`, `boto3`, `plotly`, `matplotlib`).
   * Launches the Flask development server and automatically opens your default web browser to the local network address (`http://localhost:5000`).

---

---

## ⚠️ Troubleshooting

* **Server immediately closes when running `.bat`:** Ensure Python is added to your Windows `PATH`. Open a command prompt and type `python --version` to verify.
* **Obspy Installation Errors:** Ensure you have the appropriate C++ build tools installed on Windows if binary wheels are not available for your specific Python version.
* **AWS Connectivity Errors:** Ensure you populate `AWS_ACCESS_KEY` and `AWS_SECRET_KEY` variables securely within `processor_shared.py` to execute S3 queries.
* **Interactive Plots not Loading:** The stretch/zoom Plotly features generate temporary files in `temp_interactive_plots`. Ensure the application has write-permissions in its directory.

---


## 📂 Project Structure

```text
├── master_app.py              # Main Flask application, routing, and SSE task orchestrator
├── processor_shared.py        # Core DSP logic, Matplotlib/Plotly rendering, and AWS S3 config
├── processor_app1.py          # App 1: Search EQ Archive (S3/Local/FDSN)
├── processor_app2.py          # App 2: Visualizing CSV/Parquet Data
├── processor_app3.py          # App 3: BLCA Data Availability Calendars
├── processor_app4.py          # App 4: Parquet <-> CSV Batch Converter
├── processor_app5.py          # App 5: Multi-Station Comparative Engine
├── processor_app6.py          # App 6: miniSEED to Parquet Archiver
└── run_master.bat             # Automated Windows environment deployment script



