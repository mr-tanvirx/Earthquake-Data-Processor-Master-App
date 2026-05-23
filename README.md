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


<img width="999" height="878" alt="Screenshot 2026-05-23 125429" src="https://github.com/user-attachments/assets/e46b29bb-1862-4ec0-ad92-af71ddc3f551" />

<img width="1037" height="320" alt="Screenshot 2026-05-23 125446" src="https://github.com/user-attachments/assets/f4da6d72-3947-4b3f-a0bd-ed38b146e5df" />

<img width="1024" height="778" alt="Screenshot 2026-05-23 125502" src="https://github.com/user-attachments/assets/960d7a81-4bd3-4f4e-8722-43173bc047c3" />

<img width="1033" height="737" alt="Screenshot 2026-05-23 125511" src="https://github.com/user-attachments/assets/0a8dab6b-f313-4daf-8dec-36063c3fb02c" />

<img width="1867" height="881" alt="Screenshot 2026-05-23 125525" src="https://github.com/user-attachments/assets/8ce3d191-b24e-448d-8306-134af9e8f3e7" />

*(Caption: Granular visualization settings and state management)*

### 3. BLCA Data Availability Dashboard (App 3)
A diagnostic tool that scans massive structural monitoring archives to visualize uptime and data completeness.
* **Cloud & Local Scanning:** Maps the directory structures of both local hard drives and AWS S3 buckets.
* **Visual Calendar Generation:** Renders a comprehensive SVG calendar dashboard highlighting specific hours and days where sensor data is available, missing, or corrupted.


<img width="1020" height="821" alt="Screenshot 2026-05-23 125731" src="https://github.com/user-attachments/assets/9dd36621-fac6-47c6-af13-bd8e75ec15c6" />

<img width="937" height="724" alt="Screenshot 2026-05-23 125750" src="https://github.com/user-attachments/assets/a0526738-1687-4926-b7ef-4d4934a29261" />

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



<img width="947" height="848" alt="Screenshot 2026-05-23 131059" src="https://github.com/user-attachments/assets/361ff285-a8f8-4598-9215-1561362c72ff" />

<img width="845" height="228" alt="Screenshot 2026-05-23 131123" src="https://github.com/user-attachments/assets/bf2c6100-a1e2-479f-a7a2-003aa5fd2ea8" />

<img width="856" height="773" alt="Screenshot 2026-05-23 131138" src="https://github.com/user-attachments/assets/3c02a8f8-bc5d-4b39-8934-0f18ed2c1355" />

*(Caption: Building a multi-profile comparative overlay)*






### 6. Example of a 3-profile comparative overlay (App 5)
<img width="3150" height="2187" alt="Compare_2026-05-23_11-52-49_Filt_0to20Hz_X" src="https://github.com/user-attachments/assets/faf20eb9-dd00-49dc-8983-8c267d31e918" />
<img width="3150" height="2187" alt="Compare_2026-05-23_12-06-34_Resp_X" src="https://github.com/user-attachments/assets/18d2cabd-7ddb-41a9-8af0-b44366eff9ab" />

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
