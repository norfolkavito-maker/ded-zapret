"""
Strategy validator for DedZapret Manager

Validates strategy definitions, requirements, and compatibility.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import re

from .model import Strategy, StrategyStatus, RuntimeTarget, OriginalEngine, StrategyRequirement
from zapret_manager.core.paths import SafePaths
from zapret_manager.core.logging import get_logger, LogComponent


class ValidationResult:
    """Validation result"""
    
    def __init__(self):
        self.valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.suggestions: List[str] = []
    
    def add_error(self, error: str):
        """Add validation error"""
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning: str):
        """Add validation warning"""
        self.warnings.append(warning)
    
    def add_suggestion(self, suggestion: str):
        """Add validation suggestion"""
        self.suggestions.append(suggestion)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }


class StrategyValidator:
    """Validates strategies"""
    
    def __init__(self, safe_paths: SafePaths):
        self.safe_paths = safe_paths
        self.logger = get_logger("validator", LogComponent.STRATEGY)
    
    def validate_strategy(self, strategy: Strategy) -> ValidationResult:
        """Validate a strategy"""
        result = ValidationResult()
        
        # Basic validation
        self._validate_basic_info(strategy, result)
        
        # Runtime validation
        self._validate_runtime_target(strategy, result)
        
        # Arguments validation
        self._validate_arguments(strategy, result)
        
        # Requirements validation
        self._validate_requirements(strategy, result)
        
        # File validation
        self._validate_required_files(strategy, result)
        
        # Parameter validation
        self._validate_parameters(strategy, result)
        
        # Security validation
        self._validate_security(strategy, result)
        
        # Performance validation
        self._validate_performance(strategy, result)
        
        return result
    
    def _validate_basic_info(self, strategy: Strategy, result: ValidationResult):
        """Validate basic strategy information"""
        if not strategy.id or not strategy.id.strip():
            result.add_error("Strategy ID is required")
        elif not re.match(r'^[a-zA-Z0-9._-]+$', strategy.id):
            result.add_error("Strategy ID contains invalid characters")
        
        if not strategy.name or not strategy.name.strip():
            result.add_error("Strategy name is required")
        
        if not strategy.description_ru and not strategy.description_en:
            result.add_warning("Strategy should have at least one description")
        
        if not strategy.author:
            result.add_warning("Strategy should have an author")
        
        if not strategy.version:
            result.add_warning("Strategy should have a version")
    
    def _validate_runtime_target(self, strategy: Strategy, result: ValidationResult):
        """Validate runtime target"""
        if strategy.runtime_target == RuntimeTarget.UNKNOWN:
            result.add_error("Runtime target is unknown")
        
        if strategy.original_engine == OriginalEngine.UNKNOWN:
            result.add_warning("Original engine is unknown")
        
        # Check compatibility
        if strategy.runtime_target == RuntimeTarget.WINWS2:
            if strategy.original_engine in [OriginalEngine.LINUX]:
                result.add_warning("Linux engine may not be fully compatible with winws2")
        
        # Check if normalization might be needed
        if (strategy.original_engine == OriginalEngine.BAT and 
            strategy.runtime_target == RuntimeTarget.WINWS2 and
            strategy.status != StrategyStatus.FLOWSEAL_WINWS2_READY):
            result.add_suggestion("Consider normalizing BAT strategy for winws2")
    
    def _validate_arguments(self, strategy: Strategy, result: ValidationResult):
        """Validate strategy arguments"""
        if not strategy.args:
            result.add_warning("Strategy has no arguments")
            return
        
        # Check for conflicting arguments
        has_filter_tcp = any('--filter-tcp' in arg for arg in strategy.args)
        has_filter_udp = any('--filter-udp' in arg for arg in strategy.args)
        
        if not has_filter_tcp and not has_filter_udp:
            result.add_warning("Strategy doesn't specify filter type (TCP/UDP)")
        
        # Check for desync methods
        has_desync = any('--dpi-desync' in arg for arg in strategy.args)
        if not has_desync:
            result.add_warning("Strategy doesn't specify DPI desync method")
        
        # Check for hostlist
        has_hostlist = any('--hostlist' in arg for arg in strategy.args)
        if not has_hostlist:
            result.add_suggestion("Consider adding hostlist for better filtering")
        
        # Validate argument format
        for arg in strategy.args:
            if not arg.startswith('--'):
                result.add_warning(f"Argument '{arg}' doesn't start with '--'")
            
            # Check for suspicious arguments
            if any(dangerous in arg.lower() for dangerous in ['exec', 'system', 'shell']):
                result.add_error(f"Dangerous argument detected: {arg}")
    
    def _validate_requirements(self, strategy: Strategy, result: ValidationResult):
        """Validate strategy requirements"""
        for requirement in strategy.requirements:
            if not requirement.asset_type:
                result.add_error("Requirement asset type is required")
            
            if not requirement.asset_path:
                result.add_error("Requirement asset path is required")
            
            if not requirement.description:
                result.add_warning("Requirement should have description")
            
            # Check if required file exists
            if not requirement.optional:
                file_path = self.safe_paths.get_runtime_dir() / requirement.asset_path
                if not file_path.exists():
                    result.add_error(f"Required file not found: {requirement.asset_path}")
    
    def _validate_required_files(self, strategy: Strategy, result: ValidationResult):
        """Validate required files"""
        if not strategy.required_files:
            return
        
        for file_path in strategy.required_files:
            if not file_path:
                continue
            
            full_path = self.safe_paths.get_runtime_dir() / file_path
            if not full_path.exists():
                result.add_error(f"Required file not found: {file_path}")
            elif not full_path.is_file():
                result.add_error(f"Required path is not a file: {file_path}")
    
    def _validate_parameters(self, strategy: Strategy, result: ValidationResult):
        """Validate strategy parameters"""
        for param in strategy.parameters:
            if not param.name:
                result.add_error("Parameter name is required")
            
            if not param.description:
                result.add_warning("Parameter should have description")
            
            # Check parameter type
            valid_types = ['string', 'int', 'bool', 'list']
            if param.type_hint not in valid_types:
                result.add_warning(f"Unknown parameter type: {param.type_hint}")
            
            # Validate parameter value
            if param.type_hint == 'int':
                try:
                    int(param.value)
                except (ValueError, TypeError):
                    result.add_error(f"Parameter '{param.name}' should be integer")
            elif param.type_hint == 'bool':
                if not isinstance(param.value, bool):
                    result.add_error(f"Parameter '{param.name}' should be boolean")
    
    def _validate_security(self, strategy: Strategy, result: ValidationResult):
        """Validate security aspects"""
        # Check for suspicious arguments
        suspicious_patterns = [
            r'--exec\s*=',
            r'--system\s*=',
            r'--shell\s*=',
            r'\|\s*',
            r'&&\s*',
            r';\s*'
        ]
        
        for arg in strategy.args:
            for pattern in suspicious_patterns:
                if re.search(pattern, arg, re.IGNORECASE):
                    result.add_error(f"Suspicious argument detected: {arg}")
        
        # Check for file paths outside runtime directory
        for file_path in strategy.required_files:
            if '..' in file_path or file_path.startswith('/'):
                result.add_error(f"Unsafe file path: {file_path}")
        
        # Check for network connections to localhost
        for arg in strategy.args:
            if '127.0.0.1' in arg or 'localhost' in arg:
                result.add_warning(f"Argument references localhost: {arg}")
    
    def _validate_performance(self, strategy: Strategy, result: ValidationResult):
        """Validate performance aspects"""
        # Check for potentially expensive operations
        expensive_patterns = [
            '--dpi-desync=fake',
            '--dpi-desync=split',
            '--dpi-desync=disorder'
        ]
        
        expensive_count = sum(1 for arg in strategy.args 
                           if any(pattern in arg for pattern in expensive_patterns))
        
        if expensive_count > 2:
            result.add_warning("Strategy uses multiple expensive desync methods")
        
        # Check for resource-intensive settings
        for arg in strategy.args:
            if '--dpi-desync-ttl=' in arg:
                try:
                    ttl = int(arg.split('=')[1])
                    if ttl > 255:
                        result.add_error(f"Invalid TTL value: {ttl}")
                    elif ttl < 10:
                        result.add_warning(f"Very low TTL value: {ttl}")
                except (ValueError, IndexError):
                    result.add_error(f"Invalid TTL format: {arg}")
    
    def validate_strategy_compatibility(self, strategy1: Strategy, strategy2: Strategy) -> ValidationResult:
        """Validate compatibility between two strategies"""
        result = ValidationResult()
        
        # Check runtime compatibility
        if strategy1.runtime_target != strategy2.runtime_target:
            result.add_error("Strategies target different runtimes")
        
        # Check for conflicting arguments
        args1_set = set(strategy1.args)
        args2_set = set(strategy2.args)
        
        # Find conflicting arguments (same parameter with different values)
        for arg1 in args1_set:
            if '=' in arg1:
                param1 = arg1.split('=')[0]
                for arg2 in args2_set:
                    if '=' in arg2:
                        param2 = arg2.split('=')[0]
                        if param1 == param2 and arg1 != arg2:
                            result.add_warning(f"Conflicting arguments: {arg1} vs {arg2}")
        
        return result
    
    def validate_strategy_for_profile(self, strategy: Strategy, profile_requirements: Dict[str, Any]) -> ValidationResult:
        """Validate strategy for specific profile requirements"""
        result = ValidationResult()
        
        # Check required tags
        required_tags = profile_requirements.get('required_tags', [])
        for tag in required_tags:
            if not strategy.has_tag(tag):
                result.add_error(f"Strategy missing required tag: {tag}")
        
        # Check forbidden tags
        forbidden_tags = profile_requirements.get('forbidden_tags', [])
        for tag in forbidden_tags:
            if strategy.has_tag(tag):
                result.add_error(f"Strategy has forbidden tag: {tag}")
        
        # Check minimum success rate
        min_success_rate = profile_requirements.get('min_success_rate', 0.0)
        if strategy.success_rate < min_success_rate:
            result.add_error(f"Strategy success rate too low: {strategy.success_rate}% < {min_success_rate}%")
        
        # Check maximum latency
        max_latency = profile_requirements.get('max_latency_ms', float('inf'))
        if strategy.avg_latency_ms > max_latency:
            result.add_warning(f"Strategy latency too high: {strategy.avg_latency_ms}ms > {max_latency}ms")
        
        return result
    
    def get_validation_summary(self, strategies: List[Strategy]) -> Dict[str, Any]:
        """Get validation summary for multiple strategies"""
        total = len(strategies)
        valid = 0
        invalid = 0
        warnings = 0
        errors = 0
        
        status_counts = {}
        
        for strategy in strategies:
            result = self.validate_strategy(strategy)
            
            if result.valid:
                valid += 1
            else:
                invalid += 1
            
            warnings += len(result.warnings)
            errors += len(result.errors)
            
            status = strategy.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_strategies": total,
            "valid_strategies": valid,
            "invalid_strategies": invalid,
            "total_warnings": warnings,
            "total_errors": errors,
            "status_distribution": status_counts,
            "validation_rate": (valid / total * 100) if total > 0 else 0
        }
