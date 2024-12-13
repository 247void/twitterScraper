from ..workflow import Workflow, WorkflowStep

timeline_focused = Workflow(
    name="timeline_focused",
    entry_point="timeline_check",
    constants={
        "FOLLOWING_CHECK_CHANCE": 0.15,  # 15% chance to check followings
        "MAX_FOLLOWING_PAGES": 5,        # Less following pages
        "FOLLOW_CHANCE": 0.2,            # Lower follow chance
        "MAX_TIMELINE_PAGES": 15         # More timeline pages
    },
    steps={
        "timeline_check": WorkflowStep(
            action="fetch_timeline",
            params={"max_pages": 15},
            next_steps=["process_batch"],
            min_sleep=20,
            max_sleep=45
        ),
        "process_batch": WorkflowStep(
            action="process_batch",
            params={},
            next_steps=["timeline_check"],
            min_sleep=30,
            max_sleep=90
        )
    }
) 