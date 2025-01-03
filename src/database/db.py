import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta
import zlib
import json

DB_PATH = Path("data/tweets.db")

def init_db():
    # Create all parent directories
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY,
                  twitter_id TEXT UNIQUE,
                  following_count INTEGER,
                  followers_count INTEGER,
                  tweet_count INTEGER,
                  listed_count INTEGER,
                  created_at TEXT,
                  description TEXT,
                  location TEXT,
                  url TEXT,
                  verified INTEGER,
                  profile_image_url TEXT,
                  profile_banner_url TEXT,
                  last_tweet_check TEXT,
                  last_following_check TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS api_calls
                 (timestamp TEXT,
                  endpoint TEXT,
                  collector_id TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS tweets
                 (id TEXT PRIMARY KEY,
                  author_id TEXT,
                  author_username TEXT,
                  text TEXT,
                  created_at TEXT,
                  collected_at TEXT,
                  collector_id TEXT,
                  likes INTEGER,
                  retweets INTEGER,
                  views INTEGER,
                  bookmark_count INTEGER,
                  reply_counts INTEGER,
                  quote_counts INTEGER,
                  source TEXT,
                  language TEXT,
                  conversation_id TEXT,
                  possibly_sensitive INTEGER,
                  is_retweet INTEGER,
                  is_quote INTEGER,
                  original_tweet_id TEXT,
                  original_author TEXT,
                  has_media INTEGER,
                  media_type TEXT,
                  media_url TEXT,
                  place_id TEXT,
                  place_full_name TEXT,
                  coordinates_lat REAL,
                  coordinates_long REAL,
                  edit_history_tweet_ids TEXT,
                  edit_controls TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS tweet_mentions
                 (tweet_id TEXT NOT NULL,
                  mentioned_username TEXT NOT NULL,
                  author_username TEXT NOT NULL,
                  mention_type TEXT NOT NULL,
                  discovered_at TEXT NOT NULL,
                  collector_id TEXT NOT NULL,
                  PRIMARY KEY (tweet_id, mentioned_username),
                  FOREIGN KEY (tweet_id) REFERENCES tweets(id),
                  FOREIGN KEY (author_username) REFERENCES users(username))''')

    c.execute('''CREATE TABLE IF NOT EXISTS tweet_threads
                 (tweet_id TEXT NOT NULL,
                  conversation_id TEXT NOT NULL,
                  thread_type TEXT NOT NULL,
                  thread_position INTEGER NOT NULL,
                  parent_tweet_id TEXT,
                  root_tweet_id TEXT NOT NULL,
                  discovered_at TEXT NOT NULL,
                  collector_id TEXT NOT NULL,
                  PRIMARY KEY (tweet_id),
                  FOREIGN KEY (tweet_id) REFERENCES tweets(id),
                  FOREIGN KEY (parent_tweet_id) REFERENCES tweets(id),
                  FOREIGN KEY (root_tweet_id) REFERENCES tweets(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS token_mentions
                 (tweet_id TEXT NOT NULL,
                  token_symbol TEXT NOT NULL,
                  author_username TEXT NOT NULL,
                  mentioned_at TEXT NOT NULL,
                  price_at_mention REAL,
                  price_24h REAL,
                  price_7d REAL,
                  collector_id TEXT NOT NULL,
                  PRIMARY KEY (tweet_id, token_symbol),
                  FOREIGN KEY (tweet_id) REFERENCES tweets(id),
                  FOREIGN KEY (author_username) REFERENCES users(username))''')

    c.execute('''CREATE TABLE IF NOT EXISTS influencer_scores
                 (author_username TEXT NOT NULL,
                  token_symbol TEXT NOT NULL,
                  calls_count INTEGER DEFAULT 0,
                  successful_calls INTEGER DEFAULT 0,
                  last_updated TEXT NOT NULL,
                  collector_id TEXT NOT NULL,
                  PRIMARY KEY (author_username, token_symbol))''')

    c.execute('''CREATE TABLE IF NOT EXISTS account_followings
                 (follower TEXT,
                  following TEXT,
                  following_id TEXT,
                  discovered_at TEXT,
                  PRIMARY KEY (follower, following))''')

    c.execute('''CREATE TABLE IF NOT EXISTS our_following
                 (username TEXT,
                  collector_id TEXT,
                  followed_at TEXT,
                  PRIMARY KEY (username, collector_id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS following_check_log
                 (username TEXT,
                  page_checked INTEGER,
                  checked_at TEXT,
                  PRIMARY KEY (username, page_checked))''')

    c.execute('''CREATE TABLE IF NOT EXISTS tweet_engagements
                 (tweet_id TEXT,
                  author_username TEXT,
                  engagement_type TEXT,
                  engaged_at TEXT,
                  collector_id TEXT,
                  PRIMARY KEY (tweet_id, collector_id, engagement_type))''')

    c.execute('''CREATE TABLE IF NOT EXISTS tweet_hashtags
                 (tweet_id TEXT,
                  hashtag TEXT,
                  discovered_at TEXT,
                  PRIMARY KEY (tweet_id, hashtag))''')

    c.execute('''CREATE TABLE IF NOT EXISTS search_cache
                 (search_type TEXT,
                  term TEXT,
                  metrics TEXT,
                  last_searched_at TEXT,
                  PRIMARY KEY (search_type, term))''')

    # Create indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_tweets_author ON tweets(author_username)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_followings_follower ON account_followings(follower)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_api_calls_endpoint ON api_calls(endpoint)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_hashtags ON tweet_hashtags(hashtag)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_engagements_time ON tweet_engagements(engaged_at)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_hashtags_time ON tweet_hashtags(discovered_at)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_tweets_created ON tweets(created_at)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_tweets_engagement ON tweets(likes, retweets)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_mentions_username ON tweet_mentions(mentioned_username)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_threads_conversation ON tweet_threads(conversation_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_threads_root ON tweet_threads(root_tweet_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_token_mentions_symbol ON token_mentions(token_symbol)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_token_mentions_author ON token_mentions(author_username)')

    conn.commit()
    conn.close()

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    def get_connection(self):
        return sqlite3.connect(self.db_path, timeout=20)
        
    def execute(self, query, params=None):
        with self.get_connection() as conn:
            c = conn.cursor()
            if params:
                c.execute(query, params)
            else:
                c.execute(query)
            conn.commit()
            return c.fetchall()
            
    # Add methods for common database operations 