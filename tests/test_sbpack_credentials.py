"""Tests for sbpack credentials file setup."""

import os
import configparser
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from owlkit.sbpack.manager import SBPackManager


class TestSBPackCredentials:
    """Test sbpack credentials file management."""

    def test_setup_sbpack_credentials_new_file(self, temp_dir, sbpack_manager):
        """Test creating new sbpack credentials file."""
        # Mock home directory to use temp directory
        with patch('pathlib.Path.home', return_value=temp_dir):
            result = sbpack_manager._setup_sbpack_credentials("test-token", "cgc")
            
            assert result is True
            
            # Check that directory was created
            sb_dir = temp_dir / ".sevenbridges"
            assert sb_dir.exists()
            assert sb_dir.stat().st_mode & 0o777 == 0o700
            
            # Check credentials file
            creds_file = sb_dir / "credentials"
            assert creds_file.exists()
            assert creds_file.stat().st_mode & 0o777 == 0o600
            
            # Parse and verify content
            config = configparser.ConfigParser()
            config.read(creds_file)
            
            assert config.has_section('cgc')
            assert config.get('cgc', 'api_endpoint') == 'https://cgc-api.sbgenomics.com/v2'
            assert config.get('cgc', 'auth_token') == 'test-token'

    def test_setup_sbpack_credentials_existing_file(self, temp_dir, sbpack_manager):
        """Test updating existing sbpack credentials file."""
        # Create existing credentials file
        sb_dir = temp_dir / ".sevenbridges"
        sb_dir.mkdir(mode=0o700)
        creds_file = sb_dir / "credentials"
        
        # Write existing content
        existing_content = """[sbg-us]
api_endpoint = https://api.sbgenomics.com/v2
auth_token = existing-token
"""
        creds_file.write_text(existing_content)
        
        # Mock home directory
        with patch('pathlib.Path.home', return_value=temp_dir):
            result = sbpack_manager._setup_sbpack_credentials("cgc-token", "cgc")
            
            assert result is True
            
            # Parse and verify both profiles exist
            config = configparser.ConfigParser()
            config.read(creds_file)
            
            # Original profile should still exist
            assert config.has_section('sbg-us')
            assert config.get('sbg-us', 'auth_token') == 'existing-token'
            
            # New profile should be added
            assert config.has_section('cgc')
            assert config.get('cgc', 'api_endpoint') == 'https://cgc-api.sbgenomics.com/v2'
            assert config.get('cgc', 'auth_token') == 'cgc-token'

    def test_setup_sbpack_credentials_update_existing_profile(self, temp_dir, sbpack_manager):
        """Test updating existing profile in credentials file."""
        # Create existing credentials file with CGC profile
        sb_dir = temp_dir / ".sevenbridges"
        sb_dir.mkdir(mode=0o700)
        creds_file = sb_dir / "credentials"
        
        existing_content = """[cgc]
api_endpoint = https://cgc-api.sbgenomics.com/v2
auth_token = old-token
"""
        creds_file.write_text(existing_content)
        
        # Mock home directory
        with patch('pathlib.Path.home', return_value=temp_dir):
            result = sbpack_manager._setup_sbpack_credentials("new-token", "cgc")
            
            assert result is True
            
            # Parse and verify token was updated
            config = configparser.ConfigParser()
            config.read(creds_file)
            
            assert config.has_section('cgc')
            assert config.get('cgc', 'auth_token') == 'new-token'

    def test_setup_sbpack_credentials_custom_profile(self, temp_dir, sbpack_manager):
        """Test creating credentials with custom profile name."""
        with patch('pathlib.Path.home', return_value=temp_dir):
            result = sbpack_manager._setup_sbpack_credentials("test-token", "my-custom-profile")
            
            assert result is True
            
            # Check credentials file
            creds_file = temp_dir / ".sevenbridges" / "credentials"
            config = configparser.ConfigParser()
            config.read(creds_file)
            
            assert config.has_section('my-custom-profile')
            assert config.get('my-custom-profile', 'api_endpoint') == 'https://cgc-api.sbgenomics.com/v2'
            assert config.get('my-custom-profile', 'auth_token') == 'test-token'

    def test_setup_sbpack_credentials_permission_error(self, temp_dir, sbpack_manager):
        """Test handling permission errors when creating credentials."""
        # Mock home directory that we can't write to
        with patch('pathlib.Path.home', return_value=Path("/nonexistent")):
            result = sbpack_manager._setup_sbpack_credentials("test-token", "cgc")
            
            assert result is False

    def test_setup_sbpack_credentials_file_permissions(self, temp_dir, sbpack_manager):
        """Test that credentials file has correct permissions."""
        with patch('pathlib.Path.home', return_value=temp_dir):
            sbpack_manager._setup_sbpack_credentials("test-token", "cgc")
            
            # Check directory permissions
            sb_dir = temp_dir / ".sevenbridges"
            assert sb_dir.stat().st_mode & 0o777 == 0o700
            
            # Check file permissions
            creds_file = sb_dir / "credentials"
            assert creds_file.stat().st_mode & 0o777 == 0o600

    def test_deploy_with_credentials_setup(self, temp_dir, sample_cwl_workflow, mock_subprocess):
        """Test that deployment sets up credentials automatically."""
        # Mock sbpack command success
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "sbpack success"
        mock_subprocess.return_value.stderr = ""
        
        sbpack_manager = SBPackManager()
        sbpack_manager.cred_manager.set_credential('cgc', 'auth_token', 'test-token')
        
        with patch('pathlib.Path.home', return_value=temp_dir):
            result = sbpack_manager.deploy_to_cgc(
                str(sample_cwl_workflow),
                "test/project",
                "test-app"
            )
            
            assert result is True
            
            # Verify credentials file was created
            creds_file = temp_dir / ".sevenbridges" / "credentials"
            assert creds_file.exists()
            
            # Verify sbpack was called
            mock_subprocess.assert_called()
            call_args = mock_subprocess.call_args[0][0]
            assert call_args == ['sbpack', 'cgc', 'test/project/test-app', str(sample_cwl_workflow)]

    def test_credentials_file_format_compatibility(self, temp_dir, sbpack_manager):
        """Test that generated credentials file is compatible with sbpack."""
        with patch('pathlib.Path.home', return_value=temp_dir):
            sbpack_manager._setup_sbpack_credentials("test-token-123", "cgc")
            
            # Read file and verify it can be parsed by configparser
            creds_file = temp_dir / ".sevenbridges" / "credentials"
            config = configparser.ConfigParser()
            config.read(creds_file)
            
            # Verify required fields for sbpack
            assert config.has_section('cgc')
            assert config.has_option('cgc', 'api_endpoint')
            assert config.has_option('cgc', 'auth_token')
            
            # Verify values
            endpoint = config.get('cgc', 'api_endpoint')
            token = config.get('cgc', 'auth_token')
            
            assert endpoint == 'https://cgc-api.sbgenomics.com/v2'
            assert token == 'test-token-123'
            
            # Verify format matches sbpack expectations
            with open(creds_file, 'r') as f:
                content = f.read()
                
            # Should contain section header
            assert '[cgc]' in content
            # Should contain key-value pairs
            assert 'api_endpoint = https://cgc-api.sbgenomics.com/v2' in content
            assert 'auth_token = test-token-123' in content

    def test_multiple_profiles_handling(self, temp_dir, sbpack_manager):
        """Test managing multiple profiles in credentials file."""
        with patch('pathlib.Path.home', return_value=temp_dir):
            # Add multiple profiles
            sbpack_manager._setup_sbpack_credentials("cgc-token", "cgc")
            sbpack_manager._setup_sbpack_credentials("sbg-token", "sbg-us") 
            sbpack_manager._setup_sbpack_credentials("eu-token", "sbg-eu")
            
            # Verify all profiles exist
            creds_file = temp_dir / ".sevenbridges" / "credentials"
            config = configparser.ConfigParser()
            config.read(creds_file)
            
            assert config.has_section('cgc')
            assert config.has_section('sbg-us')
            assert config.has_section('sbg-eu')
            
            # Verify tokens are correct
            assert config.get('cgc', 'auth_token') == 'cgc-token'
            assert config.get('sbg-us', 'auth_token') == 'sbg-token'
            assert config.get('sbg-eu', 'auth_token') == 'eu-token'

    def test_credentials_file_error_handling(self, temp_dir, sbpack_manager):
        """Test error handling when credentials file operations fail."""
        # Create a directory where the credentials file should be (causing write error)
        sb_dir = temp_dir / ".sevenbridges"
        sb_dir.mkdir()
        creds_dir = sb_dir / "credentials"
        creds_dir.mkdir()  # This should be a file, not a directory
        
        with patch('pathlib.Path.home', return_value=temp_dir):
            result = sbpack_manager._setup_sbpack_credentials("test-token", "cgc")
            
            assert result is False