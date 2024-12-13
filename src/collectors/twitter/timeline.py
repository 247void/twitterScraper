from datetime import datetime, timedelta
import sqlite3
import random
import asyncio
from time import time
from tweety.types import HOME_TIMELINE_TYPE_FOR_YOU, HOME_TIMELINE_TYPE_FOLLOWING
from .constants import (
    MIN_TIMELINE_INTERVAL,
    MAX_TIMELINE_INTERVAL,
    SCROLL_TIME_NEW,
    SCROLL_TIME_OLD,
    MAX_TIMELINE_PAGES,
    MIN_NEW_TWEETS_TO_CONTINUE
)
from src.database.db import DB_PATH
import json

class TimelineManager:
    def __init__(self, collector):
        self.collector = collector
        self.last_timeline_check = 0

    async def fetch_timeline_tweets(self, max_pages=None):
        """Fetch and save timeline tweets with organic scrolling behavior"""
        try:
            current_time = time()
            time_since_last = current_time - self.last_timeline_check
            
            if time_since_last < MIN_TIMELINE_INTERVAL:
                return False
            
            await self.collector.rate_limiter.rate_limit_sleep()
            
            timeline_type = random.choice([HOME_TIMELINE_TYPE_FOR_YOU, HOME_TIMELINE_TYPE_FOLLOWING])
            print(f"\n[{self.collector.collector_id}] Deep scrolling {timeline_type}...")
            
            new_tweets_total = 0
            consecutive_low_pages = 0
            cursor = None  # Initialize cursor
            
            max_pages = max_pages or MAX_TIMELINE_PAGES
            print(f"[{self.collector.collector_id}] Scrolling up to {max_pages} pages")
            
            for page in range(max_pages):
                # Get tweets from timeline
                tweets = await self.collector.app.get_home_timeline(
                    timeline_type=timeline_type,
                    pages=1,
                    wait_time=3,
                    cursor=cursor
                )
                
                total_tweets = len(tweets) if tweets else 0
                new_tweets = 0
                
                # Process tweets...
                with sqlite3.connect(DB_PATH, timeout=20) as conn:
                    c = conn.cursor()
                    for tweet in tweets:
                        if not hasattr(tweet, 'id'):
                            continue
                        
                        print(f"[{self.collector.collector_id}] Processing tweet {tweet.id} by @{tweet.author.username}")
                        
                        c.execute('SELECT id FROM tweets WHERE id = ?', (tweet.id,))
                        exists = c.fetchone()
                        
                        if not exists:
                            try:
                                c.execute('''
                                    INSERT INTO tweets (
                                        id, author_id, author_username, text, 
                                        created_at, collected_at, collector_id,
                                        likes, retweets, views, bookmark_count,
                                        reply_counts, quote_counts, source, language,
                                        conversation_id, possibly_sensitive,
                                        is_retweet, is_quote, original_tweet_id, original_author,
                                        has_media, media_type, media_url,
                                        place_id, place_full_name, coordinates_lat, coordinates_long,
                                        edit_history_tweet_ids, edit_controls
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    tweet.id,
                                    tweet.author.id,
                                    tweet.author.username,
                                    tweet.text,
                                    tweet.created_on.isoformat(),
                                    datetime.now().isoformat(),
                                    self.collector.collector_id,
                                    tweet.likes,
                                    tweet.retweet_counts if hasattr(tweet, 'retweet_counts') else 0,
                                    getattr(tweet, 'views', 0),
                                    getattr(tweet, 'bookmark_count', 0),
                                    getattr(tweet, 'reply_counts', 0),
                                    getattr(tweet, 'quote_counts', 0),
                                    getattr(tweet, 'source', None),
                                    getattr(tweet, 'language', None),
                                    getattr(tweet, 'conversation_id', None),
                                    1 if getattr(tweet, 'possibly_sensitive', False) else 0,
                                    1 if hasattr(tweet, 'is_retweet') and tweet.is_retweet else 0,
                                    1 if hasattr(tweet, 'is_quoted') and tweet.is_quoted else 0,
                                    None,  # original_tweet_id
                                    None,  # original_author
                                    1 if hasattr(tweet, 'media') and tweet.media else 0,
                                    tweet.media[0].type if hasattr(tweet, 'media') and tweet.media else None,
                                    tweet.media[0].url if hasattr(tweet, 'media') and tweet.media else None,
                                    getattr(tweet, 'place_id', None),
                                    getattr(tweet, 'place_full_name', None),
                                    getattr(tweet, 'coordinates_lat', None),
                                    getattr(tweet, 'coordinates_long', None),
                                    json.dumps(getattr(tweet, 'edit_history_tweet_ids', [])),
                                    json.dumps(getattr(tweet, 'edit_controls', {}))
                                ))
                                new_tweets += 1
                            except Exception as e:
                                print(f"[{self.collector.collector_id}] ERROR inserting tweet {tweet.id}: {str(e)}")
                        
                        conn.commit()
                
                # Add this page's new tweets to total
                new_tweets_total += new_tweets
                
                # Calculate quality of the page
                new_tweet_ratio = new_tweets / total_tweets if total_tweets > 0 else 0
                is_quality_page = new_tweet_ratio >= 0.3  # At least 30% new tweets
                
                # Adjust scroll behavior based on page quality
                if is_quality_page:
                    scroll_time = random.uniform(*SCROLL_TIME_NEW)
                    print(f"[{self.collector.collector_id}] Quality page ({new_tweet_ratio:.1%} new), reading carefully: {scroll_time:.1f}s")
                    consecutive_low_pages = 0
                else:
                    scroll_time = random.uniform(*SCROLL_TIME_OLD)
                    print(f"[{self.collector.collector_id}] Low quality page ({new_tweet_ratio:.1%} new), quick scroll: {scroll_time:.1f}s")
                    consecutive_low_pages += 1
                
                # Exit if we've seen too many low quality pages
                if consecutive_low_pages >= 2:
                    print(f"[{self.collector.collector_id}] Too many low quality pages, moving on...")
                    break
                
                await asyncio.sleep(scroll_time)
                
                await self.collector.rate_limiter.log_api_call("home_timeline")
                
                # Debug: Print what we got from the API
                print(f"[{self.collector.collector_id}] DEBUG: Got {len(tweets) if tweets else 0} tweets from timeline")
                if tweets:
                    first_tweet = tweets[0]
                    print(f"[{self.collector.collector_id}] DEBUG: First tweet: {vars(first_tweet) if hasattr(first_tweet, '__dict__') else 'No vars'}")
                    print(f"[{self.collector.collector_id}] DEBUG: Tweet text: {first_tweet.text if hasattr(first_tweet, 'text') else 'No text'}")
                else:
                    print(f"[{self.collector.collector_id}] DEBUG: tweets is empty or None")
                
                print(f"[{self.collector.collector_id}] Found {new_tweets} new tweets on page {page + 1}")
                
                # Update cursor for next page
                cursor = tweets.cursor if hasattr(tweets, 'cursor') else None
                if not cursor:
                    break
            
            print(f"[{self.collector.collector_id}] Deep scroll complete - Saved {new_tweets_total} new tweets")
            
            self.last_timeline_check = current_time
            if new_tweets_total < MIN_NEW_TWEETS_TO_CONTINUE:
                print(f"[{self.collector.collector_id}] Few new tweets, will check again in {MAX_TIMELINE_INTERVAL/60:.1f}m")
                self.last_timeline_check = current_time + (MAX_TIMELINE_INTERVAL - MIN_TIMELINE_INTERVAL)
            
            return new_tweets_total > 0
        except Exception as e:
            print(f"[{self.collector.collector_id}] Timeline fetch error: {str(e)}")
            return False