import streamlit as st
import re
import pandas as pd
import altair as alt
from collections import Counter

# Try to import scikit-learn, fallback to pure Python
try:
    from sklearn.feature_extraction.text import CountVectorizer
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# Moroccan keywords and industries data
MOROCCO_KEYWORDS = [
    "Morocco", "Maroc", "المغرب", "Casablanca", "Rabat", 
    "Tanger", "OCP", "Attijariwafa", "Darija", "touris",
    "visit", "immobili", "property", "house", "شقة"
]

MOROCCO_INDUSTRIES = {
    "Banking": ["attijariwafa", "bank", "bancaire", "البنك"],
    "Tech": ["AI", "technologie", "informatique", "الذكاء"],
    "Education": ["PFE", "stage", "université", "جامعة"],
    "Real Estate": ["house", "riad", "immobilier", "property", "شقة", "سكن"]
}

def highlight_moroccan(text, keywords):
    """Highlight Moroccan keywords in text."""
    if not isinstance(text, str):
        return text
        
    for word in keywords:
        if word.lower() in text.lower():
            return f"<span style='background-color: #FFD700'>{text}</span>"
    return text

def get_top_keywords(posts, n=10):
    """Fallback keyword extraction without scikit-learn"""
    STOP_WORDS = {
        'the', 'and', 'of', 'to', 'in', 'is', 'it', 'that', 'this',
        'ال', 'في', 'من', 'على', 'أن', 'هذا'
    }
    
    words = []
    for post in posts:
        if not isinstance(post, str):
            continue
        clean_text = re.sub(r'[^\w\s]', '', post.lower())
        words.extend([word for word in clean_text.split() 
                     if word not in STOP_WORDS and len(word) > 2])
    
    return [word for word, count in Counter(words).most_common(n)]

def get_morocco_metrics(df, keywords, search_term=None):
    """Robust metric calculation with fallbacks"""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
        
    # First filter by search term if provided
    if search_term:
        df = df[df["title"].str.contains(search_term, case=False, na=False)]
    
    # Then filter by Moroccan keywords
    if keywords:
        keyword_pattern = "|".join([re.escape(str(k)) for k in keywords])
        morocco_posts = df[df["title"].str.contains(keyword_pattern, case=False, na=False)]
    else:
        morocco_posts = df.copy()
    
    if morocco_posts.empty:
        return None
    
    # Get top keywords using best available method
    if HAS_SKLEARN:
        try:
            vec = CountVectorizer(stop_words="english", max_features=10)
            counts = vec.fit_transform(morocco_posts["title"].fillna(""))
            top_keywords = vec.get_feature_names_out().tolist()
        except:
            top_keywords = get_top_keywords(morocco_posts["title"].tolist())
    else:
        top_keywords = get_top_keywords(morocco_posts["title"].tolist())
    
    return {
        "morocco_posts": morocco_posts,
        "avg_sentiment": morocco_posts["sentiment_compound"].mean(),
        "post_count": len(morocco_posts),
        "top_keywords": top_keywords,
        "sample_posts": morocco_posts.head(3)[["title", "sentiment_compound"]]
    }

def render_morocco_analysis(df, keywords, search_term=None):
    """Simplified rendering function"""
    if not keywords or not isinstance(df, pd.DataFrame) or df.empty:
        return
    
    metrics = get_morocco_metrics(df, keywords, search_term)
    
    if not metrics:
        st.warning("No matching posts found. Try different keywords or broader search.")
        return
    
    st.subheader("🇲🇦 Moroccan Focus Analysis")
    
    # Key Metrics
    cols = st.columns(3)
    cols[0].metric("Relevant Posts", metrics["post_count"])
    cols[1].metric("Avg Sentiment", f"{metrics['avg_sentiment']:.2f}")
    
    # Top Keywords
    if metrics["top_keywords"]:
        cols[2].markdown("**Top Keywords**")
        cols[2].write(" ".join([f"`{word}`" for word in metrics["top_keywords"]]))
    
    # Sample Posts
    with st.expander("Sample Posts"):
        st.table(metrics["sample_posts"])