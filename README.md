<div align="center">
  
  # 🌍 Earthquake Data Processor Suite
  
  *A comprehensive, modular web application designed for the extraction, processing, conversion, detection, remote hardware management, and visualization of high-frequency seismic and structural monitoring data.*
  
  ![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)
  ![Flask](https://img.shields.io/badge/Flask-Web_UI-black?style=for-the-badge&logo=flask&logoColor=white)
  ![Pandas](https://img.shields.io/badge/Pandas-Data_Processing-150458?style=for-the-badge&logo=pandas&logoColor=white)
  ![AWS S3](https://img.shields.io/badge/AWS_S3-Cloud_Storage-569A31?style=for-the-badge&logo=amazons3&logoColor=white)
  ![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
</div>

---

## 📖 Overview

This repository contains a 9-module, web-based analytics and hardware management suite engineered for civil, structural, and seismological researchers. Built on a robust Flask backend, it seamlessly integrates local file processing, AWS S3 cloud archiving, direct FDSNWS server querying, remote SSH field node management, automated earthquake detection, and real-time hardware telemetry visualization.

The suite automates complex analytical pipelines including Fast Fourier Transform (FFT) analysis, numerical integration, mathematical differentiation of velocity to acceleration, multi-damping response spectrum generation, multi-profile comparative analysis, multi-phase seismic event scanning, and remote field node data ingestion.

<img width="1364" height="1263" alt="Screenshot 2026-09-02 204007" src="https://github.com/user-attachments/assets/2a1789d4-c341-4b75-88dd-3ad166a3e106" />

---

## ✨ Comprehensive Features

### 📡 1. Data Acquisition, Networking & Remote Management
* **Multi-Source Cloud & Local Extraction:** Simultaneously query and pull data from local archive directories, AWS S3 cloud storage buckets, and direct FDSNWS servers.
* **Direct FDSNWS Integration:** Download continuous waveforms directly from Raspberry Shake FDSN servers via `dataselect` queries based on precise event time windows.
* **Remote Device Management & SSH Retrieval:** Dynamically check tri-endpoint IP connectivity (Local, Cloud 1, Cloud 2 via Tailscale) and pull recorded hourly `.parquet` / `.csv` data directly from field hardware nodes using Paramiko SSH.
* **Smart Caching:** Prevents redundant downloads by checking local directories before executing AWS S3 or network queries.

### 🧮 2. Signal Processing & Mathematical Analysis
* **Response Spectrum Generation:** Computes highly accurate Pseudo-Spectral Acceleration (PSA) across customizable damping ratios and time periods using the Exact Analytical Method.
* **Fast Fourier Transform (FFT):** Transforms time-domain acceleration into frequency-domain amplitude data utilizing NumPy's `rfft` routines to identify dominant frequencies and isolate sensor noise.
* **Band-Pass Filtering:** Apply dynamic low-cut and high-cut frequency filters with inverse FFT (`irfft`) reconstruction.
* **Geophone Velocity Differentiation:** Automatically differentiates velocity data (EHZ channels) to acceleration ($m/s^2$) using exact finite difference calculations.
* **Automated Multi-Phase EQ Detection:** Multi-threshold trigger engine evaluating Phase 1, Phase 2, and Phase 3 signal windows across customizable axes and baseline conditions.

### ⚡ 3. Efficient Data Conversion & Ingestion
* **miniSEED & Julian Day Processing:** Scans `.mseed` files and Julian day channel directories (`.325`), cleans waveforms via ObsPy (demean, detrend, interpolate), and outputs compressed, timestamped `.parquet` files.
* **Format Interoperability:** Converts seamlessly between `.parquet` and `.csv` formats, preserving nested folder structures (`Station/Archive/Year/Month/...`).
* **Multi-Threaded Batch Processing:** Operations parallelize across concurrent CPU threads to maximize throughput during massive archive scans and conversions.
* **Hardware Calibration Overrides:** Apply distinct sensitivity factors for MEMS Accelerometers (V4/V5 nodes) and Geophones to output accurate physical units.

### 🖥️ 4. Interactive Visualization & Telemetry
* **Dual-Rendering Engine:** Outputs both static, publication-ready Matplotlib SVG graphics and interactive Plotly HTML dashboards supporting infinite drag-zoom, hovering, and data sub-sampling.
* **Hardware Telemetry Monitoring:** Visualizes system health metrics (CPU usage, CPU temperature, RAM/Swap usage, disk speeds, voltage, clock frequency, throttling flags) across multiple remote hardware nodes.
* **Dynamic Title Editor & State Persistence:** Edit SVG titles directly within the UI and save/load GUI configurations via JSON files.
* **Live Status Stream:** Real-time terminal logs, progress bars, and pagination sent to the web interface via Server-Sent Events (SSE).

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

$$PSA = \omega^2 \cdot \max(\vert{}u\vert{})$$

---

<p align="center">
  <img width="49%" alt="Compare Plot 1" src="https://github.com/user-attachments/assets/f9038e57-b77e-4e1e-bec9-c5ab8d8cf450" />
  <img width="49%" alt="Compare Plot 2" src="https://github.com/user-attachments/assets/66917bfd-71e8-4e85-9e4f-34fa2a4df051" />
</p>

---

## 💻 Usage Guide: The 9 Core Modules

### 🔍 App 1: Global Archive Search
**Purpose:** Automates the precise retrieval and immediate visualization of earthquake events from massive global datasets.
* **Smart Tri-Source Fetching:** Paste a list of earthquake timestamps, and the engine will intelligently hunt for data. It checks local directories first, pulls from AWS S3 if missing locally, or connects directly to FDSNWS Dataselect servers for live Raspberry Shake waveforms.
* **Automated Window Extraction:** Define a lead-in and lag-out time (e.g., 10 seconds before, 90 seconds after). The app automatically slices the massive daily datasets down to the exact event window.
* **Seamless Handoff:** App 1 automatically generates `.json` configuration files for each discovered event, allowing instant loading into App 2 for granular tweaking.

<p align="center">
 
 <img width="1364" height="1263" alt="Screenshot 2026-09-02 204007" src="https://github.com/user-attachments/assets/f5c8eae2-88f0-45fd-bf4e-13eba5ffc6ea" />


</p>

### 📈 App 2: Direct CSV/Parquet Visualization
**Purpose:** A highly granular visual analysis dashboard for deep-diving into specific, targeted datasets.
* **Multi-Stage Processing:** Apply multiple band-pass filters simultaneously to clean raw data. Auto-center baselines to zero using Mode Average or parse ETABS formatted files.
* **Dynamic Analytics:** Toggle side-by-side comparative plots (Raw vs. Filtered), frequency-domain FFT plots (per axis), and Pseudo-Spectral Acceleration (PSA) response plots across multiple damping ratios.
* **Unit Calibration Matrix:** Features a built-in mathematical unit converter. Instantly multiply sensor data by scalar fractions (e.g., multiply by `1/9.81` to convert $m/s^2$ to standard gravity *g*) and automatically update all axis labels.

<img width="1374" height="1120" alt="Screenshot 2026-09-02 204038" src="https://github.com/user-attachments/assets/b3a92668-b09b-4ac8-8bfd-0f3a98b91870" />


### 📅 App 3: BLCA Data Availability Dashboard
**Purpose:** A diagnostic reporting tool designed to track sensor uptime and identify critical data gaps across entire networks.
* **Deep Directory & S3 Scanning:** Crawl local folder hierarchies or AWS S3 prefixes to generate interactive visual directory tree structures.
* **Visual Health Mapping:** Generates clean, color-coded SVG calendar heatmaps indicating exact hours of operation, missing hours, and complete network dropouts for every station over multiple years, with custom station suffix labeling.

<img width="1376" height="895" alt="Screenshot 2026-09-02 204046" src="https://github.com/user-attachments/assets/0b8757a2-0979-4140-a11b-57988672500e" />


### 🗄️ App 4: High-Speed Format Converter
**Purpose:** A brute-force, high-throughput batch processing engine for translating data formats.
* **Lossless Translation:** Converts highly compressed, binary `.parquet` files back into human-readable `.csv` formats, or vice versa.
* **Architecture Preservation:** Recursively traverses input directories and mimics nested folder structures (`Station/Archive/Year/Month/...`) in the destination directory.
* **Multi-Threaded Execution:** Parallelizes conversion tasks across available CPU cores to handle thousands of files in minutes.

<img width="1386" height="940" alt="Screenshot 2026-09-02 204054" src="https://github.com/user-attachments/assets/3167d456-e2f6-48e3-b8a0-9644ce7ce097" />


### ⚖️ App 5: Multi-Station Comparative Analysis
**Purpose:** Cross-analyzes structural responses across different sensors or floors during the exact same seismic event.
* **Multi-Profile Stacking:** Load independent datasets and stack them on unified, synchronized timelines.
* **Physical Correction Overrides:** Swap structural axes (e.g., plot Station A's X-axis against Station B's Y-axis), invert polarity (-1 scalar), or select baseline removal modes (Mean, Mode, Median, Linear Detrend).
* **Format Flexibility & Scaling:** Seamlessly handles standard datasets, ETABS 100Hz formats, and raw IMV streams (resampling and scaling IMV data to match reference time grids).
* **Amplification Tracking:** Overlay FFT amplitudes and Response Spectrums from multiple stations on color-coded Plotly/Matplotlib graphs to prove structural amplification or frequency shifts.

<img width="1374" height="1260" alt="Screenshot 2026-09-02 204103" src="https://github.com/user-attachments/assets/53e13b8b-b969-4dbd-a965-39e41216c058" />


### 📡 App 6: Raspberry Shake to BLCA Converter
**Purpose:** The ingestion pipeline that bridges the gap between raw hardware traces and the analytical database.
* **miniSEED & Julian Day Parsing:** Reads raw `.mseed` files or Julian Day folder structures (`.325`) downloaded from nodes or FDSN servers.
* **Automated Data Cleaning:** Demeans, detrends, and interpolates data to uniform target sample rates (e.g., 100Hz). Automatically filters out short packet bleed-over files (<5s).
* **Hardware Sensitivity Math:** Applies sensitivity calibrations for MEMS Accelerometers (V4/V5 nodes) and differentiates Geophone velocity data (EHZ) into acceleration ($m/s^2$) via time-step gradient calculations.
* **Archive Structuring:** Outputs structured hourly `.parquet` files formatted either for standard BLCA archives or App 1 custom root directories.

<p align="center">
  <img width="1386" height="894" alt="Screenshot 2026-09-02 204113" src="https://github.com/user-attachments/assets/071a0ba0-65a0-45c1-96c6-13c96128b76a" />
</p>

### 🚨 App 7: EQ Auto Scanner
**Purpose:** An automated earthquake detection engine designed to scan massive continuous waveform archives and pinpoint uncataloged seismic events.
* **Multi-Phase Trigger Algorithm:** Implements a cascading 3-phase detection pipeline (Phase 1 trigger threshold, Phase 2 medium certainty validation, and Phase 3 high certainty confirmation) with customizable hit counts and time windows.
* **Flexible Logic & Pre-Filtering:** Configure unified or individual axis thresholds (X, Y, Z), trigger condition logic (`Any` vs. `All`), pre-filters (0-10Hz or 0-20Hz bandpass), baseline auto-centering, and discard limits for noisy channels.
* **Automated Event Artifact Export:** Automatically extracts event time windows (pre/post trigger seconds), exports raw CSV slices, generates publication plots, and outputs ready-to-run App 2 `.json` config files for each detected event.

<p align="center">
  <img width="1383" height="856" alt="Screenshot 2026-09-02 204121" src="https://github.com/user-attachments/assets/ea61117e-4a5c-4963-83f4-f78395313321" />
</p>

### 🌐 App 8: Device Manager & SSH Suite
**Purpose:** A centralized hardware management and remote network retrieval dashboard for field-deployed Raspberry Shake and BLCA nodes.
* **Tri-Endpoint Network Health Sweeps:** Probes Local IP, Cloud 1, and Cloud 2 (Tailscale) network endpoints concurrently to report real-time station connectivity status (`ONLINE` / `OFFLINE`).
* **Remote Data Retrieval via SSH:** Connects directly to field nodes via `paramiko` SSH to download current hour or previous hour recorded `.parquet` / `.csv` data files directly into structured local directories.
* **Live Web Stream Monitoring:** Direct interface connection to open live wave streams hosted on remote field node servers.

<p align="center">
  <img width="1373" height="1218" alt="Screenshot 2026-09-02 204319" src="https://github.com/user-attachments/assets/e3b7ad0e-6ace-47dc-b919-9c1eef4d139f" />
</p>

### 📊 App 9: Resource Monitor Visualizer
**Purpose:** A telemetry and infrastructure performance analytics tool for monitoring Raspberry Pi field nodes and processing server hardware.
* **Multi-Device Telemetry Overlay:** Stack and cross-compare continuous hardware telemetry metrics (CPU %, CPU Temp °C, RAM %, Disk %, Read/Write speeds, Reader/Writer/Monitor process RAM & Swap, CPU Voltage, Clock Frequency, Undervoltage and Frequency Throttling flags).
* **Statistical Overlays & Smoothing:** Toggle raw telemetry traces, rolling moving averages (SMA), horizontal baseline mean lines, and min/max extrema markers.
* **Dual Visualization Stack:** Generates shared X-axis stacked Plotly interactive HTML dashboards and publication-ready Matplotlib vector graphics (SVG).

<p align="center">
 <img width="1373" height="1039" alt="Screenshot 2026-09-02 204435" src="https://github.com/user-attachments/assets/005b5adc-b9e8-48a8-bc94-367e58c02ea8" />
</p>

---

## 🛠️ Prerequisites & Installation

### Requirements
* **Operating System:** Windows 10/11 (Required for the `run_master.bat` automated setup script).
* **Python:** [Python 3.8+](https://www.python.org/downloads/) installed and added to your system `PATH`.
* **AWS Credentials:** Required *only* if accessing S3 cloud archive functionalities.
* **Paramiko & SSH Credentials:** Required *only* for App 8 remote node downloads (configured via `Config.txt`).

### Quick Start
Deployment is streamlined via an automated Windows batch script. 

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/mr-tanvirx/Earthquake-Data-Processor-Master-App.git](https://github.com/mr-tanvirx/Earthquake-Data-Processor-Master-App.git)
   cd earthquake-data-processor<img width="1364" height="1263" alt="Screenshot 2026-09-02 204007" src="https://github.com/user-attachments/assets/69de3fb9-d246-452e-8307-24488725b8e3" />
