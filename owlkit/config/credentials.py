"""Secure credential storage and management."""

import os
import json
import keyring
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from getpass import getpass
import platform


class CredentialManager:
    """Manages secure storage of credentials using keyring and encryption."""
    
    SERVICE_NAME = "owlkit"
    KEYRING_AVAILABLE = True
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize credential manager.
        
        Args:
            config_dir: Directory for storing encrypted credentials if keyring unavailable
        """
        self.config_dir = config_dir or Path.home() / ".owlkit"
        self.config_dir.mkdir(exist_ok=True, mode=0o700)
        self.creds_file = self.config_dir / "credentials.enc"
        
        # Test keyring availability
        try:
            keyring.get_password("test", "test")
        except Exception:
            self.KEYRING_AVAILABLE = False
            
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key for fallback file storage."""
        key_file = self.config_dir / ".key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Secure the key file
            os.chmod(key_file, 0o600)
            return key
    
    def get_credential(self, service: str, username: str) -> Optional[str]:
        """Retrieve a credential.
        
        Args:
            service: Service name (e.g., 'docker', 'sbg')
            username: Username or key name
            
        Returns:
            The credential value or None if not found
        """
        full_key = f"{service}:{username}"
        
        if self.KEYRING_AVAILABLE:
            try:
                return keyring.get_password(self.SERVICE_NAME, full_key)
            except Exception:
                pass
        
        # Fallback to encrypted file
        if self.creds_file.exists():
            try:
                key = self._get_or_create_key()
                f = Fernet(key)
                
                with open(self.creds_file, 'rb') as file:
                    encrypted_data = file.read()
                    decrypted_data = f.decrypt(encrypted_data)
                    creds = json.loads(decrypted_data.decode())
                    
                return creds.get(full_key)
            except Exception:
                pass
                
        return None
    
    def set_credential(self, service: str, username: str, password: str) -> None:
        """Store a credential securely.
        
        Args:
            service: Service name (e.g., 'docker', 'sbg')
            username: Username or key name
            password: Password or token value
        """
        full_key = f"{service}:{username}"
        
        if self.KEYRING_AVAILABLE:
            try:
                keyring.set_password(self.SERVICE_NAME, full_key, password)
                return
            except Exception:
                pass
        
        # Fallback to encrypted file
        key = self._get_or_create_key()
        f = Fernet(key)
        
        # Load existing credentials
        creds = {}
        if self.creds_file.exists():
            try:
                with open(self.creds_file, 'rb') as file:
                    encrypted_data = file.read()
                    decrypted_data = f.decrypt(encrypted_data)
                    creds = json.loads(decrypted_data.decode())
            except Exception:
                creds = {}
        
        # Update credentials
        creds[full_key] = password
        
        # Save encrypted
        encrypted_data = f.encrypt(json.dumps(creds).encode())
        with open(self.creds_file, 'wb') as file:
            file.write(encrypted_data)
        
        # Secure the file
        os.chmod(self.creds_file, 0o600)
    
    def delete_credential(self, service: str, username: str) -> None:
        """Delete a stored credential.
        
        Args:
            service: Service name
            username: Username or key name
        """
        full_key = f"{service}:{username}"
        
        if self.KEYRING_AVAILABLE:
            try:
                keyring.delete_password(self.SERVICE_NAME, full_key)
            except Exception:
                pass
        
        # Also remove from encrypted file
        if self.creds_file.exists():
            try:
                key = self._get_or_create_key()
                f = Fernet(key)
                
                with open(self.creds_file, 'rb') as file:
                    encrypted_data = file.read()
                    decrypted_data = f.decrypt(encrypted_data)
                    creds = json.loads(decrypted_data.decode())
                
                if full_key in creds:
                    del creds[full_key]
                    encrypted_data = f.encrypt(json.dumps(creds).encode())
                    with open(self.creds_file, 'wb') as file:
                        file.write(encrypted_data)
            except Exception:
                pass
    
    def prompt_and_store(self, service: str, username: str, 
                        prompt: Optional[str] = None) -> str:
        """Prompt user for credential and store it.
        
        Args:
            service: Service name
            username: Username or key name
            prompt: Custom prompt message
            
        Returns:
            The entered credential
        """
        # Check if already stored
        existing = self.get_credential(service, username)
        if existing:
            use_existing = input(f"Found stored credential for {service}:{username}. Use it? [Y/n]: ")
            if use_existing.lower() != 'n':
                return existing
        
        # Prompt for new credential
        if prompt is None:
            prompt = f"Enter {service} credential for {username}: "
        
        credential = getpass(prompt)
        
        # Ask if should store
        store = input("Store this credential securely? [Y/n]: ")
        if store.lower() != 'n':
            self.set_credential(service, username, credential)
            print(f"Credential stored {'in system keyring' if self.KEYRING_AVAILABLE else 'in encrypted file'}")
        
        return credential
    
    def list_credentials(self) -> Dict[str, list]:
        """List all stored credentials (keys only, not values).
        
        Returns:
            Dictionary mapping services to list of usernames
        """
        creds = {}
        
        # From keyring
        if self.KEYRING_AVAILABLE:
            try:
                # This is platform-specific, might not work everywhere
                pass
            except Exception:
                pass
        
        # From encrypted file
        if self.creds_file.exists():
            try:
                key = self._get_or_create_key()
                f = Fernet(key)
                
                with open(self.creds_file, 'rb') as file:
                    encrypted_data = file.read()
                    decrypted_data = f.decrypt(encrypted_data)
                    stored_creds = json.loads(decrypted_data.decode())
                
                for full_key in stored_creds:
                    service, username = full_key.split(':', 1)
                    if service not in creds:
                        creds[service] = []
                    creds[service].append(username)
            except Exception:
                pass
        
        return creds