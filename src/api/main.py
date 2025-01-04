from fastapi import FastAPI, Query, HTTPException
from datetime import datetime, timedelta
import sqlite3
from typing import List, Optional, Dict
from pydantic import BaseModel
from src.database.db import DB_PATH
from src.collectors.twitter.collector import TwitterCollector
import config
from src.utils.logging import setup_logging
from src.database.db import init_db
import json

# API Models
class SearchMetrics(BaseModel):
    search_type: str
    term: str
    top_tweets: dict
    recent_tweets: dict

# Global collectors dict
collectors: Dict[str, TwitterCollector] = {}

# API Setup
app = FastAPI(
    title="Twitter Data Collector API",
    description="API for querying collected Twitter data from our database.",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize collector on startup using existing config"""
    setup_logging()
    init_db()
    
    # Use first scraper from config
    scraper_id, scraper_config = next(iter(config.SCRAPERS.items()))
    
    collector = TwitterCollector(
        collector_id=scraper_id,
        config=scraper_config
    )
    
    await collector.connect()
    collectors[scraper_id] = collector

@app.get("/tweets", 
    response_model=List[dict],
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

@app.get("/search", 
    response_model=SearchMetrics,
    summary="Search Twitter for metrics",
    description="""
    Search Twitter and get engagement metrics.
    
    - **search_type**: Type of search (ticker, user, etc)
    - **term**: Search term (e.g. AAPL)
    - **collector_id**: Optional specific collector to use
    """
)
async def search_metrics(
    search_type: str = Query(...),
    term: str = Query(...),
    collector_id: Optional[str] = Query(None),
    force_refresh: bool = Query(False)
):
    try:
        # Check if we searched this term recently
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT metrics, last_searched_at 
                FROM search_cache 
                WHERE search_type = ? AND term = ?
                AND last_searched_at > ?
            """, (
                search_type, 
                term,
                (datetime.now() - timedelta(minutes=30)).isoformat()
            ))
            cached = c.fetchone()
            
            if cached and not force_refresh:
                return json.loads(cached[0])
        
        # If no recent search or force refresh, get new data
        collector = collectors.get(collector_id) or next(iter(collectors.values()))
        results = await collector.search_term(search_type, term)
        
        # Update search cache
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO search_cache 
                (search_type, term, metrics, last_searched_at)
                VALUES (?, ?, ?, ?)
            """, (
                search_type,
                term, 
                json.dumps(results),
                datetime.now().isoformat()
            ))
            conn.commit()
            
        return results
        
    except Exception as e:
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