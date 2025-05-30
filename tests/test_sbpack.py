"""Tests for sbpack operations."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from owlkit.sbpack.manager import SBPackManager


class TestSBPackManager:
    """Test Seven Bridges sbpack operations."""

    def test_init(self, sbpack_manager):
        """Test SBPackManager initialization."""
        assert sbpack_manager.console is not None
        assert sbpack_manager.cred_manager is not None

    def test_check_sbpack_available_true(self, sbpack_manager, mock_sbpack_commands):
        """Test sbpack availability check when available."""
        result = sbpack_manager.check_sbpack_available()
        
        assert result is True
        mock_sbpack_commands.assert_called()

    def test_check_sbpack_available_false(self, sbpack_manager, mock_subprocess):
        """Test sbpack availability check when not available."""
        mock_subprocess.side_effect = FileNotFoundError()

        result = sbpack_manager.check_sbpack_available()
        
        assert result is False

    def test_pack_workflow_success(self, sbpack_manager, sample_cwl_workflow, mock_sbpack_commands):
        """Test successful workflow packing."""
        result = sbpack_manager.pack_workflow(str(sample_cwl_workflow))
        
        assert result is not None
        assert result.endswith("-packed.cwl")
        mock_sbpack_commands.assert_called()

    def test_pack_workflow_with_output_file(self, sbpack_manager, sample_cwl_workflow, mock_sbpack_commands):
        """Test workflow packing with custom output filename."""
        output_file = "custom-packed.cwl"
        result = sbpack_manager.pack_workflow(str(sample_cwl_workflow), output_file)
        
        assert result == output_file
        
        call_args = mock_sbpack_commands.call_args[0][0]
        assert "sbpack" in call_args
        assert "--output" in call_args
        assert output_file in call_args

    def test_pack_workflow_file_not_found(self, sbpack_manager):
        """Test workflow packing with non-existent file."""
        with pytest.raises(FileNotFoundError):
            sbpack_manager.pack_workflow("/path/to/nonexistent.cwl")

    def test_pack_workflow_sbpack_not_available(self, sbpack_manager, sample_cwl_workflow, mock_subprocess):
        """Test workflow packing when sbpack is not available."""
        mock_subprocess.side_effect = FileNotFoundError()

        with pytest.raises(RuntimeError, match="sbpack is not available"):
            sbpack_manager.pack_workflow(str(sample_cwl_workflow))

    def test_pack_workflow_failure(self, sbpack_manager, sample_cwl_workflow, mock_subprocess):
        """Test failed workflow packing."""
        # First call succeeds (version check), second fails (packing)
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout="sbpack 2024.12.17"),  # version check
            Exception("Packing failed")  # actual packing
        ]

        with pytest.raises(Exception):
            sbpack_manager.pack_workflow(str(sample_cwl_workflow))

    def test_validate_packed_workflow_success(self, sbpack_manager, sample_packed_workflow):
        """Test successful packed workflow validation."""
        result = sbpack_manager.validate_packed_workflow(str(sample_packed_workflow))
        
        assert result is True

    def test_validate_packed_workflow_file_not_found(self, sbpack_manager):
        """Test packed workflow validation with non-existent file."""
        result = sbpack_manager.validate_packed_workflow("/path/to/nonexistent.cwl")
        
        assert result is False

    def test_validate_packed_workflow_invalid_json(self, sbpack_manager, temp_dir):
        """Test packed workflow validation with invalid JSON."""
        invalid_file = temp_dir / "invalid.cwl"
        invalid_file.write_text("not valid json")
        
        result = sbpack_manager.validate_packed_workflow(str(invalid_file))
        
        assert result is False

    def test_validate_packed_workflow_missing_class(self, sbpack_manager, temp_dir):
        """Test packed workflow validation with missing class field."""
        workflow_data = {
            "cwlVersion": "v1.2"
            # Missing "class" field
        }
        
        workflow_file = temp_dir / "workflow.cwl"
        workflow_file.write_text(json.dumps(workflow_data))
        
        result = sbpack_manager.validate_packed_workflow(str(workflow_file))
        
        assert result is False

    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_login_to_cgc_success(self, mock_input, mock_getpass, sbpack_manager, mock_sbpack_commands):
        """Test successful CGC login."""
        mock_getpass.return_value = "test-token"
        mock_input.return_value = "y"  # Store credential

        result = sbpack_manager.login_to_cgc()
        
        assert result is True
        # Should test token by listing projects
        assert mock_sbpack_commands.call_count >= 1

    @patch('getpass.getpass')
    def test_login_to_cgc_with_token_parameter(self, mock_getpass, sbpack_manager, mock_sbpack_commands):
        """Test CGC login with token provided as parameter."""
        result = sbpack_manager.login_to_cgc("provided-token")
        
        assert result is True
        mock_getpass.assert_not_called()

    def test_login_to_cgc_use_stored_token(self, sbpack_manager, mock_sbpack_commands):
        """Test CGC login using stored token."""
        # Store a token first
        sbpack_manager.cred_manager.set_credential('cgc', 'auth_token', 'stored-token')
        
        with patch('builtins.input', return_value='y'):  # Use stored token
            result = sbpack_manager.login_to_cgc()
        
        assert result is True

    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_login_to_cgc_authentication_failure(self, mock_input, mock_getpass, 
                                               sbpack_manager, mock_subprocess):
        """Test CGC login with authentication failure."""
        mock_getpass.return_value = "invalid-token"
        mock_input.return_value = "y"
        mock_subprocess.side_effect = Exception("Authentication failed")

        result = sbpack_manager.login_to_cgc()
        
        assert result is False

    def test_get_stored_token(self, sbpack_manager):
        """Test getting stored CGC token."""
        # No token stored
        assert sbpack_manager.get_stored_token() is None

        # Store a token
        sbpack_manager.cred_manager.set_credential('cgc', 'auth_token', 'test-token')
        assert sbpack_manager.get_stored_token() == 'test-token'

    def test_deploy_to_cgc_success(self, sbpack_manager, sample_packed_workflow, mock_sbpack_commands):
        """Test successful CGC deployment."""
        # Store a token
        sbpack_manager.cred_manager.set_credential('cgc', 'auth_token', 'test-token')

        result = sbpack_manager.deploy_to_cgc(
            str(sample_packed_workflow),
            "testuser/testproject",
            "test-app"
        )
        
        assert result is True
        
        # Should validate first, then deploy
        assert mock_sbpack_commands.call_count >= 2

    def test_deploy_to_cgc_no_sb_cli(self, sbpack_manager, sample_packed_workflow, mock_subprocess):
        """Test CGC deployment when sb-cli is not available."""
        mock_subprocess.side_effect = FileNotFoundError()

        result = sbpack_manager.deploy_to_cgc(
            str(sample_packed_workflow),
            "testuser/testproject", 
            "test-app"
        )
        
        assert result is False

    def test_deploy_to_cgc_validation_failure(self, sbpack_manager, temp_dir, mock_sbpack_commands):
        """Test CGC deployment with validation failure."""
        # Create invalid packed workflow
        invalid_workflow = temp_dir / "invalid.cwl"
        invalid_workflow.write_text("invalid json")

        result = sbpack_manager.deploy_to_cgc(
            str(invalid_workflow),
            "testuser/testproject",
            "test-app"
        )
        
        assert result is False

    def test_deploy_to_cgc_no_token(self, sbpack_manager, sample_packed_workflow):
        """Test CGC deployment without token."""
        result = sbpack_manager.deploy_to_cgc(
            str(sample_packed_workflow),
            "testuser/testproject",
            "test-app"
        )
        
        assert result is False

    def test_deploy_to_cgc_file_not_found(self, sbpack_manager):
        """Test CGC deployment with non-existent file."""
        result = sbpack_manager.deploy_to_cgc(
            "/path/to/nonexistent.cwl",
            "testuser/testproject",
            "test-app"
        )
        
        assert result is False

    def test_list_apps_success(self, sbpack_manager, mock_sbpack_commands):
        """Test successful app listing."""
        # Store a token
        sbpack_manager.cred_manager.set_credential('cgc', 'auth_token', 'test-token')

        apps = sbpack_manager.list_apps("testuser/testproject")
        
        assert len(apps) == 1
        assert apps[0]["id"] == "test/app"
        assert apps[0]["name"] == "Test App"

    def test_list_apps_no_token(self, sbpack_manager):
        """Test app listing without token."""
        apps = sbpack_manager.list_apps("testuser/testproject")
        
        assert len(apps) == 0

    def test_list_apps_failure(self, sbpack_manager, mock_subprocess):
        """Test failed app listing."""
        # Store a token
        sbpack_manager.cred_manager.set_credential('cgc', 'auth_token', 'test-token')
        
        mock_subprocess.side_effect = Exception("Failed to list apps")

        apps = sbpack_manager.list_apps("testuser/testproject")
        
        assert len(apps) == 0

    def test_list_apps_invalid_json_response(self, sbpack_manager, mock_subprocess):
        """Test app listing with invalid JSON response."""
        # Store a token
        sbpack_manager.cred_manager.set_credential('cgc', 'auth_token', 'test-token')
        
        mock_subprocess.return_value.stdout = "invalid json"
        mock_subprocess.return_value.returncode = 0

        apps = sbpack_manager.list_apps("testuser/testproject")
        
        assert len(apps) == 0

    def test_install_sbpack_success(self, sbpack_manager, mock_sbpack_commands):
        """Test successful sbpack installation."""
        # Mock pip install command
        mock_sbpack_commands.side_effect = [
            Exception("sbpack not found"),  # First check fails
            Mock(returncode=0, stdout="Successfully installed sbpack")  # Install succeeds
        ]

        result = sbpack_manager.install_sbpack()
        
        assert result is True

    def test_install_sbpack_failure(self, sbpack_manager, mock_subprocess):
        """Test failed sbpack installation."""
        mock_subprocess.side_effect = Exception("Installation failed")

        result = sbpack_manager.install_sbpack()
        
        assert result is False

    def test_install_sbpack_pip_not_found(self, sbpack_manager, mock_subprocess):
        """Test sbpack installation when pip is not available."""
        mock_subprocess.side_effect = FileNotFoundError()

        result = sbpack_manager.install_sbpack()
        
        assert result is False

    def test_deploy_workflow_end_to_end(self, sbpack_manager, sample_cwl_workflow, mock_sbpack_commands):
        """Test end-to-end workflow deployment."""
        # Store a token
        sbpack_manager.cred_manager.set_credential('cgc', 'auth_token', 'test-token')

        # Pack the workflow
        packed_file = sbpack_manager.pack_workflow(str(sample_cwl_workflow))
        assert packed_file is not None

        # Validate the packed workflow
        Path(packed_file).write_text(json.dumps({
            "cwlVersion": "v1.2",
            "class": "Workflow"
        }))
        
        result = sbpack_manager.validate_packed_workflow(packed_file)
        assert result is True

        # Deploy to CGC
        result = sbpack_manager.deploy_to_cgc(
            packed_file,
            "testuser/testproject",
            "test-app"
        )
        assert result is True

    def test_token_precedence(self, sbpack_manager, mock_sbpack_commands):
        """Test token precedence: parameter > stored > environment."""
        # Store a token
        sbpack_manager.cred_manager.set_credential('cgc', 'auth_token', 'stored-token')
        
        # Test with parameter token (should take precedence)
        apps = sbpack_manager.list_apps("testuser/testproject", "param-token")
        assert len(apps) == 1
        
        # Check that param-token was used in environment
        call_env = mock_sbpack_commands.call_args[1]['env']
        assert call_env['SB_AUTH_TOKEN'] == 'param-token'

    def test_error_handling_during_packing(self, sbpack_manager, sample_cwl_workflow, mock_subprocess):
        """Test error handling during workflow packing."""
        # sbpack available but packing fails
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout="sbpack 2024.12.17"),  # version check succeeds
            Mock(returncode=1, stderr="Packing error", stdout="")  # packing fails
        ]

        with pytest.raises(Exception):
            sbpack_manager.pack_workflow(str(sample_cwl_workflow))

    def test_workflow_validation_warnings(self, sbpack_manager, temp_dir):
        """Test workflow validation with warnings."""
        # Create workflow missing cwlVersion
        workflow_data = {
            "class": "Workflow"
            # Missing cwlVersion - should trigger warning
        }
        
        workflow_file = temp_dir / "workflow.cwl"
        workflow_file.write_text(json.dumps(workflow_data))
        
        # Should still pass validation but show warning
        result = sbpack_manager.validate_packed_workflow(str(workflow_file))
        assert result is True