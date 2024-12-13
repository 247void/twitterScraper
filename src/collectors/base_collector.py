from abc import ABC, abstractmethod
from datetime import datetime

class BaseCollector(ABC):
    def __init__(self, collector_id, config):
        self.collector_id = collector_id
        self.config = config
        self.session = None
    
    @abstractmethod
    async def connect(self):
        """Establish connection to the platform"""
        pass
    
    @abstractmethod
    async def collect_data(self):
        """Main collection logic"""
        pass
    
    @abstractmethod
    async def handle_rate_limits(self):
        """Handle rate limiting"""
        pass
    
    def close(self):
        """Cleanup resources"""
        if self.session:
            self.session.close() 