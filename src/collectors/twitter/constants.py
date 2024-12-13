# Timeline constants
MIN_TIMELINE_INTERVAL = 300   # Check timeline every 5-8 mins
MAX_TIMELINE_INTERVAL = 480   # 8 mins max between checks
SCROLL_TIME_NEW = (5, 20)     # Time between pages with new content
SCROLL_TIME_OLD = (2, 5)      # Quick scroll past old content
MAX_TIMELINE_PAGES = 15       # Much deeper scroll
MIN_NEW_TWEETS_TO_CONTINUE = 3  # Keep scrolling if we see at least 3 new tweets
TIMELINE_CHECK_CHANCE = 0.6   # 60% chance to check timeline

# Night mode settings
NIGHT_HOURS = [5, 6, 7, 8, 9, 10, 11]  # 10PM - 6AM
NIGHT_CHECK_CHANCE = 0.2  # 20% chance to check during night
NIGHT_SCROLL_TIME = (1800, 3600)  # 30-60 min between checks at night

# Rate limiting
RATE_LIMIT_THRESHOLD = 42
RATE_LIMIT_MAX = 48
MAX_CALLS_BEFORE_SLEEP = 45

# Following behavior
FOLLOW_CHANCE = 0.1
MAX_FOLLOWS_PER_DAY = 20
MUST_HAVE_TWEETS = 3
FOLLOWING_CHECK_CHANCE = 0.3  # 30% chance to check followings
FOLLOWING_CHECK_INTERVAL = 300  # 5 minutes between following checks
MAX_FOLLOWING_PAGES = 5  # Maximum pages to fetch when checking followings

# Batch settings
ACCOUNTS_PER_BATCH = 20  # Process accounts in batches of 20
HASHTAG_BATCH_SIZE = 50  # Process hashtags in batches
# Other constants from tweet_collector.py... 

# Add to existing constants:
MENTION_TYPES = {
    'direct': 'direct_mention',    # Mentioned in tweet text
    'reply': 'reply_mention',      # Mentioned via reply
    'quote': 'quote_mention',      # Mentioned in quote tweet
    'thread': 'thread_mention'     # Mentioned in thread
}

THREAD_TYPES = {
    'root': 'thread_root',         # First tweet in thread
    'branch': 'thread_branch',     # Reply that starts a new discussion
    'continuation': 'thread_cont', # Author's thread continuation
    'reply': 'thread_reply'       # Regular reply in thread
}