from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import random
import asyncio

@dataclass
class WorkflowStep:
    action: str  # e.g., "fetch_timeline", "fetch_tweets", "fetch_following"
    params: Dict[str, Any]
    conditions: Optional[Dict[str, Any]] = None
    next_steps: Optional[List[str]] = None
    min_sleep: float = 0  # Minimum sleep after action
    max_sleep: float = 0  # Maximum sleep after action
    rate_limit_sleep: bool = True  # Whether to check rate limits after action
    
    def choose_next_step(self, result: Any) -> Optional[str]:
        """Choose next step based on action result"""
        if not self.next_steps:
            return None
        
        if isinstance(result, bool) and not result:
            # If action failed/returned False, try alternate path
            return self.next_steps[-1]
        elif isinstance(result, int) and result < 3:
            # For timeline checks with few new tweets
            return self.next_steps[-1]
        
        # Default to first path
        return self.next_steps[0]
    
@dataclass
class Workflow:
    def __init__(self, name: str, steps: Dict[str, WorkflowStep], entry_point: str, constants: Dict[str, Any]):
        self.name = name
        self.steps = steps
        self.entry_point = entry_point
        self.constants = constants

    async def execute(self, collector):
        """Execute workflow with error handling"""
        current_step = self.entry_point
        
        while current_step:
            try:
                step = self.steps[current_step]
                
                # Execute step action
                result = await getattr(collector, step.action)(**step.params)
                
                # Handle sleep
                if step.rate_limit_sleep:
                    await collector.rate_limiter.rate_limit_sleep()
                if step.min_sleep > 0:
                    sleep_time = random.uniform(step.min_sleep, step.max_sleep)
                    print(f"[{collector.collector_id}] Workflow sleep: {sleep_time:.1f}s")
                    await asyncio.sleep(sleep_time)
                
                # Determine next step
                current_step = step.choose_next_step(result)
                
            except Exception as e:
                print(f"[{collector.collector_id}] Error in workflow step {current_step}: {str(e)}")
                # Log error but continue to next step
                current_step = step.next_steps[0] if step.next_steps else None
                continue