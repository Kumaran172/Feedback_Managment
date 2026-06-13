# Customer Feedback Intelligence Dashboard

## Overview

Customer Feedback Intelligence Dashboard is a Streamlit-based application that transforms raw customer feedback data into actionable business insights.

The system automatically cleans customer comments, categorizes issues, analyzes sentiment, assigns priorities, generates summaries, and displays results through an interactive dashboard.

---

## Features

- CSV Upload
- Automated Data Cleaning
- Sentiment Analysis
- Issue Categorization
- Priority Detection
- Issue Summarization
- Interactive Dashboard
- KPI Metrics
- Export Processed Data

---

## Tech Stack

Frontend:
- Streamlit

Data Processing:
- Pandas

Visualization:
- Plotly

Programming Language:
- Python

---

## Project Structure

project/
│
├── dashboard/
│   └── app.py
│
├── notebooks/
│   └── QuickCart_POC.ipynb
│
├── output/
│
└── README.md

---

## Installation

Install required packages:

pip install streamlit pandas plotly

---

## Running the Application

Navigate to the project root folder:

cd project

Run Streamlit:

python -m streamlit run dashboard/app.py

or

streamlit run dashboard/app.py

---

## Input File Format

The uploaded CSV should contain a customer feedback column.

Example:

id,timestamp,feedback_text
1,2025-01-01,"Delivery was delayed by two days"
2,2025-01-02,"Payment failed but money was deducted"

---

## Processing Steps

1. Load Raw CSV
2. Validate Feedback Records
3. Clean Text
4. Remove Invalid Entries
5. Categorize Feedback
6. Detect Sentiment
7. Assign Priority
8. Generate Issue Summary
9. Create Dashboard Visualizations

---

## Dashboard Outputs

### KPI Cards
- Total Feedback
- Categories
- Negative Sentiment Count
- High Priority Issues

### Charts
- Category Distribution
- Sentiment Distribution
- Priority Distribution

### Insights
- Most Common Category
- High Priority Issues
- Sentiment Trends

### Data Table
- Clean Feedback
- Category
- Sentiment
- Priority
- Issue Summary

---

## Export

Users can download the enriched dataset as a CSV file directly from the dashboard.

---

## Future Enhancements

- AI-generated issue summaries
- AI-generated recommendations
- Real-time feedback monitoring
- Trend analysis
- Database integration
- API integration
- User authentication

---

## Author

Kumaran M S
BE Computer Science and Engineering