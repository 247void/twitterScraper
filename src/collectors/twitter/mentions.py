import sqlite3
from datetime import datetime
import re
from src.database.db import DB_PATH
from .constants import MENTION_TYPES

class MentionManager:
    def __init__(self, collector):
        self.collector = collector
        self.mention_pattern = re.compile(r'@(\w+)')
    
    async def process_mentions(self, tweet):
        """Extract and store mentions from a tweet"""
        try:
            # Extract mentions from tweet text
            mentions = self.mention_pattern.findall(tweet.text)
            mention_type = self._determine_mention_type(tweet)
            
            with sqlite3.connect(DB_PATH, timeout=20) as conn:
                c = conn.cursor()
                now = datetime.now().isoformat()
                
                for username in mentions:
                    c.execute('''
                        INSERT INTO tweet_mentions 
                        (tweet_id, mentioned_username, author_username, 
                         mention_type, discovered_at, collector_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        tweet.id,
                        username.lower(),
                        tweet.author.username,
                        mention_type,
                        now,
                        self.collector.collector_id
                    ))
                conn.commit()
                
        except Exception as e:
            print(f"[{self.collector.collector_id}] Error processing mentions: {str(e)}")
    
    def _determine_mention_type(self, tweet):
        """Determine the type of mention based on tweet context"""
        if hasattr(tweet, 'in_reply_to_status_id') and tweet.in_reply_to_status_id:
            return MENTION_TYPES['reply']
        elif hasattr(tweet, 'is_quoted') and tweet.is_quoted:
            return MENTION_TYPES['quote']
        elif hasattr(tweet, 'conversation_id'):
            return MENTION_TYPES['thread']
        return MENTION_TYPES['direct'] 