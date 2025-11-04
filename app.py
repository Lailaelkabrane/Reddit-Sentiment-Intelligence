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
# Load External CSS
# =====================
def load_css(file_name):
    """Load CSS from external file"""
    try:
        with open(file_name, 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file {file_name} not found. Using default styling.")

# Load the professional styling
load_css('style.css')

# =====================
# Additional Custom Components
# =====================
def render_header():
    pass

def render_status_indicator(status_type, message):
    """Render professional status indicators"""
    icon_map = {
        'success': '✅',
        'warning': '⚠️',
        'error': '❌',
        'info': 'ℹ️'
    }
    
    st.markdown(f"""
    <div class="st{status_type.title()} fade-in" style="
        display: flex; 
        align-items: center; 
        gap: 0.5rem;
        margin: 1rem 0;
    ">
        <span style="font-size: 1.2rem;">{icon_map.get(status_type, 'ℹ️')}</span>
        <span>{message}</span>
    </div>
    """, unsafe_allow_html=True)

def render_kpi_card(title, value, subtitle="", trend=None):
    """Render professional KPI cards"""
    trend_arrow = ""
    trend_color = ""
    if trend:
        if trend > 0:
            trend_arrow = "up"
            trend_color = "#4CAF50"
        elif trend < 0:
            trend_arrow = "down"
            trend_color = "#F44336"
        else:
            trend_arrow = "right"
            trend_color = "#FFC107"
    
    st.markdown(f"""
    <div style="
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        border-left: 4px solid #FF4500;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    ">
        <div style="color: #6C757D; font-size: 0.875rem; margin-bottom: 0.5rem;">
            {title}
        </div>
        <div style="
            font-size: 2rem; 
            font-weight: 700; 
            background: linear-gradient(135deg, #0079D3 0%, #24A0ED 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.25rem;
        ">
            {value}
        </div>
        {f'<div style="color: {trend_color}; font-size: 0.875rem;">{trend_arrow} {subtitle}</div>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)

def render_post_card(post_data):
    """Render professional post cards"""
    sentiment_colors = {
        'Positive': '#4CAF50',
        'Negative': '#F44336',
        'Neutral': '#FFC107'
    }
    
    sentiment = post_data.get('Sentiment', 'Neutral')
    sentiment_color = sentiment_colors.get(sentiment, '#FFC107')
    
    st.markdown(f"""
    <div class="post-card">
        <div class="post-title">{post_data['title']}</div>
        <div class="post-meta">
            Comments: {post_data['num_comments']} • 
            Score: {post_data['score']} • 
            Date: {post_data['date']}
        </div>
        <div style="margin-top: 0.5rem;">
            <span style="
                background: {sentiment_color}20;
                color: {sentiment_color};
                padding: 0.25rem 0.75rem;
                border-radius: 16px;
                font-size: 0.875rem;
                font-weight: 600;
            ">
                {sentiment} Sentiment
            </span>
        </div>
    </div>
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
st.set_page_config(
    page_title="Reddit Sentiment Intelligence", 
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================
# Header
# =====================
render_header()

# =====================
# Sidebar: Controls
# =====================
with st.sidebar:
    st.markdown('<div class="slide-in-left">', unsafe_allow_html=True)
    st.title("Dashboard Controls")

    with st.expander("Data Source Configuration", expanded=True):
        mode = st.radio("Select Data Source:", ["Fetch Reddit Data", "Upload CSV File"])

        # Fetch Reddit Data
        if mode == "Fetch Reddit Data":
            keyword = st.text_input("Subreddit/Keyword", "python", 
                                   help="Enter subreddit name or search keyword")
            limit = st.slider("Posts to Fetch", 10, 1000, 100, step=10,
                            help="Number of posts to fetch from Reddit")

        # Upload CSV
        elif mode == "Upload CSV File":
            uploaded_file = st.file_uploader("Upload Your CSV File", type=["csv"],
                                           help="Upload a CSV file with Reddit post data")

    # Filters Section
    with st.expander("Advanced Filters"):
        st.markdown("**Date Range Filter**")
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_dates = st.date_input(
                "Select Date Range",
                st.session_state.temp_dates,
                key="date_range_picker",
                help="Filter posts by date range"
            )
            # Update temp dates when user selects new range
            if len(selected_dates) == 2:
                st.session_state.temp_dates = list(selected_dates)
        
        with col2:
            st.markdown('<div style="margin-top: 1.7rem;"></div>', unsafe_allow_html=True)
            st.button("Apply", on_click=apply_date_range, key="apply_date_range",
                     help="Apply the selected date range")
        
        st.markdown("**Content Quality Filter**")
        min_score = st.slider(
            "Minimum Post Score", 
            0, 100, 
            st.session_state.min_score, 
            key="min_score_slider",
            help="Filter posts by minimum upvote score",
            on_change=lambda: setattr(st.session_state, 'min_score', st.session_state.min_score_slider)
        )

    # Morocco Focus Section
    with st.expander("Morocco Focus Analytics"):
        st.markdown("**Track Moroccan-related discussions**")
        morocco_keywords = st.multiselect(
            "Moroccan Keywords to Track",
            options=MOROCCO_KEYWORDS,
            default=["Maroc", "Casablanca"],
            key="morocco_keywords",
            help="Select Moroccan terms to track in the analysis"
        )

    # Main Action Button
    st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
    if st.button("Fetch & Analyze Data", key="fetch_button", use_container_width=True):
        st.session_state.fetch_clicked = True
        
        # Validate inputs
        validation_errors = validate_inputs()
        
        if validation_errors:
            for error in validation_errors:
                render_status_indicator('error', error)
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
                            render_status_indicator('success', 
                                f"Successfully fetched {len(df)} posts from Reddit!")
                        else:
                            render_status_indicator('error', "Invalid data format received from Reddit")
                            st.session_state.data_ready = False
                
                elif mode == "Upload CSV File" and uploaded_file:
                    df = pd.read_csv(uploaded_file)
                    if validate_reddit_data(df):
                        st.session_state.original_df = cached_processing(df)
                        st.session_state.raw_count = len(df)
                        st.session_state.current_keyword = "uploaded"
                        st.session_state.data_ready = True
                        render_status_indicator('success', 
                            f"CSV loaded successfully with {len(df)} posts!")
                    else:
                        render_status_indicator('error', 
                            "CSV missing required columns (needs 'sentiment_compound' column)")
                        st.session_state.data_ready = False
                else:
                    render_status_indicator('warning', "Please upload a CSV file first")
                    st.session_state.data_ready = False
                    
            except Exception as e:
                render_status_indicator('error', f"An error occurred: {str(e)}")
                st.session_state.data_ready = False

    st.markdown('</div>', unsafe_allow_html=True)

# =====================
# Main Dashboard Content
# =====================
if st.session_state.fetch_clicked and st.session_state.data_ready and st.session_state.original_df is not None:
    # Apply filters
    filtered_df = st.session_state.original_df[
        (st.session_state.original_df['date'] >= st.session_state.applied_dates[0]) &
        (st.session_state.original_df['date'] <= st.session_state.applied_dates[1]) &
        (st.session_state.original_df['score'] >= st.session_state.min_score)
    ].copy()

    # Show filter status with professional styling
    st.markdown(f"""
    <div class="fade-in" style="margin-bottom: 2rem;">
        <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;">
            <span class="filter-chip">Date: {st.session_state.applied_dates[0]} to {st.session_state.applied_dates[1]}</span>
            <span class="filter-chip">Score ≥ {st.session_state.min_score}</span>
            <span class="filter-chip">Showing {len(filtered_df):,} of {st.session_state.raw_count:,} posts</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if filtered_df.empty:
        render_status_indicator('warning', 
            "No posts match the selected filters. Please adjust the date range or score threshold.")
    else:
        # KPI Section with Professional Cards
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.subheader("Key Performance Indicators")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            render_kpi_card("Total Posts", f"{len(filtered_df):,}", "Posts analyzed")
        
        with col2:
            if "Sentiment" in filtered_df.columns:
                positive_pct = (filtered_df['Sentiment'] == 'Positive').mean() * 100
                render_kpi_card("Positive Sentiment", f"{positive_pct:.1f}%", "of all posts")
            else:
                render_kpi_card("Positive Sentiment", "N/A", "No sentiment data")
        
        with col3:
            if "Sentiment" in filtered_df.columns:
                negative_pct = (filtered_df['Sentiment'] == 'Negative').mean() * 100
                render_kpi_card("Negative Sentiment", f"{negative_pct:.1f}%", "of all posts")
            else:
                render_kpi_card("Negative Sentiment", "N/A", "No sentiment data")
        
        with col4:
            avg_score = filtered_df['score'].mean()
            render_kpi_card("Avg. Post Score", f"{avg_score:.1f}", "Reddit upvotes")
        
        st.markdown('</div>', unsafe_allow_html=True)

        # Only show tabs if we have sufficient data
        if len(filtered_df) > 1:
            st.markdown('<div style="margin-top: 3rem;"></div>', unsafe_allow_html=True)
            tabs = st.tabs([
                "Sentiment Overview", 
                "Trend Analysis", 
                "Top Performing Posts", 
                "Morocco Analytics", 
                "Industry Insights"
            ])
            
            try:
                # Overview Tab
                with tabs[0]:
                    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                    st.subheader("Sentiment Distribution Analysis")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if "Sentiment" in filtered_df.columns:
                            sentiment_counts = filtered_df["Sentiment"].value_counts().reset_index()
                            chart = alt.Chart(sentiment_counts).mark_bar(
                                cornerRadiusTopLeft=8,
                                cornerRadiusTopRight=8
                            ).encode(
                                x=alt.X("Sentiment", sort=["Positive", "Neutral", "Negative"]),
                                y=alt.Y("count", title="Number of Posts"),
                                color=alt.Color("Sentiment", 
                                    scale=alt.Scale(
                                        domain=["Positive", "Neutral", "Negative"],
                                        range=["#4CAF50", "#FFC107", "#F44336"]
                                    ),
                                    legend=None
                                ),
                                tooltip=["Sentiment", "count"]
                            ).properties(
                                title="Sentiment Distribution",
                                width=300,
                                height=300
                            )
                            st.altair_chart(chart, use_container_width=True)
                    
                    with col2:
                        if "sentiment_compound" in filtered_df.columns:
                            # Create sentiment score histogram
                            hist_chart = alt.Chart(filtered_df).mark_bar(
                                cornerRadiusTopLeft=4,
                                cornerRadiusTopRight=4
                            ).encode(
                                alt.X("sentiment_compound:Q", bin=alt.Bin(maxbins=20), title="Sentiment Score"),
                                y=alt.Y("count()", title="Frequency"),
                                color=alt.value("#0079D3"),
                                tooltip=["count()"]
                            ).properties(
                                title="Sentiment Score Distribution",
                                width=300,
                                height=300
                            )
                            st.altair_chart(hist_chart, use_container_width=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

                # Trends Tab
                with tabs[1]:
                    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                    st.subheader("Sentiment Trends Over Time")
                    
                    if "sentiment_compound" in filtered_df.columns:
                        # Daily sentiment trends
                        daily_sentiment = filtered_df.groupby("date").agg({
                            'sentiment_compound': ['mean', 'count']
                        }).round(3)
                        daily_sentiment.columns = ['avg_sentiment', 'post_count']
                        daily_sentiment = daily_sentiment.reset_index()
                        
                        # Line chart for sentiment trend
                        line_chart = alt.Chart(daily_sentiment).mark_line(
                            point=alt.OverlayMarkDef(size=60, filled=True),
                            strokeWidth=3
                        ).encode(
                            x=alt.X("date:T", title="Date"),
                            y=alt.Y("avg_sentiment:Q", title="Average Sentiment Score"),
                            color=alt.value("#FF4500"),
                            tooltip=["date:T", "avg_sentiment:Q", "post_count:Q"]
                        ).properties(
                            title="Daily Average Sentiment Trend",
                            height=400
                        )
                        
                        st.altair_chart(line_chart, use_container_width=True)
                        
                        # Volume chart
                        volume_chart = alt.Chart(daily_sentiment).mark_bar(
                            cornerRadiusTopLeft=4,
                            cornerRadiusTopRight=4
                        ).encode(
                            x=alt.X("date:T", title="Date"),
                            y=alt.Y("post_count:Q", title="Number of Posts"),
                            color=alt.value("#0079D3"),
                            tooltip=["date:T", "post_count:Q"]
                        ).properties(
                            title="Daily Post Volume",
                            height=200
                        )
                        
                        st.altair_chart(volume_chart, use_container_width=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

                # Top Posts Tab
                with tabs[2]:
                    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                    st.subheader("Top Performing Posts")
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        sort_options = {
                            "Highest Score": "score",
                            "Most Comments": "num_comments", 
                            "Most Recent": "date",
                            "Most Positive": "sentiment_compound"
                        }
                        sort_by = st.selectbox("Sort posts by:", list(sort_options.keys()))
                    
                    with col2:
                        show_count = st.slider("Posts to show:", 5, 20, 10)
                    
                    sort_column = sort_options[sort_by]
                    ascending = sort_column == "date" if sort_by == "Most Recent" else False
                    
                    top_posts = filtered_df.sort_values(sort_column, ascending=ascending).head(show_count)
                    
                    st.markdown('<div style="margin-top: 1.5rem;"></div>', unsafe_allow_html=True)
                    for idx, (_, row) in enumerate(top_posts.iterrows(), 1):
                        with st.container():
                            render_post_card(row.to_dict())
                    
                    st.markdown('</div>', unsafe_allow_html=True)

                # Morocco Tab
                with tabs[3]:
                    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                    render_morocco_analysis(
                        df=filtered_df,
                        keywords=morocco_keywords,
                        search_term=st.session_state.current_keyword
                    )
                    st.markdown('</div>', unsafe_allow_html=True)

                # Industry Tab
                with tabs[4]:
                    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                    render_industry_analysis(
                        df=filtered_df,
                        search_term=st.session_state.current_keyword
                    )
                    st.markdown('</div>', unsafe_allow_html=True)

                # Export Section
                st.subheader("Export Data & Generate Reports")
                st.markdown("Download your analysis in multiple formats for further processing or sharing.")
                
                col1, col2, col3 = st.columns(3)

                # CSV Export
                with col1:
                    csv = filtered_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="Download CSV Data",
                        data=csv,
                        file_name=f"reddit_sentiment_{datetime.date.today()}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        help="Download raw data as CSV file"
                    )

                # PDF Report
                with col2:
                    try:
                        pdf_bytes = EnhancedPDFGenerator(
                            df=filtered_df,
                            search_term=st.session_state.current_keyword
                        ).generate_pdf()
                        st.download_button(
                            label="Generate PDF Report",
                            data=pdf_bytes,
                            file_name=f"Reddit_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            help="Generate comprehensive PDF report"
                        )
                    except Exception as e:
                        st.error(f"PDF generation error: {str(e)}")

                # JSON Export
                with col3:
                    try:
                        json_data = EnhancedPDFGenerator(
                            df=filtered_df,
                            search_term=st.session_state.current_keyword
                        ).generate_json()
                        st.download_button(
                            label="Download JSON Data",
                            data=json.dumps(json_data, indent=2, default=str),
                            file_name=f"Reddit_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json",
                            mime="application/json",
                            use_container_width=True,
                            help="Download structured data as JSON"
                        )
                    except Exception as e:
                        st.error(f"JSON generation error: {str(e)}")
                
                st.markdown('</div>', unsafe_allow_html=True)
                
            except Exception as e:
                render_status_indicator('error', f"Error displaying analysis: {str(e)}")
        else:
            render_status_indicator('warning', 
                "Not enough posts to display detailed analysis. Need at least 2 posts for comprehensive insights.")
else:
    # Welcome screen when no data is loaded
    st.markdown("""
    <div class="fade-in" style="text-align: center; margin-top: 4rem;">
        <div style="
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            margin: 2rem 0;
        ">
            <h2 style="color: #212529; margin-bottom: 1rem;">Welcome to Reddit Sentiment Intelligence</h2>
            <p style="color: #6c757d; font-size: 1.1rem; margin-bottom: 2rem; max-width: 600px; margin-left: auto; margin-right: auto;">
                Get started by configuring your data source in the sidebar. 
                Choose to fetch live Reddit data or upload your own CSV file for analysis.
            </p>
            <div style="
                background: linear-gradient(135deg, #0079D3 0%, #24A0ED 100%);
                color: white;
                padding: 1rem 2rem;
                border-radius: 12px;
                display: inline-block;
                font-weight: 600;
            ">
                Start by clicking "Fetch & Analyze Data" in the sidebar
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)