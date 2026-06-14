# Feedback_Managment

-------------------------------------------------------------------
**The "existing_Project folder" app works without ai api need ( was made because sending 
a csv file with 1000 rows may take time to reply by the ai it may also lag , so i used 
this rule - based prototype )**

# Customer Feedback Intelligence Dashboard
## About the Project

Customer Feedback Intelligence Dashboard is a Streamlit-based analytics application that converts raw customer feedback into meaningful business insights.

The application automatically processes customer comments and performs:

* Data Cleaning
* Feedback Categorization
* Sentiment Analysis
* Priority Assignment
* Issue Summarization
* Interactive Dashboard Visualization

Users can upload a CSV file containing customer feedback and instantly view analytics through charts, KPIs, filters, and downloadable reports.

---

## Rule-Based Processing Workflow

The system uses rule-based logic to enrich customer feedback.

### 1. Data Cleaning

* Removes null and empty feedback.
* Removes extra spaces and unwanted characters.
* Normalizes text for analysis.

### 2. Category Detection

Feedback is classified into:

* Delivery
* Billing
* App Bug
* Staff/Support
* Other

Categories are assigned using predefined keywords.

Example:

* "late delivery" → Delivery
* "refund issue" → Billing
* "app crashed" → App Bug

### 3. Sentiment Analysis

Sentiment is determined using positive and negative keyword matching.

Output:

* Positive
* Neutral
* Negative

### 4. Priority Assignment

Priority is assigned based on issue severity.

Output:

* High
* Medium
* Low

Example:

* "payment failed" → High
* "app slow" → Medium
* "general feedback" → Low

### 5. Issue Summary Generation

A concise summary is generated from the cleaned feedback for easier review.

---

## Technologies Used

* Python
* Streamlit
* Pandas
* Plotly

---

## Running the Application

### Install Dependencies

```bash
pip install streamlit pandas plotly
```

### Start the Dashboard

```bash
python -m streamlit run dashboard/app.py
```

or

```bash
streamlit run dashboard/app.py
```

### Open in Browser

The application will automatically open at:

```text
http://localhost:8501
```

---

## Input

Upload a CSV file containing customer feedback.

Required column:

```text
feedback_text
```

---

## Output

The dashboard provides:

* KPI Metrics
* Category Distribution
* Sentiment Distribution
* Priority Distribution
* Feedback Records Table
* Downloadable Enriched CSV
* Summary Insights
