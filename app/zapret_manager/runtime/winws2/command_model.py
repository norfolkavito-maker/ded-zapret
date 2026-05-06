"""
winws2 command model for DedZapret Manager

Builds and validates winws2 command lines from strategies
with proper argument handling and security checks.
"""

import os
import shlex
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from ...core.paths import get_safe_paths
from ...core.security import DataMasker
from ...core.audit import get_audit_logger
from ...strategies.model import Strategy, StrategyArgument

logger = logging.getLogger(__name__)

@dataclass
class CommandBuildResult:
    """Result of command building"""
    success: bool
    command: List[str]
    errors: List[str]
    warnings: List[str]
    resolved_files: Dict[str, str]
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.resolved_files is None:
            self.resolved_files = {}

class Winws2CommandBuilder:
    """Builds winws2 commands from strategies"""
    
    def __init__(self, safe_paths=None):
        """
        Initialize command builder
        
        Args:
            safe_paths: SafePaths instance. If None, uses default.
        """
        self.safe_paths = safe_paths or get_safe_paths()
        self.audit_logger = get_audit_logger()
        self.masker = DataMasker()
        
        # winws2 executable path
        self.winws2_path = None
        
        # Argument mappings and transformations
        self.arg_mappings = {
            # Basic arguments
            'hostlist': '--hostlist',
            'ipset': '--ipset',
            'autohostlist': '--autohostlist',
            'exclude': '--exclude',
            'filter-tcp': '--filter-tcp',
            'filter-udp': '--filter-udp',
            'port': '--port',
            'dport': '--dport',
            'new': '--new',
            'ip-from': '--ip-from',
            'ip-to': '--ip-to',
            'debug': '--debug',
            
            # Fake packet arguments
            'fake-tls': '--fake-tls',
            'fake-quic': '--fake-quic',
            'fake-udp': '--fake-udp',
            'tls-rec': '--tls-rec',
            'tls-pad': '--tls-pad',
            'tls-sni': '--tls-sni',
            
            # Desync arguments
            'split-pos': '--split-pos',
            'split-http': '--split-http',
            'method': '--method',
            'oob': '--oob',
            'oob-data': '--oob-data',
            'oob-fa': '--oob-fa',
            'desync': '--desync',
            'desync-faulthdr': '--desync-faulthdr',
            'desync-retrans': '--desync-retrans',
            'desync-repeats': '--desync-repeats',
            'desync-ttl': '--desync-ttl',
            'desync-ipid': '--desync-ipid',
            'desync-fooling': '--desync-fooling',
            'desync-fake': '--desync-fake',
            'desync-fake-tls': '--desync-fake-tls'
        }
        
        # File argument types
        self.file_args = {
            'hostlist', 'ipset', 'fake-tls', 'fake-quic', 'fake-udp'
        }
        
        # Boolean flag arguments
        self.flag_args = {
            'autohostlist', 'debug', 'new', 'filter-tcp', 'filter-udp'
        }
    
    def set_winws2_path(self, winws2_path: Path) -> None:
        """
        Set winws2 executable path
        
        Args:
            winws2_path: Path to winws2 executable
        """
        self.winws2_path = winws2_path
    
    def build_command(self, strategy: Strategy, 
                   extra_args: Optional[List[str]] = None) -> CommandBuildResult:
        """
        Build winws2 command from strategy
        
        Args:
            strategy: Strategy to build command for
            extra_args: Additional arguments to include
            
        Returns:
            CommandBuildResult with built command
        """
        result = CommandBuildResult(
            success=False,
            command=[],
            errors=[],
            warnings=[],
            resolved_files={}
        )
        
        try:
            # Validate winws2 path
            if not self.winws2_path or not self.winws2_path.exists():
                result.errors.append("winws2 executable not found or not set")
                return result
            
            # Start command with executable
            command = [str(self.winws2_path)]
            
            # Process strategy arguments
            for arg in strategy.args:
                arg_result = self._process_argument(arg, strategy)
                
                if not arg_result.success:
                    result.errors.extend(arg_result.errors)
                    continue
                
                command.extend(arg_result.args)
                result.warnings.extend(arg_result.warnings)
                result.resolved_files.update(arg_result.resolved_files)
            
            # Add extra arguments
            if extra_args:
                for extra_arg in extra_args:
                    arg_result = self._process_extra_argument(extra_arg)
                    
                    if not arg_result.success:
                        result.errors.extend(arg_result.errors)
                        continue
                    
                    command.extend(arg_result.args)
                    result.warnings.extend(arg_result.warnings)
            
            # Validate final command
            validation_result = self._validate_command(command, strategy)
            result.errors.extend(validation_result.errors)
            result.warnings.extend(validation_result.warnings)
            
            if not result.errors:
                result.success = True
            
            result.command = command
            
            # Log command building
            self.audit_logger.log_action(
                action="command_built",
                component="runtime_winws2",
                success=result.success,
                message=f"Command built for strategy: {strategy.name}",
                strategy_id=strategy.id,
                details={
                    "strategy_name": strategy.name,
                    "command_length": len(command),
                    "resolved_files": len(result.resolved_files),
                    "errors": len(result.errors),
                    "warnings": len(result.warnings)
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to build command for strategy {strategy.id}: {e}")
            result.errors.append(f"Command building failed: {e}")
            return result
    
    def _process_argument(self, arg: StrategyArgument, strategy: Strategy) -> CommandBuildResult:
        """
        Process a single strategy argument
        
        Args:
            arg: Strategy argument to process
            strategy: Parent strategy
            
        Returns:
            CommandBuildResult for this argument
        """
        result = CommandBuildResult(
            success=False,
            command=[],
            errors=[],
            warnings=[],
            resolved_files={}
        )
        
        try:
            # Get argument name
            arg_name = arg.name.lower()
            
            # Check if argument is supported
            if arg_name not in self.arg_mappings:
                result.errors.append(f"Unsupported argument: {arg.name}")
                return result
            
            # Get mapped argument name
            mapped_name = self.arg_mappings[arg_name]
            
            # Handle different value types
            if isinstance(arg.value, bool):
                # Boolean flag
                if arg.value:
                    result.command.append(mapped_name)
                else:
                    # Skip if False (unless required and no default)
                    if arg.required:
                        result.warnings.append(f"Required boolean argument {arg.name} is False")
            
            elif isinstance(arg.value, list):
                # List argument - add each value
                for value in arg.value:
                    if arg_name in self.file_args:
                        # Resolve file path
                        resolved_path = self._resolve_file_path(value, strategy)
                        if resolved_path:
                            result.command.extend([mapped_name, resolved_path])
                            result.resolved_files[arg.name] = resolved_path
                        else:
                            result.errors.append(f"File not found for argument {arg.name}: {value}")
                    else:
                        result.command.extend([mapped_name, str(value)])
            
            elif isinstance(arg.value, (str, int, float)):
                # Single value argument
                if arg_name in self.file_args:
                    # Resolve file path
                    resolved_path = self._resolve_file_path(str(arg.value), strategy)
                    if resolved_path:
                        result.command.extend([mapped_name, resolved_path])
                        result.resolved_files[arg.name] = resolved_path
                    else:
                        result.errors.append(f"File not found for argument {arg.name}: {arg.value}")
                else:
                    result.command.extend([mapped_name, str(arg.value)])
            
            else:
                result.errors.append(f"Unsupported argument value type for {arg.name}: {type(arg.value)}")
                return result
            
            result.success = True
            
        except Exception as e:
            result.errors.append(f"Failed to process argument {arg.name}: {e}")
        
        return result
    
    def _process_extra_argument(self, extra_arg: str) -> CommandBuildResult:
        """
        Process an extra argument string
        
        Args:
            extra_arg: Extra argument string
            
        Returns:
            CommandBuildResult for this argument
        """
        result = CommandBuildResult(
            success=False,
            command=[],
            errors=[],
            warnings=[],
            resolved_files={}
        )
        
        try:
            # Parse extra argument
            if extra_arg.startswith('--'):
                # Flag argument
                result.command.append(extra_arg)
            elif '=' in extra_arg:
                # Key-value argument
                key, value = extra_arg.split('=', 1)
                if key.startswith('--'):
                    key = key[2:]
                
                # Check if it's a file argument
                if key in self.file_args:
                    resolved_path = self._resolve_file_path(value, None)
                    if resolved_path:
                        result.command.extend([f"--{key}", resolved_path])
                        result.resolved_files[key] = resolved_path
                    else:
                        result.errors.append(f"File not found for extra argument {key}: {value}")
                else:
                    result.command.extend([f"--{key}", value])
            else:
                # Simple value argument
                result.command.append(extra_arg)
            
            result.success = True
            
        except Exception as e:
            result.errors.append(f"Failed to process extra argument {extra_arg}: {e}")
        
        return result
    
    def _resolve_file_path(self, file_path: str, strategy: Optional[Strategy]) -> Optional[str]:
        """
        Resolve file path to absolute path
        
        Args:
            file_path: File path to resolve
            strategy: Strategy for context
            
        Returns:
            Resolved absolute path or None if not found
        """
        try:
            # If absolute path, use as-is
            if os.path.isabs(file_path):
                abs_path = Path(file_path)
            else:
                # Resolve relative to runtime directory
                abs_path = self.safe_paths.get_zapret_runtime_path(file_path)
            
            # Check if file exists
            if abs_path.exists() and abs_path.is_file():
                return str(abs_path)
            
            # Try common locations
            search_locations = [
                self.safe_paths.get_zapret_runtime_path("lists", file_path),
                self.safe_paths.get_zapret_runtime_path("fake", file_path),
                self.safe_paths.get_zapret_runtime_path("bin", file_path),
                self.safe_paths.get_zapret_runtime_path(file_path)
            ]
            
            for location in search_locations:
                if location.exists() and location.is_file():
                    logger.debug(f"Resolved file {file_path} to {location}")
                    return str(location)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to resolve file path {file_path}: {e}")
            return None
    
    def _validate_command(self, command: List[str], strategy: Strategy) -> CommandBuildResult:
        """
        Validate built command for security and correctness
        
        Args:
            command: Command to validate
            strategy: Strategy for context
            
        Returns:
            CommandBuildResult with validation results
        """
        result = CommandBuildResult(
            success=True,
            command=[],
            errors=[],
            warnings=[],
            resolved_files={}
        )
        
        try:
            # Check for dangerous patterns
            dangerous_patterns = [
                '|', '&', ';', '<', '>', '`', '$', '(', ')', 
                '&&', '||', '>>', '>', '<'
            ]
            
            for i, arg in enumerate(command):
                if i == 0:  # Skip executable
                    continue
                
                # Check for dangerous characters
                for pattern in dangerous_patterns:
                    if pattern in arg:
                        result.errors.append(f"Dangerous character '{pattern}' in argument: {arg}")
                
                # Check for command injection attempts
                if any(keyword in arg.lower() for keyword in ['powershell', 'cmd.exe', 'wscript.exe', 'cscript.exe']):
                    result.errors.append(f"Command injection attempt detected in argument: {arg}")
            
            # Validate file arguments
            file_args_found = 0
            for arg in command:
                if arg.startswith('--') and len(command) > command.index(arg) + 1:
                    next_arg = command[command.index(arg) + 1]
                    if os.path.exists(next_arg):
                        file_args_found += 1
            
            # Check for required arguments
            required_args = {'hostlist', 'ipset'}  # At least one should be present
            has_required = any(
                any(arg.startswith(f"--{req}") for arg in command) 
                for req in required_args
            )
            
            if not has_required:
                result.warnings.append("No hostlist or ipset argument specified")
            
            # Check for conflicting arguments
            conflicting_pairs = [
                ('--filter-tcp', '--filter-udp'),
                ('--desync-fake', '--desync-fake-tls')
            ]
            
            for arg1, arg2 in conflicting_pairs:
                if arg1 in command and arg2 in command:
                    result.warnings.append(f"Conflicting arguments: {arg1} and {arg2}")
            
            # Check command length
            if len(command) > 50:
                result.warnings.append(f"Command is very long: {len(command)} arguments")
            
            # Check for debug in production
            if '--debug' in command:
                result.warnings.append("Debug mode enabled")
            
        except Exception as e:
            result.errors.append(f"Command validation failed: {e}")
            result.success = False
        
        return result
    
    def get_command_string(self, command: List[str], mask_sensitive: bool = True) -> str:
        """
        Convert command list to string
        
        Args:
            command: Command list
            mask_sensitive: Whether to mask sensitive data
            
        Returns:
            Command string
        """
        try:
            if mask_sensitive:
                # Mask sensitive arguments
                masked_command = []
                for i, arg in enumerate(command):
                    if i == 0:  # Skip executable
                        masked_command.append(arg)
                        continue
                    
                    # Mask file paths
                    if os.path.exists(arg) and os.path.isfile(arg):
                        masked_command.append(self.masker.mask_path(arg))
                    else:
                        masked_command.append(self.masker.mask_string(arg))
                
                return ' '.join(shlex.quote(arg) for arg in masked_command)
            else:
                return ' '.join(shlex.quote(arg) for arg in command)
                
        except Exception as e:
            logger.error(f"Failed to convert command to string: {e}")
            return ' '.join(command)
    
    def simulate_command(self, strategy: Strategy, dry_run: bool = True) -> Dict[str, Any]:
        """
        Simulate command execution without actually running
        
        Args:
            strategy: Strategy to simulate
            dry_run: Whether to add --dry-run flag
            
        Returns:
            Simulation results
        """
        build_result = self.build_command(strategy)
        
        if not build_result.success:
            return {
                "success": False,
                "errors": build_result.errors,
                "warnings": build_result.warnings
            }
        
        command = build_result.command.copy()
        
        if dry_run:
            command.append('--dry-run')
        
        return {
            "success": True,
            "command": command,
            "command_string": self.get_command_string(command, mask_sensitive=False),
            "masked_command_string": self.get_command_string(command, mask_sensitive=True),
            "resolved_files": build_result.resolved_files,
            "warnings": build_result.warnings,
            "executable": str(self.winws2_path) if self.winws2_path else None
        }
