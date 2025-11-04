import streamlit as st
import pandas as pd
import altair as alt
import json
import datetime
from io import BytesIO
from reddit_fetch import fetch_posts_safely, process_reddit_data, validate_reddit_data
from morocco_analysis import (
    MOROCCO_KEYWORDS,
    highlight_moroccan,
    render_morocco_analysis
)
from industry_analysis import render_industry_analysis
from report_generator import EnhancedPDFGenerator

# =====================
# Custom CSS
# =====================
st.markdown("""
    <style>
    [data-testid="stSidebar"] {background-color: #f7f9fc; padding: 1rem;}
    [data-testid="stExpander"] {background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    [data-testid="stExpander"] summary {font-weight: 600; font-size: 15px; color: #1f4e79;}
    .stButton button {width: 100%; border-radius: 8px; background-color: #1f4e79; color: white; font-weight: 500; transition: 0.3s;}
    .stButton button:hover {background-color: #163a5d;}
    .stSlider, .stTextInput, .stSelectbox, .stMultiSelect {font-size: 14px;}
    .filter-chip {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        background-color: #e0e0e0;
        border-radius: 1rem;
        font-size: 0.875rem;
    }
    </style>
""", unsafe_allow_html=True)

# =====================
# Session State Initialization
# =====================
if 'original_df' not in st.session_state:
    st.session_state.original_df = None
if 'raw_count' not in st.session_state:
    st.session_state.raw_count = 0
if 'temp_dates' not in st.session_state:
    st.session_state.temp_dates = [datetime.date(2018, 3, 14), datetime.date.today()]
if 'applied_dates' not in st.session_state:
    st.session_state.applied_dates = [datetime.date(2018, 3, 14), datetime.date.today()]
if 'min_score' not in st.session_state:
    st.session_state.min_score = 0
if 'current_keyword' not in st.session_state:
    st.session_state.current_keyword = ""
if 'fetch_clicked' not in st.session_state:
    st.session_state.fetch_clicked = False
if 'data_ready' not in st.session_state:
    st.session_state.data_ready = False

# =====================
# Functions
# =====================
def classify_sentiment(compound_score):
    if compound_score >= 0.05:
        return "Positive"
    elif compound_score <= -0.05:
        return "Negative"
    else:
        return "Neutral"

@st.cache_data
def cached_processing(df: pd.DataFrame) -> pd.DataFrame:
    processed_df = process_reddit_data(df)
    if 'sentiment_compound' in processed_df.columns:
        processed_df["Sentiment"] = processed_df["sentiment_compound"].apply(classify_sentiment)
    return processed_df

def validate_inputs():
    """Validate all user inputs before processing"""
    errors = []
    
    # Check date range
    if st.session_state.temp_dates[0] > st.session_state.temp_dates[1]:
        errors.append("Start date must be before end date")
    
    return errors

def apply_date_range():
    """Apply the selected date range"""
    st.session_state.applied_dates = st.session_state.temp_dates.copy()
    st.session_state.date_range_applied = True

# =====================
# Streamlit Config
# =====================
st.set_page_config(page_title="Reddit Sentiment Dashboard", layout="wide")

# =====================
# Sidebar: Controls
# =====================
st.sidebar.title("⚙️ Controls")

with st.sidebar.expander("📂 Data Source", expanded=True):
    mode = st.radio("Mode:", ["Fetch Reddit Data", "Upload CSV"])

    # Fetch Reddit Data
    if mode == "Fetch Reddit Data":
        keyword = st.text_input("🔎 Subreddit/Keyword", "learnpython")
        limit = st.slider("Posts to fetch", 10, 1000, 20)

    # Upload CSV
    elif mode == "Upload CSV":
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

# Filters
with st.sidebar.expander("🔧 Filters"):
    # Date range with apply button
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_dates = st.date_input(
            "📅 Select date range",
            st.session_state.temp_dates,
            key="date_range_picker"
        )
        # Update temp dates when user selects new range
        if len(selected_dates) == 2:
            st.session_state.temp_dates = list(selected_dates)
    
    with col2:
        st.write("")  # Spacer
        st.button("✅ Apply", on_click=apply_date_range, key="apply_date_range")
    
    # Real-time score filter
    min_score = st.slider(
        "⬆️ Minimum Score", 
        0, 100, 
        st.session_state.min_score, 
        key="min_score_slider",
        on_change=lambda: setattr(st.session_state, 'min_score', st.session_state.min_score_slider)
    )

# Morocco Focus
with st.sidebar.expander("🌍 Morocco Focus"):
    morocco_keywords = st.multiselect(
        "Track Moroccan Terms",
        options=MOROCCO_KEYWORDS,
        default=["Maroc", "Casablanca"],
        key="morocco_keywords"
    )

# Main action button
if st.sidebar.button("🚀 Fetch & Analyze", key="fetch_button"):
    st.session_state.fetch_clicked = True
    
    # Validate inputs
    validation_errors = validate_inputs()
    
    if validation_errors:
        for error in validation_errors:
            st.sidebar.error(error)
        st.session_state.data_ready = False
    else:
        # Process data based on mode
        try:
            if mode == "Fetch Reddit Data":
                with st.spinner("Fetching Reddit posts..."):
                    df = fetch_posts_safely(keyword, limit)
                    if validate_reddit_data(df):
                        st.session_state.original_df = cached_processing(df)
                        st.session_state.raw_count = len(df)
                        st.session_state.current_keyword = keyword
                        st.session_state.data_ready = True
                        st.sidebar.success(f"""
                        Fetched {len(df)} posts total!
                        {len(df)} posts available before filtering
                        """)
                    else:
                        st.sidebar.error("Invalid data format received from Reddit")
                        st.session_state.data_ready = False
            
            elif mode == "Upload CSV" and uploaded_file:
                df = pd.read_csv(uploaded_file)
                if validate_reddit_data(df):
                    st.session_state.original_df = cached_processing(df)
                    st.session_state.raw_count = len(df)
                    st.session_state.current_keyword = "uploaded"
                    st.session_state.data_ready = True
                    st.sidebar.success(f"""
                    CSV loaded with {len(df)} posts!
                    {len(df)} posts available before filtering
                    """)
                else:
                    st.sidebar.error("CSV missing required columns (needs 'sentiment_compound' column)")
                    st.session_state.data_ready = False
            else:
                st.sidebar.warning("Please upload a CSV file first")
                st.session_state.data_ready = False
                
        except Exception as e:
            st.sidebar.error(f"An error occurred: {str(e)}")
            st.session_state.data_ready = False

# =====================
# Main Dashboard
# =====================
if st.session_state.fetch_clicked and st.session_state.data_ready and st.session_state.original_df is not None:
    # Apply filters
    filtered_df = st.session_state.original_df[
        (st.session_state.original_df['date'] >= st.session_state.applied_dates[0]) &
        (st.session_state.original_df['date'] <= st.session_state.applied_dates[1]) &
        (st.session_state.original_df['score'] >= st.session_state.min_score)
    ].copy()

    # Show filter status
    st.markdown(f"""
    <div style="margin-bottom: 1rem;">
        <span class="filter-chip">📅 {st.session_state.applied_dates[0]} to {st.session_state.applied_dates[1]}</span>
        <span class="filter-chip">⬆️ Score ≥ {st.session_state.min_score}</span>
        <span class="filter-chip">📊 Showing {len(filtered_df)} of {st.session_state.raw_count} posts</span>
    </div>
    """, unsafe_allow_html=True)

    if filtered_df.empty:
        st.warning("No posts match the selected filters. Please adjust the date range or score.")
    else:
        # KPIs
        st.subheader("📌 Key Insights")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Posts", len(filtered_df))
        if "Sentiment" in filtered_df.columns:
            positive_pct = (filtered_df['Sentiment']=='Positive').mean()*100
            negative_pct = (filtered_df['Sentiment']=='Negative').mean()*100
            col2.metric("Positive %", f"{positive_pct:.1f}%")
            col3.metric("Negative %", f"{negative_pct:.1f}%")
        else:
            col2.metric("Positive %", "N/A")
            col3.metric("Negative %", "N/A")

        # Only show tabs if we have sufficient data
        if len(filtered_df) > 1:
            tabs = st.tabs(["📊 Overview", "📈 Trends", "🔥 Top Posts", "🌍 Morocco", "🏭 Industry"])
            
            try:
                # Overview Tab
                with tabs[0]:
                    st.subheader("Sentiment Overview")
                    col1, col2 = st.columns(2)
                    if "Sentiment" in filtered_df.columns:
                        sentiment_counts = filtered_df["Sentiment"].value_counts().reset_index()
                        col1.altair_chart(
                            alt.Chart(sentiment_counts).mark_bar().encode(
                                x="Sentiment",
                                y="count",
                                color=alt.Color("Sentiment", scale=alt.Scale(
                                    domain=["Positive","Neutral","Negative"],
                                    range=["#4CAF50","#FFC107","#F44336"]
                                ))
                            ).properties(title="Sentiment Distribution"),
                            use_container_width=True
                        )
                    if "sentiment_compound" in filtered_df.columns:
                        sentiment_avg = filtered_df.groupby("Sentiment")["sentiment_compound"].mean().reset_index()
                        col2.altair_chart(
                            alt.Chart(sentiment_avg).mark_arc(innerRadius=50).encode(
                                theta="sentiment_compound",
                                color="Sentiment",
                                tooltip=["Sentiment","sentiment_compound"]
                            ).properties(title="Avg Sentiment Score (Pie)"),
                            use_container_width=True
                        )

                # Trends Tab
                with tabs[1]:
                    st.subheader("Trends Over Time")
                    if "sentiment_compound" in filtered_df.columns:
                        daily_avg = filtered_df.groupby("date")["sentiment_compound"].mean().reset_index()
                        st.altair_chart(
                            alt.Chart(daily_avg).mark_line(point=True).encode(
                                x="date:T",
                                y="sentiment_compound",
                                tooltip=["date","sentiment_compound"]
                            ).properties(title="Daily Average Sentiment"),
                            use_container_width=True
                        )

                # Top Posts Tab
                with tabs[2]:
                    st.subheader("🔥 Top Posts")
                    sort_by = st.selectbox("Sort posts by:", ["score","num_comments","date"])
                    top_posts = filtered_df.sort_values(sort_by, ascending=False).head(10)
                    for _, row in top_posts.iterrows():
                        st.markdown(f"""
                        <div style="background:#ffffff;padding:12px;margin-bottom:10px;border-radius:10px;
                        box-shadow:0 2px 5px rgba(0,0,0,0.1)">
                            <b style="color:#1f4e79">{row['title']}</b><br>
                            <span style="color:gray">💬 {row['num_comments']} comments | ⬆️ {row['score']} | 🗓 {row['date']}</span><br>
                            Sentiment: <b style="color:{'#4CAF50' if row['Sentiment']=='Positive' else '#F44336' if row['Sentiment']=='Negative' else '#FFC107'}">{row['Sentiment']}</b>
                        </div>
                        """, unsafe_allow_html=True)

                # Morocco Tab
                with tabs[3]:
                    render_morocco_analysis(
                        df=filtered_df,
                        keywords=morocco_keywords,
                        search_term=st.session_state.current_keyword
                    )

                # Industry Tab
                with tabs[4]:
                    render_industry_analysis(
                        df=filtered_df,
                        search_term=st.session_state.current_keyword
                    )

                # Export
                st.markdown("---")
                with st.expander("📥 Export Data & Reports"):
                    col1, col2, col3 = st.columns(3)

                    # CSV
                    csv = filtered_df.to_csv(index=False).encode("utf-8")
                    with col1:
                        st.download_button(
                            "⬇️ CSV",
                            data=csv,
                            file_name=f"reddit_sentiment_{datetime.date.today()}.csv",
                            mime="text/csv"
                        )

                    # PDF
                    with col2:
                        pdf_bytes = EnhancedPDFGenerator(
                            df=filtered_df,
                            search_term=st.session_state.current_keyword
                        ).generate_pdf()
                        st.download_button(
                            "📄 PDF",
                            data=pdf_bytes,
                            file_name=f"Reddit_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf"
                        )

                    # JSON
                    with col3:
                        st.download_button(
                            "📊 JSON",
                            data=json.dumps(
                                EnhancedPDFGenerator(
                                    df=filtered_df,
                                    search_term=st.session_state.current_keyword
                                ).generate_json(),
                                indent=2,
                                default=str
                            ),
                            file_name=f"Reddit_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json",
                            mime="application/json"
                        )
                
            except Exception as e:
                st.error(f"Error displaying analysis: {str(e)}")
        else:
            st.warning("Not enough posts to display detailed analysis (need at least 2 posts)")
else:
    st.info("Please configure your settings and click 'Fetch & Analyze' to begin")