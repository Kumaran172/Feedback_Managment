( Built this after the rule based model because to bring a new feature like integrating AI using api i used gemini api-2.5 flash , 
  which can provide the summary and solution on a specific feedback we want ).

# Customer Feedback Intelligence System

A Streamlit-based application for cleaning, analyzing, and exploring customer feedback data.

## Features

* Upload raw customer feedback CSV files
* Remove duplicates, empty, and meaningless records
* Standardize timestamps and validate data quality
* Download cleaned datasets
* Interactive dashboards and visual analytics
* AI-powered feedback explanation and resolution suggestions using Google Gemini API
* On-demand AI analysis to reduce API usage and improve performance

## Technologies

* Python
* Streamlit
* Pandas
* Plotly
* Google Gemini API

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open: `http://localhost:8501`

## AI Integration

The application uses Gemini API only when the user clicks **Explain Feedback** or **Suggest Resolution** for a specific feedback entry. This avoids unnecessary API calls and provides fast, targeted insights.
