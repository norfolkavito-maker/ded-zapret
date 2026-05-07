"""
Configuration management for DedZapret Manager

Handles YAML configuration files with validation, defaults,
and automatic migration between versions.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime

from .paths import SafePaths


@dataclass
class NetworkConfig:
    """Network configuration settings"""
    dns_mode: str = "system"  # system, doh, custom
    doh_provider: str = "cloudflare"  # cloudflare, google, custom
    custom_dns: list = field(default_factory=list)
    hosts_blocks: list = field(default_factory=list)
    quic_block: bool = False
    tcp_timestamps: str = "unchanged"  # unchanged, enable, disable


@dataclass
class RuntimeConfig:
    """Runtime configuration settings"""
    winws2_enabled: bool = True
    auto_start_runtime: bool = False
    auto_restart_on_crash: bool = True
    max_restart_attempts: int = 3
    restart_delay_seconds: int = 5
    log_level: str = "info"  # debug, info, warn, error


@dataclass
class ProxyConfig:
    """Proxy/VPN configuration settings"""
    enabled: bool = False
    engine: str = "singbox"  # singbox
    active_node_id: str = ""
    local_socks_port: int = 2080
    local_mixed_port: int = 2081
    system_proxy: bool = False
    auto_start_proxy: bool = False


@dataclass
class UIConfig:
    """User interface configuration settings"""
    language: str = "ru"  # ru, en
    console_theme: str = "default"  # default, dark, light
    tray_enabled: bool = True
    minimize_to_tray: bool = True
    start_minimized: bool = False
    show_notifications: bool = True


@dataclass
class TestingConfig:
    """Testing configuration settings"""
    auto_test_on_strategy_change: bool = False
    test_timeout_seconds: int = 30
    parallel_tests: int = 1
    save_test_results: bool = True
    baseline_test_enabled: bool = True


@dataclass
class SecurityConfig:
    """Security configuration settings"""
    mask_logs: bool = True
    audit_enabled: bool = True
    auto_backup: bool = True
    backup_retention_days: int = 30
    require_admin_for_runtime: bool = True


@dataclass
class DedZapretConfig:
    """Main configuration structure"""
    version: str = "1.0.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    network: NetworkConfig = field(default_factory=NetworkConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    testing: TestingConfig = field(default_factory=TestingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Active profile and strategy
    active_profile_id: str = "default_safe"
    active_strategy_id: str = ""
    
    # Upstream settings
    flowseal_update_url: str = "https://github.com/Flowseal/zapret-discord-youtube/releases"
    stressozz_update_url: str = "https://github.com/StressOzz/Zapret-Manager"
    
    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """Manages configuration loading, saving, and validation"""
    
    def __init__(self, safe_paths: SafePaths):
        self.safe_paths = safe_paths
        self.config_file = safe_paths.get_config_file()
        self._config: Optional[DedZapretConfig] = None
        self._defaults = DedZapretConfig()
    
    def load_config(self) -> DedZapretConfig:
        """Load configuration from file"""
        if not self.config_file.exists():
            return self._create_default_config()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                # Try YAML first, fallback to JSON if YAML not available
                content = f.read()
                try:
                    import yaml
                    data = yaml.safe_load(content)
                except ImportError:
                    # Simple YAML parser for basic configs
                    data = self._parse_simple_yaml(content)
            
            if not data:
                return self._create_default_config()
            
            # Convert dict to config object with migration
            config = self._dict_to_config(data)
            config = self._migrate_config(config)
            self._config = config
            return config
            
        except Exception as e:
            # If config is corrupted, create backup and default
            self._backup_corrupted_config()
            return self._create_default_config()
    
    def save_config(self, config: DedZapretConfig) -> bool:
        """Save configuration to file"""
        try:
            config.updated_at = datetime.now().isoformat()
            
            # Create backup before saving
            self._create_config_backup()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                # Try YAML first, fallback to JSON if YAML not available
                try:
                    import yaml
                    yaml.dump(
                        self._config_to_dict(config),
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False
                    )
                except ImportError:
                    # Save as JSON if YAML not available
                    json.dump(
                        self._config_to_dict(config),
                        f,
                        indent=2,
                        ensure_ascii=False
                    )
            
            self._config = config
            return True
            
        except Exception as e:
            return False
    
    def get_config(self) -> DedZapretConfig:
        """Get current configuration (cached)"""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update configuration with partial updates"""
        config = self.get_config()
        
        try:
            # Apply updates recursively
            self._apply_updates(config, updates)
            return self.save_config(config)
        except Exception:
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        try:
            self._create_config_backup()
            self._config = self._defaults
            return self.save_config(self._config)
        except Exception:
            return False
    
    def validate_config(self, config: DedZapretConfig) -> Dict[str, Any]:
        """Validate configuration values"""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate network config
        if config.network.dns_mode not in ["system", "doh", "custom"]:
            validation["errors"].append(f"Invalid DNS mode: {config.network.dns_mode}")
            validation["valid"] = False
        
        if config.network.tcp_timestamps not in ["unchanged", "enable", "disable"]:
            validation["errors"].append(f"Invalid TCP timestamps setting: {config.network.tcp_timestamps}")
            validation["valid"] = False
        
        # Validate runtime config
        if config.runtime.log_level not in ["debug", "info", "warn", "error"]:
            validation["errors"].append(f"Invalid log level: {config.runtime.log_level}")
            validation["valid"] = False
        
        if config.runtime.max_restart_attempts < 1:
            validation["errors"].append("Max restart attempts must be >= 1")
            validation["valid"] = False
        
        # Validate proxy config
        if config.proxy.engine != "singbox":
            validation["errors"].append(f"Unsupported proxy engine: {config.proxy.engine}")
            validation["valid"] = False
        
        if not (1024 <= config.proxy.local_socks_port <= 65535):
            validation["errors"].append("SOCKS port must be in range 1024-65535")
            validation["valid"] = False
        
        if not (1024 <= config.proxy.local_mixed_port <= 65535):
            validation["errors"].append("Mixed port must be in range 1024-65535")
            validation["valid"] = False
        
        # Validate UI config
        if config.ui.language not in ["ru", "en"]:
            validation["errors"].append(f"Unsupported language: {config.ui.language}")
            validation["valid"] = False
        
        # Warnings
        if config.proxy.enabled and not config.proxy.active_node_id:
            validation["warnings"].append("Proxy enabled but no active node selected")
        
        if config.runtime.winws2_enabled and not self.safe_paths.get_winws2_path().exists():
            validation["warnings"].append("winws2 runtime enabled but executable not found")
        
        return validation
    
    def _create_default_config(self) -> DedZapretConfig:
        """Create default configuration file"""
        config = self._defaults
        self.save_config(config)
        return config
    
    def _dict_to_config(self, data: Dict[str, Any]) -> DedZapretConfig:
        """Convert dictionary to config object"""
        # Extract nested configs
        network_data = data.get('network', {})
        runtime_data = data.get('runtime', {})
        proxy_data = data.get('proxy', {})
        ui_data = data.get('ui', {})
        testing_data = data.get('testing', {})
        security_data = data.get('security', {})
        
        return DedZapretConfig(
            version=data.get('version', '1.0.0'),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            
            network=NetworkConfig(**network_data),
            runtime=RuntimeConfig(**runtime_data),
            proxy=ProxyConfig(**proxy_data),
            ui=UIConfig(**ui_data),
            testing=TestingConfig(**testing_data),
            security=SecurityConfig(**security_data),
            
            active_profile_id=data.get('active_profile_id', 'default_safe'),
            active_strategy_id=data.get('active_strategy_id', ''),
            
            flowseal_update_url=data.get('flowseal_update_url', 'https://github.com/Flowseal/zapret-discord-youtube/releases'),
            stressozz_update_url=data.get('stressozz_update_url', 'https://github.com/StressOzz/Zapret-Manager'),
            
            custom_settings=data.get('custom_settings', {})
        )
    
    def _config_to_dict(self, config: DedZapretConfig) -> Dict[str, Any]:
        """Convert config object to dictionary"""
        return asdict(config)
    
    def _apply_updates(self, obj: Any, updates: Dict[str, Any]):
        """Apply updates recursively to config object"""
        for key, value in updates.items():
            if hasattr(obj, key):
                attr = getattr(obj, key)
                if isinstance(attr, (NetworkConfig, RuntimeConfig, ProxyConfig, UIConfig, TestingConfig, SecurityConfig)):
                    if isinstance(value, dict):
                        self._apply_updates(attr, value)
                else:
                    setattr(obj, key, value)
    
    def _migrate_config(self, config: DedZapretConfig) -> DedZapretConfig:
        """Migrate configuration between versions"""
        # Add migration logic here when version changes
        return config
    
    def _create_config_backup(self):
        """Create backup of current config"""
        if self.config_file.exists():
            backup_file = self.safe_paths.get_backup_dir() / f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            self.config_file.copy(backup_file)
    
    def _parse_simple_yaml(self, content: str) -> Dict[str, Any]:
        """Simple YAML parser for basic configurations"""
        data = {}
        current_section = data
        section_stack = [data]
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Handle indentation
            indent = len(line) - len(line.lstrip())
            line = line.lstrip()
            
            # Adjust section stack based on indentation
            while len(section_stack) > 1 and indent <= 2:
                section_stack.pop()
                current_section = section_stack[-1]
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if not value:  # New section
                    current_section[key] = {}
                    section_stack.append(current_section[key])
                    current_section = section_stack[-1]
                else:
                    # Simple value parsing
                    if value.lower() in ['true', 'yes', 'on']:
                        current_section[key] = True
                    elif value.lower() in ['false', 'no', 'off']:
                        current_section[key] = False
                    elif value.isdigit():
                        current_section[key] = int(value)
                    elif value.replace('.', '').isdigit():
                        current_section[key] = float(value)
                    else:
                        current_section[key] = value.strip('"\'')
        
        return data
    
    def _backup_corrupted_config(self):
        """Backup corrupted config file"""
        if self.config_file.exists():
            corrupted_file = self.safe_paths.get_backup_dir() / f"config_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            corrupted_file.parent.mkdir(parents=True, exist_ok=True)
            self.config_file.rename(corrupted_file)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        config = self.get_config()
        return {
            "version": config.version,
            "updated_at": config.updated_at,
            "active_profile": config.active_profile_id,
            "active_strategy": config.active_strategy_id,
            "winws2_enabled": config.runtime.winws2_enabled,
            "proxy_enabled": config.proxy.enabled,
            "language": config.ui.language,
            "dns_mode": config.network.dns_mode,
            "tray_enabled": config.ui.tray_enabled
        }


# Global instance for singleton pattern
_config_manager_instance: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global ConfigManager instance"""
    global _config_manager_instance
    if _config_manager_instance is None:
        raise RuntimeError("ConfigManager not initialized. Call init_config_manager() first.")
    return _config_manager_instance


def init_config_manager(safe_paths: SafePaths) -> ConfigManager:
    """Initialize global ConfigManager instance"""
    global _config_manager_instance
    _config_manager_instance = ConfigManager(safe_paths)
    return _config_manager_instance
