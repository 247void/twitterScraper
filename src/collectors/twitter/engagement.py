import sqlite3
import asyncio
import random
from datetime import datetime
from src.database.db import DB_PATH
from .constants import RATE_LIMIT_THRESHOLD

class EngagementManager:
    def __init__(self, collector):
        self.collector = collector
        self.blacklisted_users = {
            'elonmusk',
        }

    async def check_engagement(self, max_depth=5, min_engagement=100, min_reply_likes=10):
        """Collect meaningful engagement data for viral tweets"""
        try:
            # Find viral tweets from last 24h not yet processed
            with sqlite3.connect(DB_PATH, timeout=20) as conn:
                c = conn.cursor()
                placeholders = ','.join(['?' for _ in self.blacklisted_users])
                query = f'''
                    SELECT id, author_username, likes, retweets 
                    FROM tweets 
                    WHERE collected_at > datetime('now', '-24 hours')
                    AND (likes + retweets) > ?
                    AND author_username NOT IN ({placeholders})
                    AND id NOT IN (SELECT tweet_id FROM tweet_engagements WHERE engagement_type = 'checked')
                    ORDER BY (likes + retweets) DESC
                    LIMIT ?
                '''
                params = [min_engagement] + list(self.blacklisted_users) + [max_depth]
                c.execute(query, params)
                viral_tweets = c.fetchall()
                
                print(f"Found {len(viral_tweets)} viral tweets:")
                for tweet_id, author, likes, rts in viral_tweets:
                    print(f"- Tweet {tweet_id} by @{author}: {likes} likes, {rts} RTs")

            for tweet_id, author, likes, rts in viral_tweets:
                print(f"[{self.collector.collector_id}] Processing viral tweet {tweet_id} by @{author}")
                
                # Get the full conversation thread
                conversation = await self.collector.app.get_tweet_comments(
                    tweet_id, 
                    pages=random.randint(3, 5),  # Get 3-5 pages at once
                    wait_time=2,
                    get_hidden=False
                )

                # Store parent tweets first
                if conversation:
                    await self._store_engagement_data(tweet_id, conversation, [])
                    print(f"[{self.collector.collector_id}] Found {len(conversation)} parent tweets")
                
                # Get initial replies
                replies = []
                total_pages = random.randint(3, 5)  # Sometimes read more, sometimes less
                
                for page in range(total_pages):
                    await self.collector.rate_limiter.log_api_call(f"tweet_comments/{tweet_id}/page/{page}")
                    
                    # More natural reading pause between pages
                    if page > 0:
                        read_time = random.uniform(10, 25)  # Longer pause between pages
                        print(f"[{self.collector.collector_id}] Reading replies, page {page}...")
                        await asyncio.sleep(read_time)
                    
                    page_replies = await self.collector.app.get_tweet_comments(tweet_id, pages=1)
                    if not page_replies:
                        break
                        
                    # Filter quality replies but keep some lower-engagement ones randomly
                    quality_replies = [r for r in page_replies if 
                        getattr(r, 'likes', 0) >= min_reply_likes or 
                        random.random() < 0.2]  # 20% chance to keep lower-engagement replies
                    
                    replies.extend(quality_replies)
                    
                    # Sometimes dive into reply threads
                    for reply in quality_replies:
                        if getattr(reply, 'reply_counts', 0) > 5 and random.random() < 0.3:
                            print(f"[{self.collector.collector_id}] This reply looks interesting, checking responses...")
                            await asyncio.sleep(random.uniform(5, 10))
                            reply_thread = await self.collector.app.get_tweet_comments(reply.id, pages=1)
                            if reply_thread:
                                replies.extend(reply_thread)

                # More natural pause between tweets
                think_time = random.uniform(15, 45)
                print(f"[{self.collector.collector_id}] Taking a {think_time:.1f}s break to process what we read")
                await asyncio.sleep(think_time)

            return True

        except Exception as e:
            print(f"[{self.collector.collector_id}] Engagement check error: {str(e)}")
            return False

    async def _store_engagement_data(self, tweet_id, replies, quotes):
        """Store quality replies and quotes"""
        with sqlite3.connect(DB_PATH, timeout=20) as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()

            # Store replies as tweets
            for reply in replies:
                c.execute('''
                    INSERT OR IGNORE INTO tweets 
                    (id, author_username, text, created_at, collected_at,
                     likes, retweets, views, reply_counts,
                     in_reply_to_id, conversation_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (reply.id, reply.author.username, reply.text,
                     reply.created_at, now,
                     getattr(reply, 'likes', 0),
                     getattr(reply, 'retweet_counts', 0),
                     getattr(reply, 'views', 0),
                     getattr(reply, 'reply_counts', 0),
                     tweet_id, tweet_id))

            # Store quotes as tweets
            for quote in quotes:
                c.execute('''
                    INSERT OR IGNORE INTO tweets 
                    (id, author_username, text, created_at, collected_at,
                     likes, retweets, views, reply_counts,
                     is_quote, original_tweet_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ''', (quote.id, quote.author.username, quote.text,
                     quote.created_at, now,
                     getattr(quote, 'likes', 0),
                     getattr(quote, 'retweet_counts', 0),
                     getattr(quote, 'views', 0),
                     getattr(quote, 'reply_counts', 0),
                     tweet_id))

            conn.commit()

            # Store engagement records
            for reply in replies:
                c.execute('''
                    INSERT INTO tweet_engagements
                    (tweet_id, author_username, engagement_type, engaged_at, collector_id)
                    VALUES (?, ?, 'reply', ?, ?)
                ''', (tweet_id, reply.author.username, now, self.collector.collector_id))

            for quote in quotes:
                c.execute('''
                    INSERT INTO tweet_engagements
                    (tweet_id, author_username, engagement_type, engaged_at, collector_id)
                    VALUES (?, ?, 'quote', ?, ?)
                ''', (tweet_id, quote.author.username, now, self.collector.collector_id))

            conn.commit()