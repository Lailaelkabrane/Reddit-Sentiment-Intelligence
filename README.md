# Reddit Sentiment Intelligence Platform

## Project Overview

The Reddit Sentiment Intelligence Platform is an interactive platform for analyzing public discussions on Reddit. It combines real-time data fetching, natural language processing, and visual analytics to deliver insights into community opinions and trends.

## Key Features

- Fetch Reddit posts by keyword or subreddit in real-time
- Upload and analyze custom CSV datasets
- Automatic sentiment classification (**Positive**, **Neutral**, **Negative**)
- Interactive dashboards with filters for date range and minimum score
- Trends over time visualization of sentiment scores
- Top posts ranking with customizable sorting (score, comments, date)
- Morocco-specific keyword tracking
- Industry sentiment analysis across key sectors
- User-friendly visualizations
- Export reports in multiple formats: CSV, JSON, and styled PDF



## Technical Implementation

- **Backend / Data Processing:** Python, Pandas, NLTK/VADER, TextBlob  
- **Reddit API Access:** PRAW  
- **Frontend / Visualization:** Streamlit, Altair  
- **Report Generation:** FPDF (PDF export)  
- Data is processed in-memory using Pandas DataFrames for real-time analysis.  
- Dashboards are interactive and allow users to filter and explore data dynamically.  



## Usage

1. Install dependencies:

```bash
pip install praw pandas nltk textblob streamlit altair fpdf
