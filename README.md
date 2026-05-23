# Earthquake Data Processor Suite

A comprehensive, modular web application designed for the extraction, processing, and visualization of high-frequency seismic and structural monitoring data. Built with a robust Flask backend and an interactive web frontend, this suite automates complex analytical tasks such as Fast Fourier Transform (FFT) filtering, response spectrum generation, and multi-profile comparative analysis.

![Main Dashboard Screenshot](link_to_your_main_dashboard_image_here.png)
<img width="1837" height="903" alt="Screenshot 2026-05-23 125017" src="https://github.com/user-attachments/assets/09137628-b69e-4975-818e-8f5df8723632" />

*(Caption: Overview of the Master App WebUI)*

## Core Capabilities

The suite is divided into five distinct processing modules, each engineered to handle a specific stage of the seismic data workflow.

### 1. Global Archive Search & Processing (App 1)
Automates the retrieval of earthquake data across distributed storage systems.
* **Dual-Source Extraction:** Simultaneously pulls data from local archive directories and AWS S3 cloud storage buckets.
* **Automated Data Slicing:** Extracts precise time windows (e.g., 10 seconds before and 90 seconds after an event) from massive `.parquet` datasets.
* **Analytical Plotting:** Generates both static (Matplotlib SVG) and interactive (Plotly HTML) visualizations of raw acceleration, filtered signals, and response spectrums.

![App 1 Screenshot](link_to_app1_screenshot_here.png)
*(Caption: Configuring a global search and filter parameters)*

### 2. Direct CSV/Parquet Visualization (App 2)
Provides a granular analysis tool for specific, pre-downloaded datasets.
* **Config State Management:** Export and import precise analysis configurations as `.json` files to perfectly recreate past analysis states.
* **Advanced Filtering:** Apply customizable band-pass filters and damping ratios to targeted timeframes.
* **Batch Execution:** Queue multiple local station folders for sequential, automated processing.

![App 2 Screenshot](link_to_app2_screenshot_here.png)
*(Caption: Granular visualization settings and state management)*

### 3. BLCA Data Availability Dashboard (App 3)
A diagnostic tool that scans massive structural monitoring archives to visualize uptime and data completeness.
* **Cloud & Local Scanning:** Maps the directory structures of both local hard drives and AWS S3 buckets.
* **Visual Calendar Generation:** Renders a comprehensive SVG calendar dashboard highlighting specific hours and days where sensor data is available, missing, or corrupted.

![App 3 Screenshot](link_to_app3_screenshot_here.png)
*(Caption: Generated SVG calendar showing sensor uptime)*

### 4. High-Speed Format Converter (App 4)
A localized batch processing engine for data transformation.
* **Automated Batching:** Recursively scans a root directory for thousands of compressed `.parquet` files.
* **Structural Integrity:** Converts all files to `.csv` format while perfectly replicating the original folder hierarchy in the output destination.

![App 4 Screenshot](link_to_app4_screenshot_here.png)
*(Caption: Batch conversion progress interface)*

### 5. Multi-Event Comparative Analysis (App 5)
An advanced graphing engine for cross-analyzing distinct seismic events or structural profiles.
* **Custom Timeline Overlays:** Overlay data from different sensors or entirely different earthquakes onto a single, synchronized relative timeline.
* **Data Manipulation:** Swap X and Y axes or multiply data by -1 to correct sensor misalignments on the fly.
* **Comparative Spectrums:** Generate grouped response spectrum plots mapping multiple damping ratios across multiple structural profiles simultaneously.

![App 5 Screenshot](link_to_app5_screenshot_here.png)
*(Caption: Building a multi-profile comparative overlay)*

---

## Technical Architecture

* **Frontend:** HTML5, CSS Variables (Dark/Light mode native), JavaScript (Server-Sent Events for live terminal streaming).
* **Backend:** Python 3, Flask.
* **Data Processing:** Pandas, NumPy, PyArrow, FastParquet.
* **Signal Processing:** Custom Python numerical integration for Response Spectrum (Newmark-beta methodology), NumPy FFT for signal filtering.
* **Visualization:** Matplotlib (Agg backend for thread-safe SVGs), Plotly (Interactive HTML exports).
* **Cloud Integration:** Boto3 (AWS S3).

---

## Installation and Execution

This application is packaged with an automated setup script designed for Windows environments.

1. Clone this repository to your local machine.
2. Ensure Python 3 is installed and added to your system PATH.
3. [cite_start]Double-click the `run_master.bat` file[cite: 41]. 
4. The script will automatically:
   * [cite_start]Create an isolated virtual environment (`venv`)[cite: 41].
   * [cite_start]Install all required dependencies (`flask`, `pandas`, `numpy`, `matplotlib`, `pyarrow`, `fastparquet`, `boto3`, `plotly`)[cite: 42].
   * [cite_start]Launch the Flask server[cite: 42].
5. Your default web browser will automatically open to `http://localhost:5000`.

### AWS S3 Configuration
If utilizing the cloud-search features (App 1 and App 3), ensure you populate the `AWS_ACCESS_KEY` and `AWS_SECRET_KEY` variables securely within `processor_shared.py` (or load them via a `.env` file to prevent exposing credentials).
