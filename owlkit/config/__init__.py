"""Configuration management for OWLKit."""

from .credentials import CredentialManager

ConfigManager = CredentialManager  # Alias for compatibility

__all__ = ["ConfigManager", "CredentialManager"]