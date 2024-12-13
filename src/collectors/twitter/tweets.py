import sqlite3
from datetime import datetime
import random
import asyncio
import json
from src.database.db import DB_PATH
from .constants import (
    FOLLOW_CHANCE,
    MUST_HAVE_TWEETS
)
from src.collectors.twitter.tokens import TokenManager

class TweetManager:
    def __init__(self, collector):
        self.collector = collector
        self.token_manager = TokenManager(collector)

    async def fetch_account_tweets(self, account):
        """Fetch and process tweets for an account"""
        try:
            if await self.collector.rate_limiter.check_rate_limit() >= 45:
                base_wait = 15 * 60
                jitter = random.uniform(-5 * 60, 5 * 60)
                wait_time = base_wait + jitter
                print(f"[{self.collector.collector_id}] Rate limit hit, sleeping {wait_time/60:.1f}m")
                await asyncio.sleep(wait_time)
                
            await self.collector.rate_limiter.log_api_call(f"tweets/{account}")
            print(f"\n[{self.collector.collector_id}] Fetching tweets for @{account}")
            
            tweets = await self.collector.app.get_tweets(account, pages=1)
            if not tweets:
                print(f"[{self.collector.collector_id}] No tweets found for {account}")
                return False

            with sqlite3.connect(DB_PATH, timeout=20) as conn:
                c = conn.cursor()
                c.execute('INSERT OR IGNORE INTO users (username) VALUES (?)', (account,))
                for tweet in tweets:
                    if not hasattr(tweet, 'id'):
                        continue
                    
                    # Check for media
                    has_media = hasattr(tweet, 'media') and tweet.media
                    media_type = None
                    media_url = None
                    if has_media:
                        media_type = tweet.media[0].type if tweet.media else None
                        media_url = tweet.media[0].url if tweet.media else None
                        print(f"  └ Media: {media_type} - {media_url}")
                    
                    print(f"\nTweet from @{account}: {tweet.text[:100]}...")
                    
                    c.execute('''INSERT OR IGNORE INTO tweets 
                               (id, author_username, text, created_at, likes, retweets, collected_at,
                                is_retweet, is_quote, original_tweet_id, original_author,
                                has_media, media_type, media_url,
                                views, bookmark_count, reply_counts, quote_counts,
                                source, language, conversation_id, possibly_sensitive,
                                place_id, place_full_name, coordinates_lat, coordinates_long,
                                edit_history_tweet_ids, edit_controls)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                             (str(tweet.id), 
                              account, 
                              tweet.text, 
                              str(tweet.date),
                              tweet.likes, 
                              tweet.retweet_counts if hasattr(tweet, 'retweet_counts') else 0,
                              datetime.now().isoformat(),
                              1 if hasattr(tweet, 'is_retweet') and tweet.is_retweet else 0,
                              1 if hasattr(tweet, 'is_quoted') and tweet.is_quoted else 0,
                              None,
                              None,
                              1 if has_media else 0,
                              media_type,
                              media_url,
                              getattr(tweet, 'views', 0),
                              getattr(tweet, 'bookmark_count', 0),
                              getattr(tweet, 'reply_counts', 0),
                              getattr(tweet, 'quote_counts', 0),
                              getattr(tweet, 'source', None),
                              getattr(tweet, 'language', None),
                              getattr(tweet, 'conversation_id', None),
                              1 if getattr(tweet, 'possibly_sensitive', False) else 0,
                              getattr(tweet, 'place_id', None),
                              getattr(tweet, 'place_full_name', None),
                              getattr(tweet, 'coordinates_lat', None),
                              getattr(tweet, 'coordinates_long', None),
                              json.dumps(getattr(tweet, 'edit_history_tweet_ids', [])),
                              json.dumps(getattr(tweet, 'edit_controls', {}))))
                    
                    # Handle retweets
                    if hasattr(tweet, 'is_retweet') and tweet.is_retweet:
                        rt = getattr(tweet, 'retweeted_tweet', None)
                        if rt and hasattr(rt, 'author'):
                            print(f"  └─ Retweet of @{rt.author.username}: {rt.text[:100]}...")
                            
                            c.execute('''INSERT OR IGNORE INTO tweets 
                                       (id, author_username, text, created_at, likes, retweets, collected_at,
                                        is_retweet, is_quote, original_tweet_id, original_author,
                                        has_media, media_type, media_url,
                                        views, bookmark_count, reply_counts, quote_counts,
                                        source, language, conversation_id, possibly_sensitive,
                                        place_id, place_full_name, coordinates_lat, coordinates_long,
                                        edit_history_tweet_ids, edit_controls)
                                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                     (str(rt.id), 
                                      rt.author.username, 
                                      rt.text, 
                                      str(rt.date),
                                      rt.likes, 
                                      rt.retweet_counts if hasattr(rt, 'retweet_counts') else 0,
                                      datetime.now().isoformat(),
                                      0, 0, None, None,
                                      0, None, None,  # media fields
                                      getattr(rt, 'views', 0),
                                      getattr(rt, 'bookmark_count', 0),
                                      getattr(rt, 'reply_counts', 0),
                                      getattr(rt, 'quote_counts', 0),
                                      getattr(rt, 'source', None),
                                      getattr(rt, 'language', None),
                                      getattr(rt, 'conversation_id', None),
                                      1 if getattr(rt, 'possibly_sensitive', False) else 0,
                                      getattr(rt, 'place_id', None),
                                      getattr(rt, 'place_full_name', None),
                                      getattr(rt, 'coordinates_lat', None),
                                      getattr(rt, 'coordinates_long', None),
                                      json.dumps(getattr(rt, 'edit_history_tweet_ids', [])),
                                      json.dumps(getattr(rt, 'edit_controls', {}))))
                            
                            c.execute('''UPDATE tweets 
                                       SET original_tweet_id = ?, 
                                           original_author = ?,
                                           is_retweet = 1,
                                           is_quote = 0
                                       WHERE id = ?''',
                                     (str(rt.id), rt.author.username, str(tweet.id)))
                        else:
                            print(f"  └─ Retweet found but missing author info")
                            continue
                    
                    # Handle quotes
                    if hasattr(tweet, 'is_quoted') and tweet.is_quoted and hasattr(tweet, 'quoted_tweet'):
                        qt = tweet.quoted_tweet
                        print(f"  └─ Quote of @{qt.author.username}: {qt.text[:100]}...")
                        
                        c.execute('''INSERT OR IGNORE INTO tweets 
                                   (id, author_username, text, created_at, likes, retweets, collected_at,
                                    is_retweet, is_quote, original_tweet_id, original_author,
                                    has_media, media_type, media_url,
                                    views, bookmark_count, reply_counts, quote_counts,
                                    source, language, conversation_id, possibly_sensitive,
                                    place_id, place_full_name, coordinates_lat, coordinates_long,
                                    edit_history_tweet_ids, edit_controls)
                                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                 (str(qt.id), 
                                  qt.author.username, 
                                  qt.text, 
                                  str(qt.date),
                                  qt.likes, 
                                  qt.retweet_counts if hasattr(qt, 'retweet_counts') else 0,
                                  datetime.now().isoformat(),
                                  0, 0, None, None,
                                  0, None, None,  # media fields
                                  getattr(qt, 'views', 0),
                                  getattr(qt, 'bookmark_count', 0),
                                  getattr(qt, 'reply_counts', 0),
                                  getattr(qt, 'quote_counts', 0),
                                  getattr(qt, 'source', None),
                                  getattr(qt, 'language', None),
                                  getattr(qt, 'conversation_id', None),
                                  1 if getattr(qt, 'possibly_sensitive', False) else 0,
                                  getattr(qt, 'place_id', None),
                                  getattr(qt, 'place_full_name', None),
                                  getattr(qt, 'coordinates_lat', None),
                                  getattr(qt, 'coordinates_long', None),
                                  json.dumps(getattr(qt, 'edit_history_tweet_ids', [])),
                                  json.dumps(getattr(qt, 'edit_controls', {}))))
                        
                        c.execute('''UPDATE tweets 
                                   SET original_tweet_id = ?, 
                                       original_author = ?,
                                       is_retweet = 0,
                                       is_quote = 1
                                   WHERE id = ?''',
                                 (str(qt.id), qt.author.username, str(tweet.id)))
                
                if hasattr(tweet, 'hashtags'):
                    for tag in tweet.hashtags:
                        c.execute('''
                            INSERT OR IGNORE INTO tweet_hashtags
                            (tweet_id, hashtag, discovered_at)
                            VALUES (?, ?, ?)
                        ''', (tweet.id, tag.lower(), datetime.now().isoformat()))
                
                conn.commit()
        except sqlite3.Error as e:
            print(f"[{self.collector.collector_id}] Database error processing tweets for {account}: {str(e)}")
            return False
        except Exception as e:
            print(f"[{self.collector.collector_id}] Error fetching tweets for {account}: {str(e)}")
            print(f"[{self.collector.collector_id}] Error type: {type(e).__name__}")
            return False
        
        if random.random() < FOLLOW_CHANCE:
            if await self.collector.following_manager.should_follow_account(account):
                await self.collector.following_manager.follow_account(account) 

    async def process_tweet(self, tweet):
        """Process a single tweet for storage"""
        # Store base tweet data
        await self._store_tweet_data(tweet)
        
        # Process mentions and thread data
        await self.collector.mention_manager.process_mentions(tweet)
        await self.collector.thread_manager.process_thread(tweet)
        
        # Add token mention processing
        if hasattr(tweet, 'text'):
            await self.token_manager.process_token_mentions(
                tweet.id,
                tweet.text,
                tweet.author.username
            )
        
        return True