import sqlite3
from datetime import datetime, timedelta
import random
import asyncio
from src.database.db import DB_PATH
from .constants import (
    RATE_LIMIT_MAX,
    RATE_LIMIT_THRESHOLD
)

class RateLimiter:
    def __init__(self, collector):
        self.collector = collector
        self.last_call_time = None

    async def check_rate_limit(self):
        """Get current number of API calls in last 15 minutes"""
        with sqlite3.connect(DB_PATH, timeout=20) as conn:
            c = conn.cursor()
            fifteen_mins_ago = (datetime.now() - timedelta(minutes=15)).isoformat()
            c.execute('SELECT COUNT(*) FROM api_calls WHERE timestamp > ? AND collector_id = ?', 
                     (fifteen_mins_ago, self.collector.collector_id))
            return c.fetchone()[0]

    async def log_api_call(self, endpoint):
        """Log an API call and enforce minimum delay"""
        # Enforce minimum 2s between calls
        now = datetime.now()
        if self.last_call_time:
            elapsed = (now - self.last_call_time).total_seconds()
            if elapsed < 2:
                await asyncio.sleep(2 - elapsed)
        
        self.last_call_time = now

        # Log the call
        with sqlite3.connect(DB_PATH, timeout=20) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO api_calls (timestamp, endpoint, collector_id) VALUES (?, ?, ?)',
                     (now.isoformat(), endpoint, self.collector.collector_id))
            conn.commit()

    async def rate_limit_sleep(self):
        """Sleep if we're approaching rate limits"""
        calls = await self.check_rate_limit()
        
        if calls >= RATE_LIMIT_MAX:
            # Emergency brake - sleep longer
            wait_time = random.uniform(600, 900)  # 10-15 mins
            print(f"[{self.collector.collector_id}] Rate limit max reached ({calls}/50). Sleeping {wait_time/60:.1f}m")
            await asyncio.sleep(wait_time)
            return True
        
        elif calls >= RATE_LIMIT_THRESHOLD:
            # Getting close - quick pause
            wait_time = random.uniform(60, 180)  # 1-3 mins
            print(f"[{self.collector.collector_id}] Rate limit threshold ({calls}/50). Pausing {wait_time/60:.1f}m")
            await asyncio.sleep(wait_time)
            return True
        
        return False

    async def handle_rate_limits(self):
        """Less aggressive rate limit management"""
        calls = await self.check_rate_limit()
        
        if calls >= RATE_LIMIT_MAX:
            wait_time = random.uniform(600, 900)  # 10-15 mins
            print(f"[{self.collector.collector_id}] Rate limit max reached ({calls}/50 calls). Sleeping {wait_time/60:.1f}m")
            await asyncio.sleep(wait_time)
            return True
        
        elif calls >= RATE_LIMIT_THRESHOLD:
            wait_time = random.uniform(60, 180)  # 1-3 mins
            print(f"[{self.collector.collector_id}] Rate limit threshold ({calls}/50 calls). Pausing {wait_time/60:.1f}m")
            await asyncio.sleep(wait_time)
            return True
        
        return False 