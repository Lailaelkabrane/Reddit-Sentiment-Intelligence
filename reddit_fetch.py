import pandas as pd
from functools import lru_cache  # Python's built-in caching
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import datetime
import logging
from tenacity import retry, stop_after_attempt
from dotenv import load_dotenv
import os
import praw

# Configure logging
logging.basicConfig(filename='reddit_fetch.log', level=logging.INFO)
load_dotenv()
# Initialize VADER
analyzer = SentimentIntensityAnalyzer()

@retry(stop=stop_after_attempt(3))
def fetch_posts_safely(keyword: str, limit: int = 50) -> pd.DataFrame:
    """Fetches Reddit posts with sentiment analysis and robust error handling."""
    try:
        import praw  # Import here to avoid PRAW dependency unless needed
        reddit = praw.Reddit(
            client_id=os.getenv("client_id"),
            client_secret=os.getenv("client_secret"),
            user_agent=os.getenv("SocialSentimentApp")
        )
        
        posts = reddit.subreddit("all").search(keyword, limit=limit)
        data = []
        
        for post in posts:
            text = post.title + " " + post.selftext
            vs = analyzer.polarity_scores(text)
            created_time = datetime.datetime.fromtimestamp(post.created) if post.created else None
            
            data.append({
                "title": post.title,
                "text": post.selftext,
                "score": post.score,
                "num_comments": post.num_comments,
                "created": created_time,
                "url": post.url,
                "sentiment_neg": vs["neg"],
                "sentiment_neu": vs["neu"],
                "sentiment_pos": vs["pos"],
                "sentiment_compound": vs["compound"],
            })
            
        logging.info(f"Successfully fetched {len(data)} posts for keyword: {keyword}")
        return pd.DataFrame(data)
        
    except Exception as e:
        logging.error(f"Failed to fetch data: {str(e)}")
        return pd.DataFrame()

@lru_cache(maxsize=1)  # Python's built-in cache (alternative to st.cache_data)
def process_reddit_data(df: pd.DataFrame) -> pd.DataFrame:
    """Cached data processing pipeline."""
    df = df.copy()
    df['date'] = pd.to_datetime(df['created']).dt.date
    return df

def validate_reddit_data(df: pd.DataFrame) -> bool:
    """Validates required columns exist in the DataFrame."""
    required_columns = ["title", "sentiment_compound", "created"]
    return all(col in df.columns for col in required_columns)