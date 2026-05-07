"""
Strategy loader for DedZapret Manager

Handles loading strategies from various sources including
files, directories, and upstream projects.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

from .model import Strategy, StrategyStatus, StrategyKind, RuntimeTarget, OriginalEngine, StrategyTag
from zapret_manager.core.paths import SafePaths
from zapret_manager.core.logging import get_logger, LogComponent


class StrategyLoader:
    """Loads strategies from various sources"""
    
    def __init__(self, safe_paths: SafePaths):
        self.safe_paths = safe_paths
        self.logger = get_logger("loader", LogComponent.STRATEGY)
    
    def load_all_strategies(self) -> List[Strategy]:
        """Load strategies from all available sources"""
        strategies = []
        
        # Load from strategies directory
        strategies.extend(self._load_from_directory())
        
        # Load built-in strategies
        strategies.extend(self._load_builtin_strategies())
        
        # Load from upstream repositories
        strategies.extend(self._load_from_upstream())
        
        self.logger.info(f"Loaded {len(strategies)} strategies from all sources")
        return strategies
    
    def _load_from_upstream(self) -> List[Strategy]:
        """Load strategies from upstream repositories"""
        strategies = []
        
        # Define upstream repositories
        upstream_repos = [
            "https://raw.githubusercontent.com/bol-van/zapret2/main/strategies",
            "https://raw.githubusercontent.com/StressOzz/Zapret-Manager/main/strategies", 
            "https://raw.githubusercontent.com/flowseal/zapret-discord-youtube/main/strategies",
            "https://raw.githubusercontent.com/norfolkavito-maker/Pupupu/main/strategies"
        ]
        
        for repo_url in upstream_repos:
            try:
                import requests
                
                # Get strategy files list from repository
                api_url = f"{repo_url}/strategies.json"
                response = requests.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    strategy_files = response.json()
                    
                    for file_info in strategy_files:
                        if file_info.get('name', '').endswith('.json'):
                            file_url = f"{repo_url}/{file_info['name']}"
                            file_response = requests.get(file_url, timeout=10)
                            
                            if file_response.status_code == 200:
                                try:
                                    strategy_data = file_response.json()
                                    strategy = self._parse_strategy_data(strategy_data, f"upstream:{file_info['name']}")
                                    if strategy:
                                        strategies.append(strategy)
                                        self.logger.info(f"Loaded upstream strategy: {strategy.name}")
                                except Exception as e:
                                    self.logger.error(f"Failed to parse {file_info['name']}: {e}")
                        else:
                            self.logger.warning(f"Failed to download {file_info['name']}: {file_response.status_code}")
                else:
                    self.logger.warning(f"Failed to get strategies list from {repo_url}: {response.status_code}")
                    
            except Exception as e:
                self.logger.error(f"Failed to load from {repo_url}: {e}")
        
        return strategies
    
    def _load_from_directory(self) -> List[Strategy]:
        """Load strategies from strategies directory"""
        strategies = []
        strategies_dir = self.safe_paths.get_strategies_dir()
        
        if not strategies_dir.exists():
            self.logger.info("Strategies directory not found")
            return strategies
        
        # Load JSON strategy files
        for json_file in strategies_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, dict) and 'id' in data:
                    strategy = Strategy.from_dict(data)
                    strategies.append(strategy)
                    self.logger.debug(f"Loaded strategy from {json_file}")
                elif isinstance(data, list):
                    # Multiple strategies in one file
                    for item in data:
                        if isinstance(item, dict) and 'id' in item:
                            strategy = Strategy.from_dict(item)
                            strategies.append(strategy)
                    self.logger.debug(f"Loaded {len(data)} strategies from {json_file}")
                
            except Exception as e:
                self.logger.error(f"Failed to load strategies from {json_file}", error=str(e))
        
        return strategies
    
    def _load_builtin_strategies(self) -> List[Strategy]:
        """Load built-in strategies"""
        strategies = []
        
        # Add some basic built-in strategies for testing
        strategies.append(self._create_test_strategy("test.basic", "Basic Test Strategy"))
        strategies.append(self._create_test_strategy("test.advanced", "Advanced Test Strategy"))
        strategies.append(self._create_flowseal_strategy())
        
        return strategies
    
    def _create_test_strategy(self, strategy_id: str, name: str) -> Strategy:
        """Create a test strategy"""
        from .model import Strategy
        
        return Strategy(
            id=strategy_id,
            name=name,
            description_ru=f"Тестовая стратегия: {name}",
            description_en=f"Test strategy: {name}",
            source="builtin",
            kind=StrategyKind.BASE,
            runtime_target=RuntimeTarget.WINWS2,
            original_engine=OriginalEngine.WINWS2,
            normalized_engine=RuntimeTarget.WINWS2,
            status=StrategyStatus.FLOWSEAL_WINWS2_READY,
            tags=[StrategyTag.RECOMMENDED, StrategyTag.SAFE],
            args=["--filter-udp", "--filter-tcp"],
            required_files=[],
            author="DedZapret Manager",
            version="1.0.0"
        )
    
    def _create_flowseal_strategy(self) -> Strategy:
        """Create a Flowseal-style strategy"""
        return Strategy(
            id="flowseal.general.alt5",
            name="general ALT5",
            description_ru="Базовая стратегия Flowseal ALT5",
            description_en="Flowseal ALT5 basic strategy",
            source="flowseal",
            source_ref="general/ALT5",
            kind=StrategyKind.BASE,
            runtime_target=RuntimeTarget.WINWS2,
            original_engine=OriginalEngine.BAT,
            normalized_engine=RuntimeTarget.WINWS2,
            status=StrategyStatus.FLOWSEAL_WINWS2_READY,
            tags=[StrategyTag.RECOMMENDED, StrategyTag.YOUTUBE],
            args=[
                "--filter-udp", "--filter-tcp",
                "--hostlist", "files/lists/banned.txt",
                "--dpi-desync=fake", "--dpi-desync-ttl=5"
            ],
            required_files=[
                "files/lists/banned.txt",
                "files/fake/quic_initial_www_google_com.bin"
            ],
            author="Flowseal",
            version="1.0.0"
        )
    
    def load_from_file(self, file_path: Path) -> Optional[Strategy]:
        """Load single strategy from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix == '.json':
                    data = json.load(f)
                    if isinstance(data, dict) and 'id' in data:
                        return Strategy.from_dict(data)
                elif file_path.suffix == '.bat':
                    return self._parse_bat_strategy(file_path)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load strategy from {file_path}", error=str(e))
            return None
    
    def _parse_bat_strategy(self, bat_file: Path) -> Optional[Strategy]:
        """Parse strategy from .bat file (basic implementation)"""
        try:
            with open(bat_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract winws2 command from .bat file
            winws2_match = re.search(r'winws2\.exe\s+(.+)', content, re.IGNORECASE)
            if not winws2_match:
                return None
            
            args_str = winws2_match.group(1)
            args = self._parse_command_line(args_str)
            
            # Create strategy from .bat
            strategy_id = f"imported.{bat_file.stem}"
            
            return Strategy(
                id=strategy_id,
                name=bat_file.stem,
                description_ru=f"Импортированная стратегия из {bat_file.name}",
                description_en=f"Imported strategy from {bat_file.name}",
                source="imported",
                source_ref=str(bat_file),
                kind=StrategyKind.IMPORTED,
                runtime_target=RuntimeTarget.WINWS2,
                original_engine=OriginalEngine.BAT,
                normalized_engine=RuntimeTarget.WINWS2,
                status=StrategyStatus.STRESSOZZ_IMPORTED_NEEDS_NORMALIZATION,
                args=args,
                author="Imported",
                version="1.0.0"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse .bat strategy {bat_file}", error=str(e))
            return None
    
    def _parse_command_line(self, command_line: str) -> List[str]:
        """Parse command line into arguments"""
        # Simple command line parser
        args = []
        current_arg = ""
        in_quotes = False
        
        for char in command_line:
            if char in ['"', "'"]:
                in_quotes = not in_quotes
            elif char.isspace() and not in_quotes:
                if current_arg:
                    args.append(current_arg)
                    current_arg = ""
            else:
                current_arg += char
        
        if current_arg:
            args.append(current_arg)
        
        return args
    
    def save_strategy(self, strategy: Strategy, file_path: Optional[Path] = None) -> bool:
        """Save strategy to file"""
        try:
            if file_path is None:
                strategies_dir = self.safe_paths.get_strategies_dir()
                strategies_dir.mkdir(parents=True, exist_ok=True)
                file_path = strategies_dir / f"{strategy.id}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(strategy.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved strategy {strategy.id} to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save strategy {strategy.id}", error=str(e))
            return False
    
    def load_from_directory(self, directory: Path) -> List[Strategy]:
        """Load strategies from specific directory"""
        strategies = []
        
        if not directory.exists():
            self.logger.warning(f"Directory {directory} not found")
            return strategies
        
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.json', '.bat']:
                strategy = self.load_from_file(file_path)
                if strategy:
                    strategies.append(strategy)
        
        self.logger.info(f"Loaded {len(strategies)} strategies from {directory}")
        return strategies
