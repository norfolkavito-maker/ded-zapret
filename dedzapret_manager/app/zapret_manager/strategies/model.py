"""
Strategy models for DedZapret Manager

Defines data structures for strategies, their status,
and related enumerations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class StrategyStatus(Enum):
    """Strategy status enumeration"""
    FLOWSEAL_WINWS2_READY = "flowseal_winws2_ready"
    STRESSOZZ_IMPORTED_NEEDS_NORMALIZATION = "stressozz_imported_needs_normalization"
    CUSTOM_NEEDS_VALIDATION = "custom_needs_validation"
    GENERATED_WINWS2_READY = "generated_winws2_ready"
    LEGACY_WINWS_NEEDS_CONVERSION = "legacy_winws_needs_conversion"
    INVALID_MISSING_ASSETS = "invalid_missing_assets"
    INVALID_UNSUPPORTED_ENGINE = "invalid_unsupported_engine"
    UNKNOWN_NEEDS_VERIFICATION = "unknown_needs_verification"
    BROKEN = "broken"


class RuntimeTarget(Enum):
    """Runtime target enumeration"""
    WINWS = "winws"
    WINWS2 = "winws2"
    NFQWS = "nfqws"
    TPWS = "tpws"
    UNKNOWN = "unknown"


class OriginalEngine(Enum):
    """Original engine enumeration"""
    BAT = "bat"
    WINWS = "winws"
    WINWS2 = "winws2"
    LINUX = "linux"
    UNKNOWN = "unknown"


class StrategyKind(Enum):
    """Strategy kind enumeration"""
    BASE = "base"
    LAYER = "layer"
    GENERATED = "generated"
    CUSTOM = "custom"
    IMPORTED = "imported"


class StrategyTag(Enum):
    """Strategy tag enumeration"""
    DISCORD = "discord"
    YOUTUBE = "youtube"
    GAMES = "games"
    RKN = "rkn"
    WSSIZE = "wssize"
    RECOMMENDED = "recommended"
    EXPERIMENTAL = "experimental"
    LEGACY = "legacy"
    SAFE = "safe"
    AGGRESSIVE = "aggressive"


@dataclass
class StrategyRequirement:
    """Strategy requirement"""
    asset_type: str  # fake, list, binary
    asset_path: str
    description: str
    optional: bool = False


@dataclass
class StrategyParameter:
    """Strategy parameter"""
    name: str
    value: Any
    description: str
    type_hint: str = "string"  # string, int, bool, list
    required: bool = True


@dataclass
class StrategyTestResult:
    """Strategy test result"""
    strategy_id: str
    test_time: str
    success_rate: float
    domains_tested: int
    domains_passed: int
    latency_ms: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Strategy:
    """Strategy model"""
    # Basic identification
    id: str
    name: str
    description_ru: str = ""
    description_en: str = ""
    
    # Source information
    source: str = "custom"  # flowseal, stressozz, custom, generated
    source_ref: str = ""  # commit/tag/date
    author: str = ""
    version: str = "1.0.0"
    
    # Classification
    kind: StrategyKind = StrategyKind.BASE
    runtime_target: RuntimeTarget = RuntimeTarget.WINWS2
    original_engine: OriginalEngine = OriginalEngine.WINWS2
    normalized_engine: RuntimeTarget = RuntimeTarget.WINWS2
    
    # Status and validation
    status: StrategyStatus = StrategyStatus.CUSTOM_NEEDS_VALIDATION
    tags: List[StrategyTag] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Strategy definition
    args: List[str] = field(default_factory=list)
    required_files: List[str] = field(default_factory=list)
    requirements: List[StrategyRequirement] = field(default_factory=list)
    parameters: List[StrategyParameter] = field(default_factory=list)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_tested: Optional[str] = None
    test_results: List[StrategyTestResult] = field(default_factory=list)
    
    # Performance metrics
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    usage_count: int = 0
    rating: float = 0.0  # 0-5 stars
    
    # Custom data
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """Check if strategy is valid"""
        return (self.status not in [
            StrategyStatus.INVALID_MISSING_ASSETS,
            StrategyStatus.INVALID_UNSUPPORTED_ENGINE,
            StrategyStatus.BROKEN
        ])
    
    def is_ready(self) -> bool:
        """Check if strategy is ready for use"""
        return self.status in [
            StrategyStatus.FLOWSEAL_WINWS2_READY,
            StrategyStatus.GENERATED_WINWS2_READY
        ]
    
    def has_tag(self, tag: StrategyTag) -> bool:
        """Check if strategy has specific tag"""
        return tag in self.tags
    
    def get_tags_as_strings(self) -> List[str]:
        """Get tags as string list"""
        return [tag.value for tag in self.tags]
    
    def add_tag(self, tag: StrategyTag):
        """Add tag to strategy"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now().isoformat()
    
    def remove_tag(self, tag: StrategyTag):
        """Remove tag from strategy"""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now().isoformat()
    
    def add_warning(self, warning: str):
        """Add warning to strategy"""
        if warning not in self.warnings:
            self.warnings.append(warning)
            self.updated_at = datetime.now().isoformat()
    
    def add_error(self, error: str):
        """Add error to strategy"""
        if error not in self.errors:
            self.errors.append(error)
            self.updated_at = datetime.now().isoformat()
    
    def clear_warnings(self):
        """Clear all warnings"""
        self.warnings.clear()
        self.updated_at = datetime.now().isoformat()
    
    def clear_errors(self):
        """Clear all errors"""
        self.errors.clear()
        self.updated_at = datetime.now().isoformat()
    
    def update_test_result(self, result: StrategyTestResult):
        """Update strategy with test result"""
        self.test_results.append(result)
        self.last_tested = result.test_time
        self.success_rate = result.success_rate
        self.avg_latency_ms = result.latency_ms
        self.updated_at = datetime.now().isoformat()
        
        # Keep only last 10 test results
        if len(self.test_results) > 10:
            self.test_results = self.test_results[-10:]
    
    def get_latest_test_result(self) -> Optional[StrategyTestResult]:
        """Get latest test result"""
        return self.test_results[-1] if self.test_results else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description_ru": self.description_ru,
            "description_en": self.description_en,
            "source": self.source,
            "source_ref": self.source_ref,
            "author": self.author,
            "version": self.version,
            "kind": self.kind.value,
            "runtime_target": self.runtime_target.value,
            "original_engine": self.original_engine.value,
            "normalized_engine": self.normalized_engine.value,
            "status": self.status.value,
            "tags": [tag.value for tag in self.tags],
            "warnings": self.warnings,
            "errors": self.errors,
            "args": self.args,
            "required_files": self.required_files,
            "requirements": [
                {
                    "asset_type": req.asset_type,
                    "asset_path": req.asset_path,
                    "description": req.description,
                    "optional": req.optional
                }
                for req in self.requirements
            ],
            "parameters": [
                {
                    "name": param.name,
                    "value": param.value,
                    "description": param.description,
                    "type_hint": param.type_hint,
                    "required": param.required
                }
                for param in self.parameters
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_tested": self.last_tested,
            "test_results": [
                {
                    "strategy_id": result.strategy_id,
                    "test_time": result.test_time,
                    "success_rate": result.success_rate,
                    "domains_tested": result.domains_tested,
                    "domains_passed": result.domains_passed,
                    "latency_ms": result.latency_ms,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "details": result.details
                }
                for result in self.test_results
            ],
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "usage_count": self.usage_count,
            "rating": self.rating,
            "custom_data": self.custom_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Strategy':
        """Create strategy from dictionary"""
        # Parse requirements
        requirements = []
        for req_data in data.get('requirements', []):
            requirements.append(StrategyRequirement(
                asset_type=req_data['asset_type'],
                asset_path=req_data['asset_path'],
                description=req_data['description'],
                optional=req_data.get('optional', False)
            ))
        
        # Parse parameters
        parameters = []
        for param_data in data.get('parameters', []):
            parameters.append(StrategyParameter(
                name=param_data['name'],
                value=param_data['value'],
                description=param_data['description'],
                type_hint=param_data.get('type_hint', 'string'),
                required=param_data.get('required', True)
            ))
        
        # Parse test results
        test_results = []
        for result_data in data.get('test_results', []):
            test_results.append(StrategyTestResult(
                strategy_id=result_data['strategy_id'],
                test_time=result_data['test_time'],
                success_rate=result_data['success_rate'],
                domains_tested=result_data['domains_tested'],
                domains_passed=result_data['domains_passed'],
                latency_ms=result_data['latency_ms'],
                errors=result_data.get('errors', []),
                warnings=result_data.get('warnings', []),
                details=result_data.get('details', {})
            ))
        
        # Parse tags
        tags = [StrategyTag(tag) for tag in data.get('tags', [])]
        
        return cls(
            id=data['id'],
            name=data['name'],
            description_ru=data.get('description_ru', ''),
            description_en=data.get('description_en', ''),
            source=data.get('source', 'custom'),
            source_ref=data.get('source_ref', ''),
            author=data.get('author', ''),
            version=data.get('version', '1.0.0'),
            kind=StrategyKind(data.get('kind', 'base')),
            runtime_target=RuntimeTarget(data.get('runtime_target', 'winws2')),
            original_engine=OriginalEngine(data.get('original_engine', 'winws2')),
            normalized_engine=RuntimeTarget(data.get('normalized_engine', 'winws2')),
            status=StrategyStatus(data.get('status', 'custom_needs_validation')),
            tags=tags,
            warnings=data.get('warnings', []),
            errors=data.get('errors', []),
            args=data.get('args', []),
            required_files=data.get('required_files', []),
            requirements=requirements,
            parameters=parameters,
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            last_tested=data.get('last_tested'),
            test_results=test_results,
            success_rate=data.get('success_rate', 0.0),
            avg_latency_ms=data.get('avg_latency_ms', 0.0),
            usage_count=data.get('usage_count', 0),
            rating=data.get('rating', 0.0),
            custom_data=data.get('custom_data', {})
        )
