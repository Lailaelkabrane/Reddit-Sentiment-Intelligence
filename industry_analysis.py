import streamlit as st
import re
import pandas as pd
import altair as alt
from collections import Counter

GLOBAL_INDUSTRIES = {
    "Real Estate": ["house", "property", "rent", "buy", "lease", "real estate", "immobilier"],
    "Tech": ["AI", "software", "app", "code", "programming", "algorithm"],
    "Finance": ["bank", "loan", "invest", "stock", "crypto", "money"],
    "Education": ["school", "university", "learn", "student", "course"],
    "Healthcare": ["hospital", "doctor", "medicine", "health", "patient"],
    "Tourism": ["hotel", "travel", "visit", "tour", "vacation"]
}

def analyze_industries(df, search_term=None):
    """Analyze which industries are discussing the searched term"""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    
    industry_results = []
    for industry, terms in GLOBAL_INDUSTRIES.items():
        # Count posts mentioning both search term AND industry terms
        industry_posts = df[
            df["title"].str.contains("|".join(terms), case=False, na=False)
        ]
        
        if search_term:
            industry_posts = industry_posts[
                industry_posts["title"].str.contains(search_term, case=False, na=False)
            ]
        
        if not industry_posts.empty:
            industry_results.append({
                "Industry": industry,
                "Posts": len(industry_posts),
                "Avg Sentiment": industry_posts["sentiment_compound"].mean()
            })
    
    return pd.DataFrame(industry_results)

def render_industry_analysis(df, search_term=None):
    """Visualize industry relevance to the search term"""
    industry_df = analyze_industries(df, search_term)
    
    if industry_df is None or industry_df.empty:
        st.warning("No industry patterns detected. Try a more common term.")
        return
    
    st.subheader("🔍 Industry Relevance")
    
    # Top industries chart
    st.altair_chart(alt.Chart(industry_df).mark_bar().encode(
        x=alt.X('Posts:Q', title='Number of Posts'),
        y=alt.Y('Industry:N', sort='-x', title=''),
        color=alt.Color('Avg Sentiment:Q', scale=alt.Scale(scheme='redyellowgreen', domainMid=0)),
        tooltip=['Industry', 'Posts', 'Avg Sentiment']
    ), use_container_width=True)
    
def get_top_keywords(posts, n=5):
    """Extract most frequent keywords (fallback without sklearn)"""
    words = []
    for post in posts:
        if isinstance(post, str):
            words.extend([word.lower() for word in re.findall(r'\w+', post) if len(word) > 3])
    return [word for word, count in Counter(words).most_common(n)]