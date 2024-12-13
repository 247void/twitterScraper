from ..workflow import Workflow, WorkflowStep

engagement_focused = Workflow(
    name="engagement_focused",
    entry_point="check_viral",
    constants={
        "MIN_ENGAGEMENT": 100,
        "MIN_REPLY_LIKES": 10,
        "MAX_TWEETS_PER_BATCH": 3,    # Process fewer tweets per batch
        "MAX_DEPTH_PER_TWEET": 50,    # But go deeper per tweet
    },
    steps={
        "check_viral": WorkflowStep(
            action="check_engagement",
            params={
                "max_depth": 3,
                "min_engagement": 100
            },
            next_steps=["process_engagement"],
            min_sleep=180,            # 3-4 min between viral searches
            max_sleep=240,
            rate_limit_sleep=True
        ),
        "process_engagement": WorkflowStep(
            action="process_tweet_engagement",
            params={
                "max_depth": 50,
                "min_reply_likes": 10,
                "delay_range": (5, 15) # Random 5-15s between requests
            },
            next_steps=["check_viral"],
            min_sleep=30,             # Short rest between tweets
            max_sleep=60,
            rate_limit_sleep=True
        )
    }
) 