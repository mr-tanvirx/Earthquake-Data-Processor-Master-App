# Earthquake Data Processor Suite

A comprehensive, modular web application designed for the extraction, processing, and visualization of high-frequency seismic and structural monitoring data. Built with a robust Flask backend and an interactive web frontend, this suite automates complex analytical tasks such as Fast Fourier Transform (FFT) filtering, response spectrum generation, and multi-profile comparative analysis.

<img width="1837" height="903" alt="Screenshot 2026-05-23 125017" src="https://github.com/user-attachments/assets/09137628-b69e-4975-818e-8f5df8723632" />

*(Caption: Overview of the Master App WebUI)*

## Core Capabilities

The suite is divided into five distinct processing modules, each engineered to handle a specific stage of the seismic data workflow.

### 1. Global Archive Search & Processing (App 1)
Automates the retrieval of earthquake data across distributed storage systems.
* **Dual-Source Extraction:** Simultaneously pulls data from local archive directories and AWS S3 cloud storage buckets.
* **Automated Data Slicing:** Extracts precise time windows (e.g., 10 seconds before and 90 seconds after an event) from massive `.parquet` datasets.
* **Analytical Plotting:** Generates both static (Matplotlib SVG) and interactive (Plotly HTML) visualizations of raw acceleration, filtered signals, and response spectrums.


<img width="1107" height="741" alt="Screenshot 2026-05-23 125244" src="https://github.com/user-attachments/assets/59bd7349-3e34-407c-af68-53afc5a5d28c" />

*(Caption: Configuring a global search and filter parameters)*

### 2. Direct CSV/Parquet Visualization (App 2)
Provides a granular analysis tool for specific, pre-downloaded datasets.
* **Config State Management:** Export and import precise analysis configurations as `.json` files to perfectly recreate past analysis states.
* **Advanced Filtering:** Apply customizable band-pass filters and damping ratios to targeted timeframes.
* **Batch Execution:** Queue multiple local station folders for sequential, automated processing.


<img width="999" height="878" alt="Screenshot 2026-05-23 125429" src="https://github.com/user-attachments/assets/b2c1b2a1-2be1-4794-8419-781888a625e7" />
<img width="1037" height="455" alt="Screenshot 2026-05-23 125446" src="https://github.com/user-attachments/assets/e65486c3-9f91-4dc9-8e8d-e9b430a33e6b" />
<img width="1024" height="778" alt="Screenshot 2026-05-23 125502" src="https://github.com/user-attachments/assets/fc0a1506-329b-4e10-ab16-ea5f0c0c6d36" />
<img width="1033" height="786" alt="Screenshot 2026-05-23 125511" src="https://github.com/user-attachments/assets/ca6d2287-9042-443d-ae8f-6b3fbbbd3458" />
<img width="1867" height="881" alt="Screenshot 2026-05-23 125525" src="https://github.com/user-attachments/assets/4e491ba7-a198-4d85-9e61-8e8fcd6a2239" />

*(Caption: Granular visualization settings and state management)*

### 3. BLCA Data Availability Dashboard (App 3)
A diagnostic tool that scans massive structural monitoring archives to visualize uptime and data completeness.
* **Cloud & Local Scanning:** Maps the directory structures of both local hard drives and AWS S3 buckets.
* **Visual Calendar Generation:** Renders a comprehensive SVG calendar dashboard highlighting specific hours and days where sensor data is available, missing, or corrupted.


<img width="1020" height="821" alt="Screenshot 2026-05-23 125731" src="https://github.com/user-attachments/assets/9dd36621-fac6-47c6-af13-bd8e75ec15c6" />
<img width="937" height="879" alt="Screenshot 2026-05-23 125750" src="https://github.com/user-attachments/assets/f40405fc-5d89-48ab-bd06-84f8523322f9" />
<img width="1526" height="815" alt="Screenshot 2026-05-23 130751" src="https://github.com/user-attachments/assets/2c2bdd9f-813a-48b6-a8f8-1fec9346498d" />
<img width="1515" height="619" alt="Screenshot 2026-05-23 130736" src="https://github.com/user-attachments/assets/1e3220d3-b5da-446d-884f-a364cc8aa2b1" />

*(Caption: Generated SVG calendar showing sensor uptime)*

### 4. High-Speed Format Converter (App 4)
A localized batch processing engine for data transformation.
* **Automated Batching:** Recursively scans a root directory for thousands of compressed `.parquet` files.
* **Structural Integrity:** Converts all files to `.csv` format while perfectly replicating the original folder hierarchy in the output destination.

<img width="952" height="491" alt="Screenshot 2026-05-23 130946" src="https://github.com/user-attachments/assets/b6a50b1b-0ca9-4479-8bed-89a9cfc69e41" />

*(Caption: Batch conversion progress interface)*

### 5. Multi-Event Comparative Analysis (App 5)
An advanced graphing engine for cross-analyzing distinct seismic events or structural profiles.
* **Custom Timeline Overlays:** Overlay data from different sensors or entirely different earthquakes onto a single, synchronized relative timeline.
* **Data Manipulation:** Swap X and Y axes or multiply data by -1 to correct sensor misalignments on the fly.
* **Comparative Spectrums:** Generate grouped response spectrum plots mapping multiple damping ratios across multiple structural profiles simultaneously.

<img width="947" height="848" alt="Screenshot 2026-05-23 131059" src="https://github.com/user-attachments/assets/7badde58-787d-4e07-9910-be9e82c50d35" />
<img width="845" height="441" alt="Screenshot 2026-05-23 131123" src="https://github.com/user-attachments/assets/bae072d5-6d3a-49c8-bbc5-7f774c59aa11" />
<img width="856" height="773" alt="Screenshot 2026-05-23 131138" src="https://github.com/user-attachments/assets/5888d3df-0b25-40af-baf0-17d899467073" />
<img width="986" height="676" alt="Screenshot 2026-05-23 131220" src="https://github.com/user-attachments/assets/ede23ae9-c285-47c3-a5e5-f837b4b4526f" />
<img width="1254" height="906" alt="Screenshot 2026-05-23 131330" src="https://github.com/user-attachments/assets/9dd6cb83-8102-4b74-8232-4bfa0feea556" />

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
3. Double-click the `run_master.bat` file. 
4. The script will automatically:
   * Create an isolated virtual environment (`venv`).
   * Install all required dependencies (`flask`, `pandas`, `numpy`, `matplotlib`, `pyarrow`, `fastparquet`, `boto3`, `plotly`).
   * Launch the Flask server.
5. Your default web browser will automatically open to `http://localhost:5000`.

### AWS S3 Configuration
If utilizing the cloud-search features (App 1 and App 3), ensure you populate the `AWS_ACCESS_KEY` and `AWS_SECRET_KEY` variables securely within `processor_shared.py` (or load them via a `.env` file to prevent exposing credentials).
