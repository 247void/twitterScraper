import logging
from pathlib import Path
import json
from datetime import datetime

class TweetFilter(logging.Filter):
    def filter(self, record):
        return "HTTP Request" not in record.msg

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger().addFilter(TweetFilter())

def update_status(task, next_run=None, status_file=Path("data/collector_status.json")):
    status = {
        "current_task": task,
        "next_run": next_run.isoformat() if next_run else None,
        "last_update": datetime.now().isoformat()
    }
    with open(status_file, "w") as f:
        json.dump(status, f) 