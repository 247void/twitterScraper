import asyncio
import importlib
from src.collectors.twitter.collector import TwitterCollector
from src.utils.logging import setup_logging
from src.database.db import init_db
import config

def load_workflow(workflow_path):
    """Dynamically import workflow from path"""
    module_path, workflow_name = workflow_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, workflow_name)

async def run_collector(collector_id: str, scraper_config: dict):
    """Run a single collector"""
    workflow_path = config.WORKFLOWS[scraper_config["workflow"]]
    workflow = load_workflow(workflow_path)
    
    collector = TwitterCollector(
        collector_id=collector_id,
        config=scraper_config,
        workflow=workflow
    )
    
    await collector.collect_data()

async def main():
    setup_logging()
    init_db()
    
    # Create collector tasks
    collector_tasks = [
        run_collector(scraper_id, scraper_config)
        for scraper_id, scraper_config in config.SCRAPERS.items()
    ]
    
    # Run collectors
    await asyncio.gather(*collector_tasks)

if __name__ == "__main__":
    asyncio.run(main())