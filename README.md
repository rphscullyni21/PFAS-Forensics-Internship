# PFAS Forensics Internship - Flashcard Application

An interactive learning and training tool built with Python and Streamlit designed to help researchers and interns master PFAS (Per- and polyfluoroalkyl substances) chemical structures, analytical methods (like EPA Method 1633), and environmental forensics concepts.

## 🚀 Features

- **Interactive Flashcards**: Test your knowledge on chemical structures, compound shorthand names, and environmental toxicology.
- **EPA 1633 Integration**: Learn and reinforce criteria directly extracted from the EPA 1633 draft database.
- **Custom Styling**: Clean, modern interface designed specifically for clear visual learning.

## 📁 Repository Structure

```text
flashcard/
├── .streamlit/            # Streamlit configuration settings
├── src/
│   ├── assets/            # Graphic assets and background images
│   ├── __init__.py        # Python package initialization
│   ├── constants.py       # Configuration and constant values
│   ├── data_loader.py     # Logic for parsing Excel/CSV databases
│   ├── main.py            # Primary application entry point
│   ├── style.css          # Custom interface styling
│   └── ui_helpers.py      # Reusable UI components
├── flashcards.csv         # Structured database of questions and answers
└── EPA_1633A_PFAS_Learning_Database_v1.xlsx # Reference dataset
```

## 🛠️ Installation & Setup

To run this application locally on your machine, follow these steps:

### 1. Navigate to the Flashcard Directory
Open your terminal and ensure you are in the application subdirectory:
```bash
cd flashcard
```

### 2. Activate Your Virtual Environment
Activate your existing local `.venv` environment:
* **Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
* **Mac/Linux:**
  ```bash
  source .venv/bin/activate
  ```

### 3. Install Dependencies
If you have a `requirements.txt` file, install them via pip. Otherwise, make sure `streamlit`, `pandas`, and `openpyxl` (for Excel files) are installed:
```bash
pip install streamlit pandas openpyxl
```

### 4. Run the Application
Launch the Streamlit server directly from your local terminal:
```bash
streamlit run main.py
```

## 📊 Data Sources

- **EPA Method 1633**: Focuses on the analysis of target PFAS compounds in wastewater, surface water, groundwater, soil, biosolids, sediment, landfill leachate, and tissue samples.
