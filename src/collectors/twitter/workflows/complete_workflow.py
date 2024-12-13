from ..workflow import Workflow, WorkflowStep
from ..constants import (
    MIN_TIMELINE_INTERVAL,
    MAX_TIMELINE_INTERVAL
)

complete_workflow = Workflow(
    name="complete_workflow",
    entry_point="timeline_check",
    constants={
        "FOLLOWING_CHECK_CHANCE": 0.3,    
        "MAX_FOLLOWING_PAGES": 5,         
        "FOLLOW_CHANCE": 0.15,           
        "MIN_ENGAGEMENT": 75,            
        "MIN_REPLY_LIKES": 8,            
        "MAX_TIMELINE_PAGES": 10,
        "MIN_NEW_TWEETS": 3              
    },
    steps={
        "timeline_check": WorkflowStep(
            action="fetch_timeline",
            params={"max_pages": 10},
            next_steps=["process_batch", "check_viral"],
            min_sleep=30,
            max_sleep=60,
            rate_limit_sleep=True
        ),
        "process_batch": WorkflowStep(
            action="process_batch",
            params={},
            next_steps=["check_viral", "timeline_check"],
            min_sleep=45,
            max_sleep=90,
            rate_limit_sleep=True
        ),
        "check_viral": WorkflowStep(
            action="check_engagement",
            params={
                "max_depth": 3,
                "min_engagement": 75,
                "min_reply_likes": 8
            },
            next_steps=["timeline_check", "process_batch"],
            min_sleep=120,
            max_sleep=180,
            rate_limit_sleep=True
        )
    }
) 