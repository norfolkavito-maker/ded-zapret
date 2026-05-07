"""
Strategy registry for DedZapret Manager

Manages strategy storage, retrieval, and indexing.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .model import Strategy, StrategyStatus, StrategyTag, StrategyKind
from zapret_manager.core.paths import SafePaths
from zapret_manager.core.logging import get_logger, LogComponent


class StrategyRegistry:
    """Registry for managing strategies"""
    
    def __init__(self, safe_paths: SafePaths):
        self.safe_paths = safe_paths
        self.strategies_file = safe_paths.get_strategies_file()
        self.logger = get_logger("registry", LogComponent.STRATEGY)
        self._strategies: Dict[str, Strategy] = {}
        self._loaded = False
    
    def load_strategies(self) -> bool:
        """Load strategies from file"""
        try:
            if not self.strategies_file.exists():
                self.logger.info("Strategies file not found, creating default")
                self._strategies = {}
                self._loaded = True
                return True
            
            with open(self.strategies_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            strategies = data.get('strategies', {})
            self._strategies = {}
            
            for strategy_id, strategy_data in strategies.items():
                try:
                    strategy = Strategy.from_dict(strategy_data)
                    self._strategies[strategy_id] = strategy
                except Exception as e:
                    self.logger.error(f"Failed to load strategy {strategy_id}", error=str(e))
            
            self._loaded = True
            self.logger.info(f"Loaded {len(self._strategies)} strategies")
            return True
            
        except Exception as e:
            self.logger.error("Failed to load strategies", error=str(e))
            self._strategies = {}
            self._loaded = False
            return False
    
    def save_strategies(self) -> bool:
        """Save strategies to file"""
        try:
            # Ensure directory exists
            self.strategies_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert strategies to dict
            strategies_data = {
                "version": "1.0.0",
                "updated_at": datetime.now().isoformat(),
                "strategies": {
                    strategy_id: strategy.to_dict()
                    for strategy_id, strategy in self._strategies.items()
                }
            }
            
            with open(self.strategies_file, 'w', encoding='utf-8') as f:
                json.dump(strategies_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(self._strategies)} strategies")
            return True
            
        except Exception as e:
            self.logger.error("Failed to save strategies", error=str(e))
            return False
    
    def add_strategy(self, strategy: Strategy) -> bool:
        """Add strategy to registry"""
        try:
            if strategy.id in self._strategies:
                self.logger.warning(f"Strategy {strategy.id} already exists, updating")
            
            self._strategies[strategy.id] = strategy
            self.logger.info(f"Added strategy {strategy.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add strategy {strategy.id}", error=str(e))
            return False
    
    def remove_strategy(self, strategy_id: str) -> bool:
        """Remove strategy from registry"""
        try:
            if strategy_id not in self._strategies:
                self.logger.warning(f"Strategy {strategy_id} not found")
                return False
            
            del self._strategies[strategy_id]
            self.logger.info(f"Removed strategy {strategy_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove strategy {strategy_id}", error=str(e))
            return False
    
    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get strategy by ID"""
        return self._strategies.get(strategy_id)
    
    def get_all_strategies(self) -> List[Strategy]:
        """Get all strategies"""
        return list(self._strategies.values())
    
    def get_strategies_by_status(self, status: StrategyStatus) -> List[Strategy]:
        """Get strategies by status"""
        return [strategy for strategy in self._strategies.values() 
                if strategy.status == status]
    
    def get_strategies_by_tag(self, tag: StrategyTag) -> List[Strategy]:
        """Get strategies by tag"""
        return [strategy for strategy in self._strategies.values() 
                if strategy.has_tag(tag)]
    
    def get_strategies_by_kind(self, kind: StrategyKind) -> List[Strategy]:
        """Get strategies by kind"""
        return [strategy for strategy in self._strategies.values() 
                if strategy.kind == kind]
    
    def get_strategies_by_source(self, source: str) -> List[Strategy]:
        """Get strategies by source"""
        return [strategy for strategy in self._strategies.values() 
                if strategy.source == source]
    
    def get_ready_strategies(self) -> List[Strategy]:
        """Get strategies that are ready for use"""
        return [strategy for strategy in self._strategies.values() 
                if strategy.is_ready()]
    
    def get_valid_strategies(self) -> List[Strategy]:
        """Get strategies that are valid"""
        return [strategy for strategy in self._strategies.values() 
                if strategy.is_valid()]
    
    def search_strategies(self, query: str) -> List[Strategy]:
        """Search strategies by name or description"""
        query_lower = query.lower()
        results = []
        
        for strategy in self._strategies.values():
            if (query_lower in strategy.name.lower() or 
                query_lower in strategy.description_ru.lower() or
                query_lower in strategy.description_en.lower()):
                results.append(strategy)
        
        return results
    
    def get_strategy_count(self) -> int:
        """Get total strategy count"""
        return len(self._strategies)
    
    def get_strategy_count_by_status(self) -> Dict[str, int]:
        """Get strategy count by status"""
        counts = {}
        for strategy in self._strategies.values():
            status = strategy.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts
    
    def get_strategy_count_by_tag(self) -> Dict[str, int]:
        """Get strategy count by tag"""
        counts = {}
        for strategy in self._strategies.values():
            for tag in strategy.tags:
                tag_name = tag.value
                counts[tag_name] = counts.get(tag_name, 0) + 1
        return counts
    
    def get_strategy_count_by_source(self) -> Dict[str, int]:
        """Get strategy count by source"""
        counts = {}
        for strategy in self._strategies.values():
            source = strategy.source
            counts[source] = counts.get(source, 0) + 1
        return counts
    
    def update_strategy(self, strategy_id: str, updates: Dict[str, Any]) -> bool:
        """Update strategy with partial updates"""
        try:
            strategy = self._strategies.get(strategy_id)
            if not strategy:
                self.logger.error(f"Strategy {strategy_id} not found")
                return False
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(strategy, key):
                    setattr(strategy, key, value)
            
            strategy.updated_at = datetime.now().isoformat()
            self.logger.info(f"Updated strategy {strategy_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update strategy {strategy_id}", error=str(e))
            return False
    
    def clear_strategies(self) -> bool:
        """Clear all strategies"""
        try:
            self._strategies.clear()
            self.logger.info("Cleared all strategies")
            return True
            
        except Exception as e:
            self.logger.error("Failed to clear strategies", error=str(e))
            return False
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Get registry information"""
        return {
            "total_strategies": len(self._strategies),
            "loaded": self._loaded,
            "strategies_file": str(self.strategies_file),
            "last_updated": datetime.now().isoformat(),
            "count_by_status": self.get_strategy_count_by_status(),
            "count_by_tag": self.get_strategy_count_by_tag(),
            "count_by_source": self.get_strategy_count_by_source()
        }
    
    def export_strategies(self, output_file: Optional[Path] = None) -> Optional[Path]:
        """Export strategies to file"""
        try:
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = self.safe_paths.get_reports_dir() / f"strategies_export_{timestamp}.json"
            
            export_data = {
                "export_time": datetime.now().isoformat(),
                "registry_info": self.get_registry_info(),
                "strategies": {
                    strategy_id: strategy.to_dict()
                    for strategy_id, strategy in self._strategies.items()
                }
            }
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Exported strategies to {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error("Failed to export strategies", error=str(e))
            return None
    
    def import_strategies(self, import_file: Path, merge: bool = True) -> bool:
        """Import strategies from file"""
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            strategies_data = data.get('strategies', {})
            imported_count = 0
            
            for strategy_id, strategy_data in strategies_data.items():
                try:
                    strategy = Strategy.from_dict(strategy_data)
                    
                    if merge and strategy_id in self._strategies:
                        self.logger.warning(f"Strategy {strategy_id} already exists, skipping")
                        continue
                    
                    self._strategies[strategy_id] = strategy
                    imported_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to import strategy {strategy_id}", error=str(e))
            
            self.logger.info(f"Imported {imported_count} strategies from {import_file}")
            return True
            
        except Exception as e:
            self.logger.error("Failed to import strategies", error=str(e))
            return False


# Global instance for singleton pattern
_strategy_registry_instance: Optional[StrategyRegistry] = None


def get_strategy_registry() -> StrategyRegistry:
    """Get global StrategyRegistry instance"""
    global _strategy_registry_instance
    if _strategy_registry_instance is None:
        raise RuntimeError("StrategyRegistry not initialized. Call init_strategy_registry() first.")
    return _strategy_registry_instance


def init_strategy_registry(safe_paths: SafePaths) -> StrategyRegistry:
    """Initialize global StrategyRegistry instance"""
    global _strategy_registry_instance
    _strategy_registry_instance = StrategyRegistry(safe_paths)
    _strategy_registry_instance.load_strategies()
    return _strategy_registry_instance
