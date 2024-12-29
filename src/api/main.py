from fastapi import FastAPI, Query, HTTPException
from datetime import datetime, timedelta
import sqlite3
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from src.database.db import DB_PATH

# API Models
class Tweet(BaseModel):
    id: str
    author_username: str
    text: str
    created_at: str
    collected_at: str
    likes: int = 0
    retweets: int = 0
    views: Optional[Union[int, str]] = None
    bookmark_count: Optional[int] = None
    reply_counts: Optional[int] = None
    quote_counts: Optional[int] = None
    source: Optional[str] = None
    language: Optional[str] = None
    conversation_id: Optional[str] = None
    possibly_sensitive: bool = False
    is_retweet: bool = False
    is_quote: bool = False
    original_tweet_id: Optional[str] = None
    original_author: Optional[str] = None
    has_media: bool = False
    media_type: Optional[str] = None
    media_url: Optional[str] = None
    place_id: Optional[str] = None
    place_full_name: Optional[str] = None
    coordinates_lat: Optional[float] = None
    coordinates_long: Optional[float] = None

class UserStats(BaseModel):
    username: str
    twitter_id: Optional[str]
    following_count: Optional[int]
    followers_count: Optional[int]
    tweet_count: Optional[int]
    listed_count: Optional[int]
    created_at: Optional[str]
    description: Optional[str]
    location: Optional[str]
    url: Optional[str]
    verified: bool = False
    profile_image_url: Optional[str]
    profile_banner_url: Optional[str]
    last_tweet_check: Optional[str]
    last_following_check: Optional[str]
    avg_likes: float = 0
    max_likes: int = 0

# API Setup
app = FastAPI(
    title="Twitter Data Collector API",
    description="""
    API for querying collected Twitter data from our database. Features include:
    
    ## Data Types
    * Tweets with engagement metrics
    * User profiles and statistics
    * Hashtag tracking
    * Engagement data (replies, quotes, etc.)
    
    ## Collection Features
    * Timeline monitoring
    * User following relationships
    * Engagement tracking
    * Thread analysis
    
    ## Notes
    * All timestamps are in ISO format
    * Tweet views may show as 'Unavailable' for some tweets
    * Rate limits apply to protect the database
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/tweets", 
    response_model=List[Tweet],
    summary="Get collected tweets",
    description="""
    Retrieve tweets from the database with optional filtering.
    
    - **limit**: Maximum number of tweets to return
    - **offset**: Number of tweets to skip
    - **hours**: Only return tweets from the last N hours
    - **username**: Filter tweets by author username
    - **min_likes**: Minimum number of likes
    """
)
async def get_tweets(
    limit: int = Query(50, le=1000),
    offset: int = 0,
    hours: Optional[int] = None,
    username: Optional[str] = None,
    min_likes: Optional[int] = None
):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            query = "SELECT * FROM tweets WHERE 1=1"
            params = []
            
            if hours:
                query += " AND created_at > ?"
                params.append((datetime.now() - timedelta(hours=hours)).isoformat())
                
            if username:
                query += " AND author_username = ?"
                params.append(username)
                
            if min_likes:
                query += " AND likes >= ?"
                params.append(min_likes)
                
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            c.execute(query, params)
            return [dict(row) for row in c.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{username}/stats",
    response_model=UserStats,
    summary="Get user statistics",
    description="""
    Retrieve aggregated statistics for a specific Twitter user.
    
    Returns:
    - Tweet count
    - Average likes per tweet
    - Maximum likes on a single tweet
    - Follower and following counts (if available)
    """
)
async def get_user_stats(
    username: str
):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("""
                SELECT u.*, 
                       COUNT(DISTINCT t.id) as tweet_count,
                       AVG(t.likes) as avg_likes,
                       MAX(t.likes) as max_likes
                FROM users u
                LEFT JOIN tweets t ON u.username = t.author_username
                WHERE u.username = ?
                GROUP BY u.username
            """, (username,))
            
            result = c.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="User not found")
            return dict(result)
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health",
    summary="Health check",
    description="Check if the API is running and can connect to the database"
)
async def health_check():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.cursor().execute("SELECT 1")
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) 