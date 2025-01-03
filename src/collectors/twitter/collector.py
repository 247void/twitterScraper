from datetime import datetime, timedelta
import random
import asyncio
from tweety import TwitterAsync
from tweety.exceptions import ActionRequired
from typing import Optional
from inspect import signature

from src.collectors.base_collector import BaseCollector
from .timeline import TimelineManager
from .tweets import TweetManager
from .following import FollowingManager
from .rate_limiting import RateLimiter
from .constants import (
    NIGHT_HOURS,
    NIGHT_CHECK_CHANCE,
    FOLLOWING_CHECK_CHANCE,
    ACCOUNTS_PER_BATCH
)
from .workflow import Workflow, WorkflowStep
from .engagement import EngagementManager
from .mentions import MentionManager
from .threads import ThreadManager
from .search import SearchManager

class TwitterCollector(BaseCollector):
    def __init__(self, collector_id, config, workflow: Optional[Workflow] = None):
        super().__init__(collector_id, config)
        self.session_name = f"session_{collector_id}"
        self.accounts_file = f"accounts_{collector_id}.txt"
        self.app = None
        self.current_batch_index = 0
        self.all_accounts = []
        self.proxy = None
        self.verify = config.get("verify", True)
        
        # Initialize managers
        self.rate_limiter = RateLimiter(self)
        self.timeline_manager = TimelineManager(self)
        self.tweet_manager = TweetManager(self)
        self.following_manager = FollowingManager(self)
        self.engagement_manager = EngagementManager(self)
        self.mention_manager = MentionManager(self)
        self.thread_manager = ThreadManager(self)
        self.search_manager = SearchManager(self)
        
        # Load default workflow if none provided
        self.workflow = workflow or self.load_default_workflow()
        
        # Override constants with workflow constants
        for key, value in self.workflow.constants.items():
            globals()[key] = value

        self.workflow_paused = False  # Add pause flag
        self._pause_lock = asyncio.Lock()  # Add lock for thread safety

    def _setup_proxy(self, proxy_config):
        """Set up proxy configuration"""
        if not proxy_config:
            print(f"[{self.collector_id}] No proxy configuration found")
            return None
        
        try:
            proxy_types = {
                "http": "http",
                "socks4": "socks4",
                "socks5": "socks5"
            }
            
            proxy_type = proxy_types.get(proxy_config["proxy_type"], "http")
            print(f"[{self.collector_id}] Using proxy type: {proxy_type}")
            
            proxy_str = f"{proxy_config['host']}:{proxy_config['port']}"
            print(f"[{self.collector_id}] Base proxy string: {proxy_str}")
            
            if proxy_config.get("username"):
                auth = f"{proxy_config['username']}:{proxy_config['password']}"
                proxy_str = f"{auth}@{proxy_str}"
                print(f"[{self.collector_id}] Added auth to proxy string")
            
            final_url = f"{proxy_type}://{proxy_str}"
            print(f"[{self.collector_id}] Final proxy URL: {final_url}")
            return final_url
            
        except Exception as e:
            print(f"[{self.collector_id}] Error setting up proxy: {str(e)}")
            return None

    async def connect(self):
        """Establish connection to Twitter"""
        try:
            if self.app:  # Already connected
                return
            
            proxy_url = self._setup_proxy(self.config.get("proxy"))
            print(f"[{self.collector_id}] Setting up proxy: {proxy_url}")
            
            self.app = TwitterAsync(
                self.session_name,
                proxy=proxy_url
            )
            print(f"[{self.collector_id}] TwitterAsync initialized")

            print(f"[{self.collector_id}] Attempting sign-in for {self.config['username']}")
            try:
                await self.app.sign_in(
                    username=self.config["username"],
                    password=self.config["password"]
                )
            except ActionRequired:
                print(f"[{self.collector_id}] 2FA required")
                verify_code = input(f"[{self.collector_id}] Enter 2FA code: ")
                await self.app.sign_in(
                    username=self.config["username"],
                    password=self.config["password"],
                )
            
            print(f"[{self.collector_id}] Successfully signed in")
            
            with open(self.accounts_file, 'r') as f:
                self.all_accounts = [line.strip() for line in f if line.strip()]
                random.shuffle(self.all_accounts)
            print(f"[{self.collector_id}] Loaded {len(self.all_accounts)} accounts total")

        except Exception as e:
            print(f"[{self.collector_id}] Error in connect(): {str(e)}")

    def load_default_workflow(self) -> Workflow:
        """Load the original behavior as default workflow"""
        return Workflow(
            name="default",
            entry_point="timeline_check",
            constants={},  # Use existing constants
            steps={
                "timeline_check": WorkflowStep(
                    action="fetch_timeline",
                    params={},
                    next_steps=["process_accounts"]
                ),
                "process_accounts": WorkflowStep(
                    action="process_batch",
                    params={},
                    next_steps=["timeline_check"]
                )
            }
        )

    async def collect_data(self):
        """Dynamic workflow-based collection with pause support"""
        try:
            if not self.app:
                await self.connect()

            current_step = self.workflow.entry_point
            
            while True:
                try:
                    # Check if workflow is paused
                    if self.workflow_paused:
                        await asyncio.sleep(1)
                        continue

                    step = self.workflow.steps[current_step]
                    result, next_step = await self.execute_step(step)
                    current_step = next_step if next_step else step.next_steps[0]
                    await self.rate_limiter.handle_rate_limits()

                except Exception as e:
                    print(f"[{self.collector_id}] Error in workflow step: {e}")
                    await asyncio.sleep(300)

        except Exception as e:
            print(f"[{self.collector_id}] Error in collect_data(): {str(e)}")

    async def execute_step(self, step: WorkflowStep):
        """Execute a workflow step with dynamic path selection"""
        action_map = {
            "fetch_timeline": self.timeline_manager.fetch_timeline_tweets,
            "process_batch": self.process_account_batch,
            "fetch_tweets": self.tweet_manager.fetch_account_tweets,
            "fetch_following": self.following_manager.fetch_account_followings,
            "check_engagement": self.engagement_manager.check_engagement,
            "process_mentions": self.mention_manager.process_mentions,
            "process_thread": self.thread_manager.process_thread
        }
        
        if step.action not in action_map:
            raise ValueError(f"Unknown action: {step.action}")
        
        func = action_map[step.action]
        valid_params = signature(func).parameters.keys()
        filtered_params = {k: v for k, v in step.params.items() if k in valid_params}
        
        # Execute the action and get result
        result = await func(**filtered_params)
        
        # Handle rate limits if configured
        if step.rate_limit_sleep:
            await self.rate_limiter.handle_rate_limits()
        
        # Apply workflow-defined sleep
        if step.max_sleep > 0:
            sleep_time = random.uniform(step.min_sleep, step.max_sleep)
            print(f"[{self.collector_id}] Workflow sleep: {sleep_time:.1f}s")
            await asyncio.sleep(sleep_time)
        
        # Return both result and next step
        return result, step.choose_next_step(result)

    async def process_account_batch(self):
        """Process a batch of accounts"""
        current_batch = self.get_current_batch()
        
        for account in current_batch:
            # Fetch and process tweets (this now includes mentions and threads)
            await self.tweet_manager.fetch_account_tweets(account)
            
            if random.random() < self.workflow.constants.get("FOLLOWING_CHECK_CHANCE", FOLLOWING_CHECK_CHANCE):
                await self.following_manager.fetch_account_followings(account, deep_crawl=True)
            
            await asyncio.sleep(random.uniform(10, 20))
        
        self.rotate_batch()
        return True

    def get_current_batch(self):
        """Get current batch of accounts"""
        start_idx = self.current_batch_index * ACCOUNTS_PER_BATCH
        end_idx = start_idx + ACCOUNTS_PER_BATCH
        
        batch = self.all_accounts[start_idx:end_idx]
        print(f"[{self.collector_id}] Current batch ({start_idx}:{end_idx}): {', '.join(batch)}")
        return batch
    
    def rotate_batch(self):
        """Move to next batch of accounts"""
        total_batches = (len(self.all_accounts) + ACCOUNTS_PER_BATCH - 1) // ACCOUNTS_PER_BATCH
        self.current_batch_index = (self.current_batch_index + 1) % total_batches
        
        print(f"[{self.collector_id}] Rotating to batch {self.current_batch_index + 1} of {total_batches}")
        return self.get_current_batch()

    async def handle_rate_limits(self):
        """Implement abstract method by delegating to RateLimiter"""
        return await self.rate_limiter.handle_rate_limits()

    async def search_term(self, search_type: str, term: str, pages: int = 3) -> dict:
        """
        Search term and get metrics
        """
        try:
            return await self.search_manager.search_term(search_type, term, pages)
        except Exception as e:
            print(f"[{self.collector_id}] Search error: {str(e)}")
            raise

    async def pause_workflow(self):
        """Pause the workflow"""
        async with self._pause_lock:
            self.workflow_paused = True
            print(f"[{self.collector_id}] Workflow paused")

    async def resume_workflow(self):
        """Resume the workflow"""
        async with self._pause_lock:
            self.workflow_paused = False
            print(f"[{self.collector_id}] Workflow resumed")
