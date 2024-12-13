import sqlite3
from datetime import datetime
import random
import asyncio
from src.database.db import DB_PATH
from .constants import (
    MAX_FOLLOWS_PER_DAY,
    MUST_HAVE_TWEETS,
    MAX_FOLLOWING_PAGES
)

class FollowingManager:
    def __init__(self, collector):
        self.collector = collector

    async def should_follow_account(self, account):
        """Check if we should follow this account"""
        with sqlite3.connect(DB_PATH, timeout=20) as conn:
            c = conn.cursor()
            
            # Check if we already follow
            c.execute('''SELECT 1 FROM our_following 
                        WHERE username = ? AND collector_id = ?''', 
                        (account, self.collector.collector_id))
            if c.fetchone():
                return False
            
            # Check daily follow count
            today = datetime.now().date().isoformat()
            c.execute('''SELECT COUNT(*) FROM our_following 
                        WHERE collector_id = ? AND date(followed_at) = ?''',
                        (self.collector.collector_id, today))
            if c.fetchone()[0] >= MAX_FOLLOWS_PER_DAY:
                return False
            
            # Check their tweet count
            c.execute('''SELECT COUNT(*) FROM tweets 
                        WHERE author_username = ?''', (account,))
            if c.fetchone()[0] < MUST_HAVE_TWEETS:
                return False
            
            return True

    async def follow_account(self, account):
        """Follow an account and log it"""
        try:
            if not await self.should_follow_account(account):
                return False
                
            await self.collector.rate_limiter.log_api_call(f"follow/{account}")
            await self.collector.app.follow_user(account)
            
            with sqlite3.connect(DB_PATH, timeout=20) as conn:
                c = conn.cursor()
                c.execute('''INSERT INTO our_following 
                            (username, collector_id, followed_at) 
                            VALUES (?, ?, ?)''',
                            (account, self.collector.collector_id, datetime.now().isoformat()))
                conn.commit()
            
            print(f"[{self.collector.collector_id}] Followed @{account}")
            await asyncio.sleep(random.uniform(10, 30))
            
        except Exception as e:
            print(f"[{self.collector.collector_id}] Error following {account}: {str(e)}")
            return False

    async def fetch_account_followings(self, account, deep_crawl=False):
        """Fetch and store an account's following list"""
        try:
            # Get user info first
            await self.collector.rate_limiter.log_api_call(f"user_info/{account}")
            user_info = await self.collector.app.get_user_info(account)
            
            if not user_info:
                print(f"[{self.collector.collector_id}] Could not get user info for {account}")
                return False
            
            total_following = getattr(user_info, 'friends_count', 0)
            max_pages = min(
                MAX_FOLLOWING_PAGES * (3 if deep_crawl else 1), 
                (total_following + 49) // 50
            )
            
            print(f"[{self.collector.collector_id}] @{account} follows {total_following} accounts")
            print(f"[{self.collector.collector_id}] Checking {max_pages} pages {'(deep crawl)' if deep_crawl else ''}")
            
            followings = []
            seen_ids = set()
            cursor = None

            for current_page in range(max_pages):
                sleep_time = random.uniform(8, 12)
                print(f"[{self.collector.collector_id}] Scrolling to page {current_page + 1}, waiting {sleep_time}s...")
                await asyncio.sleep(sleep_time)
                
                response = await self.collector.app.get_user_followings(
                    username=account,
                    pages=1,
                    wait_time=3,
                    cursor=cursor  # Use cursor from previous response
                )

                if not response or not response.users:
                    print(f"[{self.collector.collector_id}] No followings found on page {current_page + 1}")
                    break

                # Filter out duplicates
                new_users = [user for user in response.users if user.id not in seen_ids]
                seen_ids.update(user.id for user in new_users)
                followings.extend(new_users)
                
                print(f"[{self.collector.collector_id}] Found {len(new_users)} new followings on page {current_page + 1}")

                # Store followings in database
                with sqlite3.connect(DB_PATH, timeout=20) as conn:
                    c = conn.cursor()
                    now = datetime.now().isoformat()
                    
                    # Store the followings
                    for user in new_users:
                        c.execute('''
                            INSERT OR IGNORE INTO account_followings 
                            (follower, following, following_id, discovered_at)
                            VALUES (?, ?, ?, ?)
                        ''', (account, user.username, user.id, now))
                    
                    # Log the check
                    c.execute('''
                        INSERT OR REPLACE INTO following_check_log
                        (username, page_checked, checked_at)
                        VALUES (?, ?, ?)
                    ''', (account, current_page + 1, now))
                    
                    # Update user's following count
                    c.execute('''
                        INSERT OR REPLACE INTO users (
                            username, twitter_id, following_count,
                            followers_count, tweet_count, listed_count,
                            created_at, description, location, url,
                            verified, profile_image_url, profile_banner_url,
                            last_following_check
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        account, 
                        user_info.id,
                        total_following,
                        getattr(user_info, 'followers_count', 0),
                        getattr(user_info, 'statuses_count', 0),
                        getattr(user_info, 'listed_count', 0),
                        getattr(user_info, 'created_at', None),
                        getattr(user_info, 'description', None),
                        getattr(user_info, 'location', None),
                        getattr(user_info, 'url', None),
                        getattr(user_info, 'verified', False),
                        getattr(user_info, 'profile_image_url', None),
                        getattr(user_info, 'profile_banner_url', None),
                        now
                    ))
                    
                    conn.commit()

                print(f"[{self.collector.collector_id}] Stored {len(new_users)} followings from page {current_page + 1}")
                
                # Get cursor for next page
                cursor = response.cursor
                if not cursor:
                    break

            print(f"[{self.collector.collector_id}] Stored {len(followings)} unique followings for @{account}")
            
            # Natural pause after following fetch
            sleep_time = random.uniform(30, 60)
            print(f"[{self.collector.collector_id}] Sleeping {sleep_time:.1f}s after following fetch")
            await asyncio.sleep(sleep_time)
            
        except Exception as e:
            print(f"[{self.collector.collector_id}] Error fetching followings for {account}: {str(e)}")
            # Log error details for debugging
            print(f"[{self.collector.collector_id}] Error details: {type(e).__name__}")
            return False