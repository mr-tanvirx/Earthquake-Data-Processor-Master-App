<div align="center">
 

  # 🌍 Earthquake Data Processor Suite
  
  *A comprehensive, modular web application designed for the extraction, processing, and visualization of high-frequency seismic and structural monitoring data.*
  
  ![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)
  ![Flask](https://img.shields.io/badge/Flask-Web_UI-black?style=for-the-badge&logo=flask&logoColor=white)
  ![Pandas](https://img.shields.io/badge/Pandas-Data_Processing-150458?style=for-the-badge&logo=pandas&logoColor=white)
  ![AWS S3](https://img.shields.io/badge/AWS_S3-Cloud_Storage-569A31?style=for-the-badge&logo=amazons3&logoColor=white)
  ![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
</div>

---

## 📖 Overview

This repository contains a modular, web-based analytics dashboard engineered for civil and structural engineering researchers. Built on a robust Flask backend, it integrates local file processing with AWS S3 cloud archiving. The suite automates complex analytical pipelines including Fast Fourier Transform (FFT) filtering, numerical integration (acceleration to velocity/displacement), response spectrum generation, and multi-profile comparative analysis.

<img src="https://github.com/user-attachments/assets/94d9962e-baa6-4fd6-885d-14ee4b105193" alt="Project Banner" width="100%">
<p align="center">
  <img width="49%" alt="Compare Plot 1" src="https://github.com/user-attachments/assets/f9038e57-b77e-4e1e-bec9-c5ab8d8cf450" />
  <img width="49%" alt="Compare Plot 2" src="https://github.com/user-attachments/assets/66917bfd-71e8-4e85-9e4f-34fa2a4df051" />
</p>

---

## ✨ Features

- **🔍 Global Dual-Source Extraction:** Simultaneously pull data from local archive directories and AWS S3 cloud storage buckets.
- **⚡ High-Speed Batch Conversion:** Recursively traverse directory trees to convert thousands of compressed `.parquet` files to `.csv` format while preserving folder hierarchy.
- **🔄 Automated Task Chaining:** Queue multiple local station folders for sequential, automated FFT filtering and plotting.
- **⏱️ Advanced Signal Processing:** Implement custom Python numerical integration for Response Spectrum and NumPy FFT for sensor noise elimination.
- **🖥️ Interactive Dashboards:** Generate comprehensive SVG calendar heatmaps for sensor uptime and output interactive Plotly HTML graphs with infinite zoom.
- **🛑 State Management:** Export and import precise analysis configurations as `.json` files to recreate past analysis states instantly.
- **🚀 One-Click Setup:** Includes a `.bat` script that automatically creates isolated virtual environments, installs scientific dependencies, and launches the server.

---

## 🛠️ Prerequisites

Before you begin, ensure you have met the following requirements:
* **Operating System:** Windows 10/11 (Required for the `run_master.bat` automated setup script).
* **Python:** [Python 3.8+](https://www.python.org/downloads/) installed and added to your system `PATH`.
* **AWS Credentials:** Required *only* if accessing S3 cloud archive functionalities (configured via standard AWS credential chains or within `processor_shared.py`).

---

## 🚀 Installation & Quick Start

Deployment is streamlined via an automated Windows batch script. 

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mr-tanvirx/Earthquake-Data-Processor-Master-App.git
   cd earthquake-data-processor
   ```

2. **Run the Automated Setup:**
   Double-click the `run_master.bat` file in the project root.
   
   *What happens next?*
   - The script creates a dedicated Python virtual environment (`venv`).
   - It upgrades `pip` and installs essential scientific packages (`pandas`, `numpy`, `pyarrow`, `fastparquet`).
   - It installs web and cloud dependencies (`flask`, `boto3`, `plotly`, `matplotlib`).
   - It launches the Flask development server and automatically opens your default web browser to the app's local network address (`http://localhost:5000`).

---

## 💻 Usage Guide

The suite is divided into five distinct processing modules.

### App 1: Global Archive Search
Automates the retrieval of earthquake data. Extract precise time windows from massive datasets and generate static (SVG) and interactive (HTML) visualizations.
<p align="center"><img width="900" src="https://github.com/user-attachments/assets/59bd7349-3e34-407c-af68-53afc5a5d28c" /></p>

### App 2: Direct CSV/Parquet Visualization
A granular visual analysis tool for specific datasets. Apply customizable band-pass filters and damping ratios to targeted timeframes.
<p align="center">
  <img width="49%" src="https://github.com/user-attachments/assets/e46b29bb-1862-4ec0-ad92-af71ddc3f551" />
  <img width="49%" src="https://github.com/user-attachments/assets/960d7a81-4bd3-4f4e-8722-43173bc047c3" />
</p>
<p align="center"><img width="100%" src="https://github.com/user-attachments/assets/8ce3d191-b24e-448d-8306-134af9e8f3e7" /></p>

### App 3: BLCA Data Availability Dashboard
A diagnostic tool that scans local and cloud directories to render SVG calendars highlighting sensor uptime.
<p align="center">
  <img width="49%" src="https://github.com/user-attachments/assets/9dd36621-fac6-47c6-af13-bd8e75ec15c6" />
  <img width="49%" src="https://github.com/user-attachments/assets/2c2bdd9f-813a-48b6-a8f8-1fec9346498d" />
</p>

### App 4: High-Speed Format Converter
A high-throughput batch processing engine for data transformation.
<p align="center"><img width="900" src="https://github.com/user-attachments/assets/b6a50b1b-0ca9-4479-8bed-89a9cfc69e41" /></p>

### App 5: Multi-Station Comparative Analysis
Cross-analyze distinct seismic event's record on different stations. Swap structural axes or multiply data by scalars to dynamically correct sensor misalignments during plotting.
<p align="center">
  <img width="49%" src="https://github.com/user-attachments/assets/361ff285-a8f8-4598-9215-1561362c72ff" />
  <img width="49%" src="https://github.com/user-attachments/assets/3c02a8f8-bc5d-4b39-8934-0f18ed2c1355" />
</p>

---

## 📂 Project Structure

```text
├── master_app.py              # Main Flask application and asynchronous task orchestrator
├── processor_shared.py        # Core signal processing logic, mathematical integration, and AWS config
├── processor_app1.py          # App 1: Search EQ Archive (S3/Local)
├── processor_app2.py          # App 2: Visualizing CSV Data
├── processor_app3.py          # App 3: BLCA Data Availability
├── processor_app4.py          # App 4: Parquet to CSV batch converter
├── processor_app5.py          # App 5: Compare Plots engine
└── run_master.bat             # Automated Windows deployment script
```

---

## ⚠️ Troubleshooting

* **Server immediately closes when running `.bat`:** Ensure Python is added to your Windows `PATH`. Open a command prompt and type `python --version` to verify.
* **AWS Connectivity Errors:** Ensure you populate `AWS_ACCESS_KEY` and `AWS_SECRET_KEY` variables securely within `processor_shared.py` to execute S3 queries in Apps 1 and 3.
* **Missing Interactive Plots:** The interactive plotting relies on Plotly HTML generation. Ensure JavaScript is enabled in your web browser.

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.


---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---
<div align="center">
  <b>Built with Python </b>
</div>
