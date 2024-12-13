import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Constants
MAX_ACCOUNTS = int(os.getenv("MAX_ACCOUNTS", "1000"))

# Get credentials with fallback for testing
USER = os.getenv("TWITTER_USER")
PASSWORD = os.getenv("TWITTER_PASSWORD")
WORKFLOW = os.getenv("WORKFLOW")

if not USER or not PASSWORD:
    raise ValueError("Twitter credentials not found in environment variables. "
                    "Please set TWITTER_USER and TWITTER_PASSWORD")

# Add proxy configuration
PROXY_CONFIG = {
    "host": os.getenv("PROXY_HOST"),
    "port": int(os.getenv("PROXY_PORT", 0)),
    "username": os.getenv("PROXY_USERNAME"),
    "password": os.getenv("PROXY_PASSWORD"),
    "proxy_type": os.getenv("PROXY_TYPE", "http")
}

# Define available workflows
WORKFLOWS = {
    "timeline": "src.collectors.twitter.workflows.timeline_focused.timeline_focused",
    "engagement": "src.collectors.twitter.workflows.engagement_focused.engagement_focused",
    "complete": "src.collectors.twitter.workflows.complete_workflow.complete_workflow"
}

# Update SCRAPERS to include workflow settings
SCRAPERS = {
    "scraper1": {
        "username": USER,
        "password": PASSWORD,
        "proxy": PROXY_CONFIG if all([PROXY_CONFIG["host"], PROXY_CONFIG["port"]]) else None,
        "verify": os.getenv("VERIFY_SSL", "true").lower() == "true",
        "workflow": WORKFLOW
    }
}