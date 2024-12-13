from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    username: str
    twitter_id: Optional[str] = None
    following_count: Optional[int] = None
    followers_count: Optional[int] = None
    tweet_count: Optional[int] = None
    listed_count: Optional[int] = None
    created_at: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    verified: bool = False
    profile_image_url: Optional[str] = None
    profile_banner_url: Optional[str] = None
    last_tweet_check: Optional[datetime] = None
    last_following_check: Optional[datetime] = None

@dataclass
class Tweet:
    id: str
    author_id: str
    author_username: str
    text: str
    created_at: str
    collected_at: str
    collector_id: str
    likes: Optional[int] = None
    retweets: Optional[int] = None
    is_retweet: bool = False
    is_quote: bool = False
    original_tweet_id: Optional[str] = None
    original_author: Optional[str] = None
    has_media: bool = False
    media_type: Optional[str] = None
    media_url: Optional[str] = None

@dataclass
class Following:
    follower: str
    following: str
    following_id: str
    discovered_at: str

@dataclass
class TweetHashtag:
    tweet_id: str
    hashtag: str
    discovered_at: str 

@dataclass
class Engagement:
    tweet_id: str
    author_username: str
    engagement_type: str  # 'reply', 'quote', 'checked'
    engaged_at: str
    collector_id: str 