"""
Security module for DedZapret Manager

Handles data masking, security validation, and sensitive data protection.
"""

import re
import hashlib
import secrets
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json
import base64
from urllib.parse import urlparse, parse_qs

from .logging import get_logger, LogComponent


class DataMasker:
    """Masks sensitive data in logs and exports"""
    
    def __init__(self):
        self.logger = get_logger("security", LogComponent.AUDIT)
        self.sensitive_patterns = self._init_sensitive_patterns()
        self.mask_char = "*"
        self.min_visible_chars = 2
        self.max_mask_length = 20
    
    def _init_sensitive_patterns(self) -> List[Dict[str, Any]]:
        """Initialize patterns for sensitive data detection"""
        return [
            # URLs with authentication
            {
                "name": "auth_url",
                "pattern": re.compile(r'([a-zA-Z]+://[^:]+:[^@]+@[^/\s]+)', re.IGNORECASE),
                "mask_func": self._mask_auth_url
            },
            # Proxy URLs (vless, vmess, trojan, ss)
            {
                "name": "proxy_url",
                "pattern": re.compile(r'((vless|vmess|trojan|ss)://[^\s]+)', re.IGNORECASE),
                "mask_func": self._mask_proxy_url
            },
            # IP addresses
            {
                "name": "ip_address",
                "pattern": re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
                "mask_func": self._mask_ip_address
            },
            # Email addresses
            {
                "name": "email",
                "pattern": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                "mask_func": self._mask_email
            },
            # Passwords in JSON/key-value format
            {
                "name": "password_field",
                "pattern": re.compile(r'(["\']?password["\']?\s*[:=]\s*["\']?)([^"\'\s,}]+)', re.IGNORECASE),
                "mask_func": self._mask_password_field
            },
            # API keys
            {
                "name": "api_key",
                "pattern": re.compile(r'(["\']?(?:api[_-]?key|token|secret)["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9+/=_-]{16,})["\']?', re.IGNORECASE),
                "mask_func": self._mask_api_key
            },
            # UUIDs (except for our own event IDs)
            {
                "name": "uuid",
                "pattern": re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE),
                "mask_func": self._mask_uuid
            },
            # File paths with user data
            {
                "name": "user_path",
                "pattern": re.compile(r'([A-Za-z]:[/\\]|/home/[^/]+|/Users/[^/]+)([/\\][^\s]*)'),
                "mask_func": self._mask_user_path
            }
        ]
    
    def mask_data(self, data: Union[str, Dict, Any]) -> Union[str, Dict, Any]:
        """Mask sensitive data in various data types"""
        if isinstance(data, str):
            return self._mask_string(data)
        elif isinstance(data, dict):
            return self._mask_dict(data)
        elif isinstance(data, list):
            return [self.mask_data(item) for item in data]
        else:
            return data
    
    def _mask_string(self, text: str) -> str:
        """Mask sensitive data in string"""
        if not text or not isinstance(text, str):
            return text
        
        masked_text = text
        
        for pattern_info in self.sensitive_patterns:
            try:
                masked_text = pattern_info["pattern"].sub(
                    lambda match: pattern_info["mask_func"](match.group(0), match),
                    masked_text
                )
            except Exception as e:
                self.logger.warning(f"Failed to apply pattern {pattern_info['name']}", error=str(e))
        
        return masked_text
    
    def _mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in dictionary"""
        masked_dict = {}
        
        for key, value in data.items():
            # Check if key suggests sensitive data
            if self._is_sensitive_key(key):
                masked_dict[key] = self._mask_value(str(value))
            else:
                masked_dict[key] = self.mask_data(value)
        
        return masked_dict
    
    def _is_sensitive_key(self, key: str) -> bool:
        """Check if dictionary key suggests sensitive data"""
        sensitive_keywords = [
            'password', 'passwd', 'pwd', 'secret', 'token', 'key', 'auth',
            'credential', 'private', 'confidential', 'sensitive'
        ]
        
        key_lower = key.lower()
        return any(keyword in key_lower for keyword in sensitive_keywords)
    
    def _mask_value(self, value: str) -> str:
        """Mask a sensitive value"""
        if not value or len(value) <= 4:
            return self.mask_char * len(value) if value else ""
        
        visible_chars = min(self.min_visible_chars, len(value) // 4)
        total_chars = len(value)
        
        if total_chars > self.max_mask_length:
            # Show first few chars and mask the rest
            visible = value[:visible_chars]
            masked = self.mask_char * (self.max_mask_length - visible_chars) + "..."
        else:
            # Show first and last few chars
            visible_start = value[:visible_chars]
            visible_end = value[-visible_chars:] if visible_chars > 0 else ""
            masked_middle = self.mask_char * (total_chars - visible_chars * 2)
            visible = visible_start + masked_middle + visible_end
        
        return visible
    
    def _mask_auth_url(self, match: str, groups) -> str:
        """Mask authentication in URL"""
        try:
            url = urlparse(match)
            if url.username and url.password:
                # Mask username and password
                username = self._mask_value(url.username)
                password = self._mask_value(url.password)
                
                masked_netloc = f"{username}:{password}@{url.hostname}"
                if url.port:
                    masked_netloc += f":{url.port}"
                
                return f"{url.scheme}://{masked_netloc}"
            return match
        except Exception:
            return self.mask_char * len(match)
    
    def _mask_proxy_url(self, match: str, groups) -> str:
        """Mask proxy URL (vless, vmess, trojan, ss)"""
        try:
            # For proxy URLs, mask the entire payload but keep the protocol
            protocol = groups[1].lower() if groups else "unknown"
            payload = match.split('://', 1)[1] if '://' in match else match
            
            # Generate a hash for identification (first 8 chars)
            payload_hash = hashlib.sha256(payload.encode()).hexdigest()[:8]
            masked_payload = self.mask_char * (len(payload) - 8) + payload_hash
            
            return f"{protocol}://{masked_payload}"
        except Exception:
            return self.mask_char * len(match)
    
    def _mask_ip_address(self, match: str, groups) -> str:
        """Mask IP address (show first octet, mask rest)"""
        try:
            parts = match.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{self.mask_char * 3}.{self.mask_char * 3}.{self.mask_char * 3}"
            return self.mask_char * len(match)
        except Exception:
            return self.mask_char * len(match)
    
    def _mask_email(self, match: str, groups) -> str:
        """Mask email address"""
        try:
            local, domain = match.split('@', 1)
            if len(local) > 2:
                masked_local = local[0] + self.mask_char * (len(local) - 2) + local[-1]
            else:
                masked_local = self.mask_char * len(local)
            
            domain_parts = domain.split('.')
            if len(domain_parts) >= 2:
                masked_domain = self.mask_char * len(domain_parts[0]) + '.' + '.'.join(domain_parts[1:])
            else:
                masked_domain = self.mask_char * len(domain)
            
            return f"{masked_local}@{masked_domain}"
        except Exception:
            return self.mask_char * len(match)
    
    def _mask_password_field(self, match: str, groups) -> str:
        """Mask password field in key-value format"""
        try:
            field_name = groups[1] if len(groups) > 1 else ""
            password_value = groups[2] if len(groups) > 2 else ""
            masked_password = self._mask_value(password_value)
            return f"{field_name}{masked_password}"
        except Exception:
            return self.mask_char * len(match)
    
    def _mask_api_key(self, match: str, groups) -> str:
        """Mask API key"""
        try:
            field_name = groups[1] if len(groups) > 1 else ""
            key_value = groups[2] if len(groups) > 2 else ""
            masked_key = self._mask_value(key_value)
            return f"{field_name}{masked_key}"
        except Exception:
            return self.mask_char * len(match)
    
    def _mask_uuid(self, match: str, groups) -> str:
        """Mask UUID (keep first segment for identification)"""
        try:
            parts = match.split('-')
            if len(parts) == 5:
                return f"{parts[0]}-{self.mask_char * 8}-{self.mask_char * 4}-{self.mask_char * 4}-{self.mask_char * 12}"
            return self.mask_char * len(match)
        except Exception:
            return self.mask_char * len(match)
    
    def _mask_user_path(self, match: str, groups) -> str:
        """Mask user-specific paths"""
        try:
            path_prefix = groups[1] if len(groups) > 1 else ""
            path_suffix = groups[2] if len(groups) > 2 else ""
            
            # Mask username in path
            if '/Users/' in path_prefix or '/home/' in path_prefix:
                masked_prefix = path_prefix.split('/')[0] + '/' + path_prefix.split('/')[1] + '/' + self.mask_char * 8
            else:
                masked_prefix = path_prefix
            
            return f"{masked_prefix}{path_suffix}"
        except Exception:
            return self.mask_char * len(match)
    
    def create_safe_export(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a safe version of data for export"""
        return {
            "masked_data": self.mask_data(data),
            "masking_info": {
                "timestamp": self._get_timestamp(),
                "patterns_applied": [p["name"] for p in self.sensitive_patterns],
                "mask_char": self.mask_char,
                "note": "Sensitive data has been masked for security"
            }
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()


class SecurityValidator:
    """Validates security-related operations"""
    
    def __init__(self):
        self.logger = get_logger("security", LogComponent.AUDIT)
    
    def validate_file_path(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Validate file path for security"""
        result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        try:
            path = Path(file_path)
            
            # Check for path traversal attempts
            if '..' in str(path):
                result["errors"].append("Path traversal detected")
                result["valid"] = False
            
            # Check for suspicious file extensions
            suspicious_extensions = ['.exe', '.bat', '.cmd', '.scr', '.vbs', '.js', '.jar']
            if path.suffix.lower() in suspicious_extensions:
                result["warnings"].append(f"Suspicious file extension: {path.suffix}")
            
            # Check if path is within expected directories
            # This would need to be configured based on application requirements
            
            # Check for very long paths (Windows limitation)
            if len(str(path)) > 260:
                result["warnings"].append("Path length exceeds Windows limit")
            
        except Exception as e:
            result["errors"].append(f"Path validation error: {str(e)}")
            result["valid"] = False
        
        return result
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL for security"""
        result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                result["errors"].append(f"Unsupported URL scheme: {parsed.scheme}")
                result["valid"] = False
            
            # Check for localhost/internal IPs
            if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
                result["warnings"].append("URL points to localhost")
            
            # Check for non-standard ports
            if parsed.port and parsed.port not in [80, 443, 8080, 8443]:
                result["warnings"].append(f"Non-standard port: {parsed.port}")
            
            # Check for suspicious query parameters
            suspicious_params = ['exec', 'cmd', 'eval', 'system']
            query_params = parse_qs(parsed.query)
            for param in query_params:
                if any(sus in param.lower() for sus in suspicious_params):
                    result["warnings"].append(f"Suspicious query parameter: {param}")
            
        except Exception as e:
            result["errors"].append(f"URL validation error: {str(e)}")
            result["valid"] = False
        
        return result
    
    def validate_command(self, command: Union[str, List[str]]) -> Dict[str, Any]:
        """Validate command for security"""
        result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        try:
            if isinstance(command, str):
                cmd_parts = command.split()
            else:
                cmd_parts = command
            
            if not cmd_parts:
                result["errors"].append("Empty command")
                result["valid"] = False
                return result
            
            # Check for dangerous commands
            dangerous_commands = [
                'format', 'del', 'rmdir', 'rd', 'shutdown', 'reboot',
                'net user', 'net localgroup', 'reg add', 'reg delete',
                'powershell', 'cmd.exe', 'wscript', 'cscript'
            ]
            
            cmd_string = ' '.join(cmd_parts).lower()
            for dangerous in dangerous_commands:
                if dangerous in cmd_string:
                    result["errors"].append(f"Dangerous command detected: {dangerous}")
                    result["valid"] = False
            
            # Check for suspicious arguments
            suspicious_args = ['>', '>>', '|', '&', '&&', '||', '`', '$()']
            for arg in suspicious_args:
                if arg in cmd_string:
                    result["warnings"].append(f"Suspicious operator detected: {arg}")
            
            # Check for script execution
            script_extensions = ['.bat', '.cmd', '.ps1', '.vbs', '.js']
            for part in cmd_parts:
                if any(part.lower().endswith(ext) for ext in script_extensions):
                    result["warnings"].append(f"Script execution detected: {part}")
            
        except Exception as e:
            result["errors"].append(f"Command validation error: {str(e)}")
            result["valid"] = False
        
        return result
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> Dict[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 with SHA-256
        iterations = 100000
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations)
        
        return {
            "hash": base64.b64encode(hashed).decode(),
            "salt": salt,
            "iterations": iterations
        }
    
    def verify_password(self, password: str, hash_data: Dict[str, str]) -> bool:
        """Verify password against hash"""
        try:
            salt = hash_data["salt"]
            iterations = hash_data.get("iterations", 100000)
            stored_hash = base64.b64decode(hash_data["hash"])
            
            test_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations)
            
            return secrets.compare_digest(test_hash, stored_hash)
        except Exception:
            return False


# Global instances for singleton pattern
_masker_instance: Optional[DataMasker] = None
_validator_instance: Optional[SecurityValidator] = None


def get_masker() -> DataMasker:
    """Get global DataMasker instance"""
    global _masker_instance
    if _masker_instance is None:
        _masker_instance = DataMasker()
    return _masker_instance


def get_validator() -> SecurityValidator:
    """Get global SecurityValidator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = SecurityValidator()
    return _validator_instance


def init_masker() -> DataMasker:
    """Initialize global DataMasker instance"""
    global _masker_instance
    _masker_instance = DataMasker()
    return _masker_instance
