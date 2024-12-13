import sqlite3
from datetime import datetime
from src.database.db import DB_PATH
from .constants import THREAD_TYPES

class ThreadManager:
    def __init__(self, collector):
        self.collector = collector
    
    async def process_thread(self, tweet):
        """Process and store thread relationships"""
        try:
            thread_type = self._determine_thread_type(tweet)
            thread_position = await self._calculate_thread_position(tweet)
            
            with sqlite3.connect(DB_PATH, timeout=20) as conn:
                c = conn.cursor()
                now = datetime.now().isoformat()
                
                c.execute('''
                    INSERT INTO tweet_threads 
                    (tweet_id, conversation_id, thread_type, 
                     thread_position, parent_tweet_id, root_tweet_id,
                     discovered_at, collector_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tweet.id,
                    getattr(tweet, 'conversation_id', tweet.id),
                    thread_type,
                    thread_position,
                    getattr(tweet, 'in_reply_to_status_id', None),
                    self._get_root_tweet_id(tweet),
                    now,
                    self.collector.collector_id
                ))
                conn.commit()
                
        except Exception as e:
            print(f"[{self.collector.collector_id}] Error processing thread: {str(e)}")
    
    def _determine_thread_type(self, tweet):
        """Determine the type of thread position"""
        if not getattr(tweet, 'in_reply_to_status_id', None):
            return THREAD_TYPES['root']
        elif tweet.author.username == self._get_parent_author(tweet):
            return THREAD_TYPES['continuation']
        elif self._has_branch_replies(tweet):
            return THREAD_TYPES['branch']
        return THREAD_TYPES['reply']
    
    async def _calculate_thread_position(self, tweet):
        """Calculate position in thread (0 for root)"""
        if not getattr(tweet, 'in_reply_to_status_id', None):
            return 0
            
        with sqlite3.connect(DB_PATH, timeout=20) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT COUNT(*) FROM tweet_threads 
                WHERE conversation_id = ? 
                AND thread_position < 
                    (SELECT created_at FROM tweets WHERE id = ?)
            ''', (tweet.conversation_id, tweet.id))
            return c.fetchone()[0] + 1
    
    def _get_parent_author(self, tweet):
        """Get the username of the parent tweet author"""
        if not getattr(tweet, 'in_reply_to_status_id', None):
            return None
            
        with sqlite3.connect(DB_PATH, timeout=20) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT author_username FROM tweets 
                WHERE id = ?
            ''', (tweet.in_reply_to_status_id,))
            result = c.fetchone()
            return result[0] if result else None
    
    def _get_root_tweet_id(self, tweet):
        """Get the root tweet ID of the thread"""
        if not getattr(tweet, 'conversation_id', None):
            return tweet.id
            
        with sqlite3.connect(DB_PATH, timeout=20) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT tweet_id FROM tweet_threads 
                WHERE conversation_id = ? 
                AND thread_type = ?
                LIMIT 1
            ''', (tweet.conversation_id, THREAD_TYPES['root']))
            result = c.fetchone()
            return result[0] if result else tweet.id
            
    def _has_branch_replies(self, tweet):
        """Check if tweet has spawned its own discussion thread"""
        with sqlite3.connect(DB_PATH, timeout=20) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT COUNT(*) FROM tweets 
                WHERE in_reply_to_status_id = ?
                GROUP BY author_username
                HAVING COUNT(*) > 2
            ''', (tweet.id,))
            return c.fetchone() is not None 