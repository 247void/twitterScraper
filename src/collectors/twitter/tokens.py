import re
import sqlite3
from datetime import datetime
from src.database.db import DB_PATH

class TokenManager:
    def __init__(self, collector):
        self.collector = collector
        self.token_pattern = r'[$#]([A-Z]{2,10})'  # Matches $BTC or #ETH
        
    async def process_token_mentions(self, tweet_id: str, text: str, author: str):
        """Extract and store token mentions from tweet"""
        mentions = re.finditer(self.token_pattern, text.upper())
        
        with sqlite3.connect(DB_PATH, timeout=20) as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            
            for match in mentions:
                symbol = match.group(1)
                print(f"[{self.collector.collector_id}] Found token mention: ${symbol} by @{author}")
                
                c.execute('''
                    INSERT INTO token_mentions 
                    (tweet_id, token_symbol, author_username, mentioned_at, collector_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (tweet_id, symbol, author, now, self.collector.collector_id))
            
            conn.commit() 