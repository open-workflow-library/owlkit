"""Tests for credential management."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from owlkit.config.credentials import CredentialManager


class TestCredentialManager:
    """Test credential storage and retrieval."""

    def test_init_creates_config_dir(self, temp_dir):
        """Test that config directory is created on init."""
        config_dir = temp_dir / ".owlkit"
        assert not config_dir.exists()
        
        manager = CredentialManager(config_dir=config_dir)
        assert config_dir.exists()
        assert config_dir.stat().st_mode & 0o777 == 0o700  # Check permissions

    def test_keyring_availability_detection(self, credential_manager, mock_keyring):
        """Test keyring availability detection."""
        # Test when keyring is available
        mock_keyring['get'].return_value = None
        manager = CredentialManager()
        assert manager.KEYRING_AVAILABLE

        # Test when keyring raises exception
        mock_keyring['get'].side_effect = Exception("Keyring not available")
        manager = CredentialManager()
        assert not manager.KEYRING_AVAILABLE

    def test_set_and_get_credential_keyring(self, credential_manager, mock_keyring):
        """Test credential storage and retrieval using keyring."""
        credential_manager.KEYRING_AVAILABLE = True
        mock_keyring['get'].return_value = "test-token"
        mock_keyring['set'].return_value = None

        # Store credential
        credential_manager.set_credential("test-service", "test-user", "test-token")
        mock_keyring['set'].assert_called_with("owlkit", "test-service:test-user", "test-token")

        # Retrieve credential
        result = credential_manager.get_credential("test-service", "test-user")
        assert result == "test-token"
        mock_keyring['get'].assert_called_with("owlkit", "test-service:test-user")

    def test_set_and_get_credential_file_fallback(self, credential_manager):
        """Test credential storage and retrieval using encrypted file fallback."""
        credential_manager.KEYRING_AVAILABLE = False

        # Store credential
        credential_manager.set_credential("test-service", "test-user", "test-token")
        
        # Check that encrypted file was created
        assert credential_manager.creds_file.exists()
        assert credential_manager.creds_file.stat().st_mode & 0o777 == 0o600

        # Retrieve credential
        result = credential_manager.get_credential("test-service", "test-user")
        assert result == "test-token"

    def test_get_nonexistent_credential(self, credential_manager):
        """Test retrieving a credential that doesn't exist."""
        result = credential_manager.get_credential("nonexistent", "user")
        assert result is None

    def test_delete_credential_keyring(self, credential_manager, mock_keyring):
        """Test credential deletion from keyring."""
        credential_manager.KEYRING_AVAILABLE = True
        mock_keyring['delete'].return_value = None

        credential_manager.delete_credential("test-service", "test-user")
        mock_keyring['delete'].assert_called_with("owlkit", "test-service:test-user")

    def test_delete_credential_file(self, credential_manager):
        """Test credential deletion from encrypted file."""
        credential_manager.KEYRING_AVAILABLE = False

        # Store two credentials
        credential_manager.set_credential("service1", "user1", "token1")
        credential_manager.set_credential("service2", "user2", "token2")

        # Delete one credential
        credential_manager.delete_credential("service1", "user1")

        # Verify only one credential remains
        assert credential_manager.get_credential("service1", "user1") is None
        assert credential_manager.get_credential("service2", "user2") == "token2"

    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_prompt_and_store_new_credential(self, mock_input, mock_getpass, credential_manager):
        """Test prompting for and storing a new credential."""
        mock_getpass.return_value = "new-token"
        mock_input.return_value = "y"  # Store the credential

        result = credential_manager.prompt_and_store("github", "username")
        
        assert result == "new-token"
        mock_getpass.assert_called_once()
        assert credential_manager.get_credential("github", "username") == "new-token"

    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_prompt_and_store_use_existing(self, mock_input, mock_getpass, credential_manager):
        """Test using existing stored credential."""
        # Store an existing credential
        credential_manager.set_credential("github", "username", "existing-token")
        
        mock_input.return_value = "y"  # Use existing credential

        result = credential_manager.prompt_and_store("github", "username")
        
        assert result == "existing-token"
        mock_getpass.assert_not_called()

    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_prompt_and_store_replace_existing(self, mock_input, mock_getpass, credential_manager):
        """Test replacing existing credential with new one."""
        # Store an existing credential
        credential_manager.set_credential("github", "username", "old-token")
        
        mock_input.side_effect = ["n", "y"]  # Don't use existing, store new one
        mock_getpass.return_value = "new-token"

        result = credential_manager.prompt_and_store("github", "username")
        
        assert result == "new-token"
        assert credential_manager.get_credential("github", "username") == "new-token"

    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_prompt_and_store_dont_save(self, mock_input, mock_getpass, credential_manager):
        """Test not saving the credential."""
        mock_getpass.return_value = "temp-token"
        mock_input.return_value = "n"  # Don't store the credential

        result = credential_manager.prompt_and_store("github", "username")
        
        assert result == "temp-token"
        assert credential_manager.get_credential("github", "username") is None

    def test_list_credentials(self, credential_manager):
        """Test listing stored credentials."""
        credential_manager.KEYRING_AVAILABLE = False

        # Store multiple credentials
        credential_manager.set_credential("github", "user1", "token1")
        credential_manager.set_credential("github", "user2", "token2")
        credential_manager.set_credential("cgc", "user1", "token3")

        creds = credential_manager.list_credentials()
        
        assert "github" in creds
        assert "cgc" in creds
        assert "user1" in creds["github"]
        assert "user2" in creds["github"]
        assert "user1" in creds["cgc"]

    def test_encryption_key_generation(self, credential_manager):
        """Test that encryption key is generated and reused."""
        credential_manager.KEYRING_AVAILABLE = False
        key_file = credential_manager.config_dir / ".key"
        
        # First call should create the key
        key1 = credential_manager._get_or_create_key()
        assert key_file.exists()
        assert key_file.stat().st_mode & 0o777 == 0o600

        # Second call should reuse the same key
        key2 = credential_manager._get_or_create_key()
        assert key1 == key2

    def test_corrupted_credentials_file_handling(self, credential_manager):
        """Test handling of corrupted credentials file."""
        credential_manager.KEYRING_AVAILABLE = False
        
        # Create a corrupted credentials file
        credential_manager.creds_file.write_bytes(b"corrupted data")
        
        # Should handle gracefully and return None
        result = credential_manager.get_credential("test", "user")
        assert result is None

    def test_multiple_services_same_username(self, credential_manager):
        """Test storing credentials for multiple services with same username."""
        credential_manager.KEYRING_AVAILABLE = False

        credential_manager.set_credential("github", "testuser", "github-token")
        credential_manager.set_credential("cgc", "testuser", "cgc-token")

        assert credential_manager.get_credential("github", "testuser") == "github-token"
        assert credential_manager.get_credential("cgc", "testuser") == "cgc-token"