# ReqIF to PDF Exporter

## 📄 Overview

This project provides a **Python 3 tool** to convert **ReqIF (Requirements Interchange Format)** files into a **formatted PDF document**.

The generated PDF preserves:

- Requirement hierarchy
- Simplified requirement IDs (e.g. `[REQ-000123]`)
- Hierarchical numbering (e.g. `1.2.3`)
- Embedded images
- Clickable links to OLE objects
- Automatic clickable table of contents
- Cross-references between requirements

---

## 🖥 System Requirements

- Windows 10 / 11 (recommended)
- Python **3.8 or newer**
- pip (Python package installer)
- PDF viewer with link support (Adobe Reader, Edge, Chrome)

---

## 📦 Python Dependencies

This project depends on the following external Python library:

### ReportLab (PDF generation)

**Installation command:**

```bash
pip install reportlab


## 📁 Expected Folder Structure

The script assumes a typical ReqIF export layout:

```text
project_folder/
├─ requirements.reqif
├─ image_001.png
├─ diagram.png
├─ object_123.ole
├─ object_456.ole
├─ export_reqif_pdf.py
