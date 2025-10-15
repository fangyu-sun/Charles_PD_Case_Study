# Painted Dog Case Study 

## Overview
This repository contains the full Painted Dog Case Study completed by **Charles Sun**, demonstrating end-to-end data processing — from raw survey data cleaning in Python to visualization dashboards in Tableau.

---

## Task 1 – Data Cleaning & Formatting
   **Objective:** Clean and format raw survey data for SPSS/Q import.

   **Key Steps**
      - Removed invalid or inconsistent responses (e.g., under-18 respondents, skip-logic violations).  
      - Processed multi-response questions using one-hot encoding.  
      - Converted text labels to numeric codes according to the QNA codeframe.  
      - Generated a weekly “Wave” variable based on completion date.  
      - Applied variable and value labels for SPSS export using `pyreadstat`.  
      - Automated file-path detection for cross-system compatibility.
   
   **Deliverables**
      - `Task1/Task1.py` – Python cleaning script  
      - `Task1/cleaned_data.sav` – SPSS-ready dataset  
      - `Task1/cleaned_data_check.xlsx` – QA file for verification  

---

## Task 2 – Data Visualization
    **Objective:** Develop interactive dashboards visualizing brand awareness and perception trends.
    
    **Platform:** Tableau Desktop 2024.2  
    
    **Visualisations**
        - **Page 1 – Brand Awareness & Usage:
            ** Bar charts (Q1, Q2)  
        - **Page 2 – Brand Perceptions:
            ** Donut chart (Q3 NET Favourable) and stacked columns (Q4a Likelihood to Recommend)  
        - **Page 3 – Brand Values Over Time:
            ** Line chart (Q5 % NET Good (4–5) by Wave)  
    
    **Deliverables**
        - `Task2/dashboard.twbx` – Final Tableau dashboard  
        - `Task2/processed_data.csv` – Data used for visualisation (exported from *.sav file) 
    
    ---
    
    ## Tools & Technologies
        - **Python:** pandas, numpy, pyreadstat  
        - **Visualization:** Tableau Desktop  
        - **Version Control:** Git & GitHub  

---

## Repository Structure
          Charles_PD_Case_Study/
        ├── EXAMPLE DATA FILE.xlsx
        ├── TASK INSTRUCTIONS.docx
        ├── EXAMPLE QNA.docx
        ├── Task1/
        │ ├── Task1.py
        │ ├── cleaned_data.sav
        │ ├── cleaned_data_check.xlsx
        ├── Task2/
        │ ├── Task2 Data visualisation.twbx
        │ ├── processed_data.csv
        └── README.md
<img width="451" height="700" alt="image" src="https://github.com/user-attachments/assets/12db40d1-ca47-4366-9aae-a889fdb9f582" />
