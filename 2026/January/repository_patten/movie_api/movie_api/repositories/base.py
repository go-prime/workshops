from abc import ABC, abstractmethod
from typing import List, Optional, Any

class IRepository(ABC):
    """Abstract repository interface - defines contract"""
    
    @abstractmethod
    def get_by_id(self, id: Any) -> Optional[Any]:
        """Retrieve single entity by ID"""
        pass
    
    @abstractmethod
    def get_all(self) -> List[Any]:
        """Retrieve all entities"""
        pass
    
    @abstractmethod
    def add(self, entity: Any) -> Any:
        """Create new entity"""
        pass
    
    @abstractmethod
    def update(self, id: Any, entity: Any) -> Optional[Any]:
        """Update existing entity"""
        pass
    
    @abstractmethod
    def delete(self, id: Any) -> bool:
        """Delete entity"""
        pass
    
    @abstractmethod
    def find(self, **criteria) -> List[Any]:
        """Find entities matching criteria"""
        pass