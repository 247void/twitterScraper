import sqlite3
from datetime import datetime
from src.database.db import Database, DB_PATH

class SearchManager:
    def __init__(self, collector):
        self.collector = collector
        self.db = Database()
    
    async def search_term(self, search_type: str, term: str, pages: int = 3) -> dict:
        """
        Search for term and get metrics from both top and recent tweets
        """
        try:
            # Pause workflow before search
            await self.collector.pause_workflow()
            
            metrics = {
                "top": {
                    "total_tweets": 0,
                    "unique_authors": set(),
                    "total_likes": 0,
                    "total_retweets": 0,
                    "oldest_tweet": None,
                    "newest_tweet": None
                },
                "recent": {
                    "total_tweets": 0,
                    "unique_authors": set(),
                    "total_likes": 0,
                    "total_retweets": 0,
                    "oldest_tweet": None,
                    "newest_tweet": None
                }
            }
            
            # Collect all data before DB operations
            all_users = set()
            all_tweets = []
            
            search_term = f"${term}" if search_type == "ticker" else term
            await self.collector.rate_limiter.handle_rate_limits()
            
            # Get top tweets
            await self.collector.rate_limiter.log_api_call(f"search/{search_term}/top")
            top_tweets = await self.collector.app.search(search_term, pages=pages, filter_="Top")
            
            # Process top tweets
            for tweet in top_tweets:
                if not hasattr(tweet, 'id'):
                    continue
                        
                metrics["top"]["total_tweets"] += 1
                metrics["top"]["unique_authors"].add(tweet.author.username)
                metrics["top"]["total_likes"] += tweet.likes
                metrics["top"]["total_retweets"] += tweet.retweet_counts
                
                all_users.add(tweet.author.username)
                
                has_media = hasattr(tweet, 'media') and tweet.media
                media_type = tweet.media[0].type if has_media else None
                media_url = tweet.media[0].url if has_media else None
                
                all_tweets.append((
                    str(tweet.id), 
                    tweet.author.username, 
                    tweet.text,
                    str(tweet.date), 
                    tweet.likes, 
                    tweet.retweet_counts,
                    datetime.now().isoformat(),
                    1 if has_media else 0, 
                    media_type, 
                    media_url
                ))
                
                tweet_date = datetime.fromisoformat(str(tweet.date))
                metrics["top"]["oldest_tweet"] = min(
                    metrics["top"]["oldest_tweet"] or tweet_date,
                    tweet_date
                )
                metrics["top"]["newest_tweet"] = max(
                    metrics["top"]["newest_tweet"] or tweet_date,
                    tweet_date
                )
            
            # Get recent tweets
            await self.collector.rate_limiter.log_api_call(f"search/{search_term}/recent")
            recent_tweets = await self.collector.app.search(search_term, pages=pages, filter_="Latest")
            
            # Process recent tweets
            for tweet in recent_tweets:
                if not hasattr(tweet, 'id'):
                    continue
                        
                metrics["recent"]["total_tweets"] += 1
                metrics["recent"]["unique_authors"].add(tweet.author.username)
                metrics["recent"]["total_likes"] += tweet.likes
                metrics["recent"]["total_retweets"] += tweet.retweet_counts
                
                all_users.add(tweet.author.username)
                
                has_media = hasattr(tweet, 'media') and tweet.media
                media_type = tweet.media[0].type if has_media else None
                media_url = tweet.media[0].url if has_media else None
                
                all_tweets.append((
                    str(tweet.id), 
                    tweet.author.username, 
                    tweet.text,
                    str(tweet.date), 
                    tweet.likes, 
                    tweet.retweet_counts,
                    datetime.now().isoformat(),
                    1 if has_media else 0, 
                    media_type, 
                    media_url
                ))
                
                tweet_date = datetime.fromisoformat(str(tweet.date))
                metrics["recent"]["oldest_tweet"] = min(
                    metrics["recent"]["oldest_tweet"] or tweet_date,
                    tweet_date
                )
                metrics["recent"]["newest_tweet"] = max(
                    metrics["recent"]["newest_tweet"] or tweet_date,
                    tweet_date
                )
            
            # Batch insert all data
            with self.db.get_connection() as conn:
                c = conn.cursor()
                
                # Batch insert users
                c.executemany('INSERT OR IGNORE INTO users (username) VALUES (?)', 
                            [(u,) for u in all_users])
                
                # Batch insert tweets
                c.executemany('''INSERT OR IGNORE INTO tweets 
                    (id, author_username, text, created_at, likes, retweets, collected_at,
                     has_media, media_type, media_url)
                    VALUES (?,?,?,?,?,?,?,?,?,?)''', all_tweets)
                
                conn.commit()
                
            # Calculate time-based metrics
            now = datetime.now()
            
            def get_timespan_metrics(section_metrics):
                if not section_metrics["newest_tweet"] or not section_metrics["oldest_tweet"]:
                    return None
                    
                timespan = section_metrics["newest_tweet"] - section_metrics["oldest_tweet"]
                timespan_hours = timespan.total_seconds() / 3600
                
                return {
                    "timespan_hours": round(timespan_hours, 2),
                    "tweets_per_hour": round(section_metrics["total_tweets"] / timespan_hours, 2) if timespan_hours > 0 else 0,
                    "engagement_per_tweet": {
                        "likes": round(section_metrics["total_likes"] / section_metrics["total_tweets"], 2) if section_metrics["total_tweets"] > 0 else 0,
                        "retweets": round(section_metrics["total_retweets"] / section_metrics["total_tweets"], 2) if section_metrics["total_tweets"] > 0 else 0
                    }
                }

            return {
                "search_type": search_type,
                "term": term,
                "search_timestamp": now.isoformat(),
                "top_tweets": {
                    "total_tweets": metrics["top"]["total_tweets"],
                    "unique_authors": len(metrics["top"]["unique_authors"]),
                    "time_range": {
                        "oldest": metrics["top"]["oldest_tweet"].isoformat() if metrics["top"]["oldest_tweet"] else None,
                        "newest": metrics["top"]["newest_tweet"].isoformat() if metrics["top"]["newest_tweet"] else None,
                    },
                    **get_timespan_metrics(metrics["top"])
                },
                "recent_tweets": {
                    "total_tweets": metrics["recent"]["total_tweets"],
                    "unique_authors": len(metrics["recent"]["unique_authors"]),
                    "time_range": {
                        "oldest": metrics["recent"]["oldest_tweet"].isoformat() if metrics["recent"]["oldest_tweet"] else None,
                        "newest": metrics["recent"]["newest_tweet"].isoformat() if metrics["recent"]["newest_tweet"] else None,
                    },
                    **get_timespan_metrics(metrics["recent"])
                },
                "metadata": {
                    "pages_fetched": pages,
                    "tweets_per_page": round((metrics["top"]["total_tweets"] + metrics["recent"]["total_tweets"]) / (2 * pages), 2)
                }
            }

        finally:
            # Always resume workflow after search
            await self.collector.resume_workflow() 