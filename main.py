import asyncio
import importlib
from src.collectors.twitter.collector import TwitterCollector
from src.utils.logging import setup_logging
from src.database.db import init_db
import config

# Global dict to store collector instances
collectors = {}

def load_workflow(workflow_path):
    """Dynamically import workflow from path"""
    module_path, workflow_name = workflow_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, workflow_name)

async def create_collector(collector_id: str, scraper_config: dict):
    workflow_path = config.WORKFLOWS[scraper_config["workflow"]]
    workflow = load_workflow(workflow_path)
    
    collector = TwitterCollector(
        collector_id=collector_id,
        config=scraper_config,
        workflow=workflow
    )
    await collector.connect()
    return collector

async def main():
    setup_logging()
    init_db()
    
    # Create single collector instance
    scraper_id, scraper_config = next(iter(config.SCRAPERS.items()))
    collector = await create_collector(scraper_id, scraper_config)
    
    # Store collector for API use
    collectors[scraper_id] = collector
    
    # Run collector workflow
    await collector.collect_data()

if __name__ == "__main__":
    asyncio.run(main())