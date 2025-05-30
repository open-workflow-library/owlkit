"""Tests for Docker/GHCR operations."""

import os
import pytest
from unittest.mock import patch, Mock

from owlkit.docker.ghcr import GHCRManager


class TestGHCRManager:
    """Test GitHub Container Registry operations."""

    def test_init_no_username(self):
        """Test initialization without username."""
        manager = GHCRManager()
        assert manager.username is None
        assert manager.registry == "ghcr.io"

    def test_init_with_username(self):
        """Test initialization with username."""
        manager = GHCRManager("testuser")
        assert manager.username == "testuser"

    def test_detect_codespaces_environment(self, mock_environment):
        """Test Codespaces environment detection."""
        manager = GHCRManager()
        assert manager._is_codespaces()
        assert manager._get_github_token() == "fake-github-token"
        assert manager._get_github_username() == "testuser"

    def test_detect_non_codespaces_environment(self):
        """Test non-Codespaces environment detection."""
        manager = GHCRManager()
        assert not manager._is_codespaces()
        assert manager._get_github_token() is None

    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_login_success(self, mock_input, mock_getpass, ghcr_manager, mock_docker_commands):
        """Test successful GHCR login."""
        mock_input.side_effect = ["testuser", "y"]  # username, store credential
        mock_getpass.return_value = "test-token"

        result = ghcr_manager.login()
        
        assert result is True
        mock_docker_commands.assert_called()
        
        # Verify docker login command was called
        call_args = mock_docker_commands.call_args[0][0]
        assert "docker" in call_args
        assert "login" in call_args
        assert "ghcr.io" in call_args

    def test_login_with_token_parameter(self, ghcr_manager, mock_docker_commands):
        """Test login with token provided as parameter."""
        result = ghcr_manager.login("provided-token")
        
        assert result is True
        mock_docker_commands.assert_called()

    def test_login_failure(self, ghcr_manager, mock_subprocess):
        """Test failed GHCR login."""
        mock_subprocess.side_effect = Exception("Docker login failed")

        result = ghcr_manager.login("test-token")
        
        assert result is False

    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_login_in_codespaces_limited_permissions(self, mock_input, mock_getpass, 
                                                   mock_environment, mock_docker_commands):
        """Test login in Codespaces with limited token permissions."""
        # Simulate the built-in token failing
        mock_docker_commands.side_effect = [
            Exception("Permission denied"),  # First attempt with GITHUB_TOKEN fails
            Mock(returncode=0, stdout="Login Succeeded")  # Second attempt with PAT succeeds
        ]
        
        mock_input.side_effect = ["y"]  # Store credential
        mock_getpass.return_value = "personal-access-token"

        manager = GHCRManager()
        result = manager.login()
        
        assert result is True
        assert mock_docker_commands.call_count == 2

    def test_build_image_success(self, ghcr_manager, mock_docker_commands):
        """Test successful Docker image build."""
        result = ghcr_manager.build_image("test-image:latest", dockerfile="Dockerfile")
        
        assert result is True
        call_args = mock_docker_commands.call_args[0][0]
        assert "docker" in call_args
        assert "build" in call_args
        assert "test-image:latest" in call_args

    def test_build_image_with_push(self, ghcr_manager, mock_docker_commands):
        """Test Docker image build with automatic push."""
        result = ghcr_manager.build_image("test-image:latest", push=True)
        
        assert result is True
        # Should be called twice: once for build, once for push
        assert mock_docker_commands.call_count == 2

    def test_build_image_failure(self, ghcr_manager, mock_subprocess):
        """Test failed Docker image build."""
        mock_subprocess.side_effect = Exception("Build failed")

        result = ghcr_manager.build_image("test-image:latest")
        
        assert result is False

    def test_push_image_success(self, ghcr_manager, mock_docker_commands):
        """Test successful Docker image push."""
        result = ghcr_manager.push_image("test-image:latest")
        
        assert result is True
        call_args = mock_docker_commands.call_args[0][0]
        assert "docker" in call_args
        assert "push" in call_args

    def test_push_image_failure(self, ghcr_manager, mock_subprocess):
        """Test failed Docker image push."""
        mock_subprocess.side_effect = Exception("Push failed")

        result = ghcr_manager.push_image("test-image:latest")
        
        assert result is False

    def test_pull_image_success(self, ghcr_manager, mock_docker_commands):
        """Test successful Docker image pull."""
        result = ghcr_manager.pull_image("test-image:latest")
        
        assert result is True
        call_args = mock_docker_commands.call_args[0][0]
        assert "docker" in call_args
        assert "pull" in call_args

    def test_tag_image_success(self, ghcr_manager, mock_docker_commands):
        """Test successful Docker image tagging."""
        result = ghcr_manager.tag_for_ghcr("local-image:latest", "testuser")
        
        assert result is True
        call_args = mock_docker_commands.call_args[0][0]
        assert "docker" in call_args
        assert "tag" in call_args
        assert "ghcr.io/testuser/local-image:latest" in call_args

    def test_tag_image_auto_username(self, mock_environment, mock_docker_commands):
        """Test image tagging with automatic username detection."""
        manager = GHCRManager()
        result = manager.tag_for_ghcr("local-image:latest")
        
        assert result is True
        call_args = mock_docker_commands.call_args[0][0]
        assert "ghcr.io/testuser/local-image:latest" in call_args

    def test_list_images_success(self, ghcr_manager, mock_docker_commands):
        """Test successful Docker image listing."""
        mock_docker_commands.return_value.stdout = """
REPOSITORY                       TAG       IMAGE ID       CREATED        SIZE
ghcr.io/testuser/app1           latest    abc123         2 hours ago    100MB
ghcr.io/testuser/app2           v1.0      def456         1 day ago      200MB
"""
        
        images = ghcr_manager.list_ghcr_images()
        
        assert len(images) == 2
        assert images[0]["repository"] == "ghcr.io/testuser/app1"
        assert images[0]["tag"] == "latest"
        assert images[1]["repository"] == "ghcr.io/testuser/app2"
        assert images[1]["tag"] == "v1.0"

    def test_list_images_empty(self, ghcr_manager, mock_docker_commands):
        """Test Docker image listing with no GHCR images."""
        mock_docker_commands.return_value.stdout = """
REPOSITORY    TAG       IMAGE ID       CREATED        SIZE
ubuntu        latest    abc123         2 hours ago    100MB
"""
        
        images = ghcr_manager.list_ghcr_images()
        
        assert len(images) == 0

    def test_logout_success(self, ghcr_manager, mock_docker_commands):
        """Test successful Docker logout."""
        result = ghcr_manager.logout()
        
        assert result is True
        call_args = mock_docker_commands.call_args[0][0]
        assert "docker" in call_args
        assert "logout" in call_args
        assert "ghcr.io" in call_args

    def test_get_full_image_name(self, ghcr_manager):
        """Test full image name generation."""
        # With username provided
        name = ghcr_manager._get_full_image_name("app:latest", "testuser")
        assert name == "ghcr.io/testuser/app:latest"

        # Without username (should use manager's username)
        ghcr_manager.username = "defaultuser"
        name = ghcr_manager._get_full_image_name("app:latest")
        assert name == "ghcr.io/defaultuser/app:latest"

    def test_validate_image_name(self, ghcr_manager):
        """Test image name validation."""
        # Valid names
        assert ghcr_manager._validate_image_name("app:latest") is True
        assert ghcr_manager._validate_image_name("my-app:v1.0") is True
        assert ghcr_manager._validate_image_name("namespace/app:latest") is True

        # Invalid names
        assert ghcr_manager._validate_image_name("") is False
        assert ghcr_manager._validate_image_name("APP:latest") is False  # uppercase
        assert ghcr_manager._validate_image_name("app:") is False  # empty tag

    def test_extract_org_and_repo(self, ghcr_manager):
        """Test organization and repository extraction from image names."""
        org, repo = ghcr_manager._extract_org_and_repo("my-app:latest")
        assert org is None
        assert repo == "my-app"

        org, repo = ghcr_manager._extract_org_and_repo("myorg/my-app:latest")
        assert org == "myorg"
        assert repo == "my-app"

        org, repo = ghcr_manager._extract_org_and_repo("ghcr.io/myorg/my-app:latest")
        assert org == "myorg"
        assert repo == "my-app"

    @patch('builtins.input')
    def test_prompt_for_username(self, mock_input, ghcr_manager):
        """Test username prompting."""
        mock_input.return_value = "prompted-user"

        username = ghcr_manager._prompt_for_username()
        
        assert username == "prompted-user"
        mock_input.assert_called_with("Enter GitHub username or organization: ")

    def test_command_timeout_handling(self, ghcr_manager, mock_subprocess):
        """Test command timeout handling."""
        import subprocess
        mock_subprocess.side_effect = subprocess.TimeoutExpired("docker", 30)

        result = ghcr_manager.build_image("test:latest")
        
        assert result is False

    def test_network_error_handling(self, ghcr_manager, mock_subprocess):
        """Test network error handling."""
        mock_subprocess.side_effect = OSError("Network unreachable")

        result = ghcr_manager.push_image("test:latest")
        
        assert result is False