"""Integration tests for owlkit."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from owlkit.config.credentials import CredentialManager
from owlkit.docker.ghcr import GHCRManager
from owlkit.cwl.runner import CWLRunner
from owlkit.sbpack.manager import SBPackManager


class TestIntegration:
    """Test integration between different owlkit components."""

    def test_credential_manager_integration(self, temp_dir):
        """Test credential manager integration with other components."""
        config_dir = temp_dir / ".owlkit"
        cred_manager = CredentialManager(config_dir)
        
        # Store credentials for different services
        cred_manager.set_credential("github", "testuser", "github-token")
        cred_manager.set_credential("cgc", "auth_token", "cgc-token")
        
        # Test GHCR manager can access GitHub credentials
        ghcr_manager = GHCRManager("testuser")
        ghcr_manager.cred_manager = cred_manager
        
        stored_token = cred_manager.get_credential("github", "testuser")
        assert stored_token == "github-token"
        
        # Test SBPack manager can access CGC credentials
        sbpack_manager = SBPackManager()
        sbpack_manager.cred_manager = cred_manager
        
        stored_token = sbpack_manager.get_stored_token()
        assert stored_token == "cgc-token"

    @patch('subprocess.run')
    def test_docker_build_and_push_workflow(self, mock_subprocess, temp_dir):
        """Test complete Docker build and push workflow."""
        # Mock successful docker commands
        def mock_docker_cmd(cmd, **kwargs):
            result = Mock()
            result.returncode = 0
            
            if 'login' in cmd:
                result.stdout = "Login Succeeded"
            elif 'build' in cmd:
                result.stdout = "Successfully built abc123"
            elif 'push' in cmd:
                result.stdout = "The push refers to repository"
            
            return result
        
        mock_subprocess.side_effect = mock_docker_cmd
        
        # Create a test Dockerfile
        dockerfile = temp_dir / "Dockerfile"
        dockerfile.write_text("""
FROM ubuntu:latest
RUN echo "test"
""")
        
        # Initialize GHCR manager
        ghcr_manager = GHCRManager("testuser")
        
        # Test complete workflow
        assert ghcr_manager.login("test-token") is True
        assert ghcr_manager.build_image("test-app:latest", dockerfile=str(dockerfile)) is True
        assert ghcr_manager.push_image("test-app:latest") is True
        assert ghcr_manager.logout() is True

    @patch('subprocess.run')
    def test_cwl_workflow_execution_with_validation(self, mock_subprocess, sample_cwl_workflow, temp_dir):
        """Test CWL workflow validation and execution."""
        # Mock cwltool commands
        def mock_cwl_cmd(cmd, **kwargs):
            result = Mock()
            result.returncode = 0
            
            if '--validate' in cmd:
                result.stdout = "Workflow is valid"
            else:
                result.stdout = "Workflow completed successfully"
                # Create mock output files
                output_dir = Path(kwargs.get('cwd', temp_dir))
                (output_dir / "output.txt").write_text("workflow result")
            
            return result
        
        mock_subprocess.side_effect = mock_cwl_cmd
        
        cwl_runner = CWLRunner()
        
        # Validate workflow first
        assert cwl_runner.validate_workflow(str(sample_cwl_workflow)) is True
        
        # Run workflow
        output_dir = temp_dir / "outputs"
        output_dir.mkdir()
        
        inputs = {
            "input_file": {
                "class": "File",
                "path": str(temp_dir / "input.txt")
            }
        }
        
        # Create input file
        (temp_dir / "input.txt").write_text("test input")
        
        assert cwl_runner.run_workflow(
            str(sample_cwl_workflow),
            inputs,
            str(output_dir)
        ) is True
        
        # List outputs
        outputs = cwl_runner.list_outputs(str(output_dir))
        assert len(outputs) >= 1

    @patch('subprocess.run')
    def test_sbpack_end_to_end_workflow(self, mock_subprocess, sample_cwl_workflow, temp_dir):
        """Test complete sbpack workflow from packing to deployment."""
        # Mock sbpack and sb commands
        def mock_sb_cmd(cmd, **kwargs):
            result = Mock()
            result.returncode = 0
            
            if cmd[0] == 'sbpack':
                if '--version' in cmd:
                    result.stdout = "sbpack 2024.12.17"
                else:
                    # Create mock packed file
                    output_file = temp_dir / "packed.cwl"
                    packed_content = {
                        "cwlVersion": "v1.2",
                        "class": "Workflow",
                        "$graph": []
                    }
                    output_file.write_text(json.dumps(packed_content))
                    result.stdout = f"Packed workflow saved to {output_file}"
            elif cmd[0] == 'sb':
                if 'projects' in cmd:
                    result.stdout = '[{"id": "test/project", "name": "Test Project"}]'
                elif 'apps' in cmd:
                    if 'create' in cmd:
                        result.stdout = "App created successfully"
                    elif 'list' in cmd:
                        result.stdout = '[{"id": "test/app", "name": "Test App", "revision": 1}]'
            elif cmd[0] == 'pip':
                result.stdout = "Successfully installed sbpack"
            
            return result
        
        mock_subprocess.side_effect = mock_sb_cmd
        
        sbpack_manager = SBPackManager()
        
        # Store CGC token
        sbpack_manager.cred_manager.set_credential('cgc', 'auth_token', 'test-token')
        
        # Test login (should use stored token)
        assert sbpack_manager.login_to_cgc() is True
        
        # Pack workflow
        packed_file = sbpack_manager.pack_workflow(str(sample_cwl_workflow))
        assert packed_file is not None
        assert Path(packed_file).exists()
        
        # Validate packed workflow
        assert sbpack_manager.validate_packed_workflow(packed_file) is True
        
        # Deploy to CGC
        assert sbpack_manager.deploy_to_cgc(
            packed_file,
            "testuser/testproject",
            "test-app"
        ) is True
        
        # List apps
        apps = sbpack_manager.list_apps("testuser/testproject")
        assert len(apps) == 1
        assert apps[0]["name"] == "Test App"

    def test_credential_sharing_between_components(self, temp_dir):
        """Test that components can share the same credential manager."""
        config_dir = temp_dir / ".owlkit"
        shared_cred_manager = CredentialManager(config_dir)
        
        # Store credentials
        shared_cred_manager.set_credential("github", "testuser", "github-token")
        shared_cred_manager.set_credential("cgc", "auth_token", "cgc-token")
        
        # Create components with shared credential manager
        ghcr_manager = GHCRManager("testuser")
        ghcr_manager.cred_manager = shared_cred_manager
        
        sbpack_manager = SBPackManager()
        sbpack_manager.cred_manager = shared_cred_manager
        
        # Both should be able to access their respective credentials
        assert shared_cred_manager.get_credential("github", "testuser") == "github-token"
        assert sbpack_manager.get_stored_token() == "cgc-token"

    def test_error_propagation_between_components(self, temp_dir):
        """Test that errors are properly propagated between components."""
        # Test with invalid config directory permissions (simulate error)
        config_dir = temp_dir / ".owlkit"
        config_dir.mkdir()
        
        cred_manager = CredentialManager(config_dir)
        
        # This should handle errors gracefully
        cred_manager.KEYRING_AVAILABLE = False
        
        # Should still work with file fallback
        cred_manager.set_credential("test", "user", "token")
        assert cred_manager.get_credential("test", "user") == "token"

    @patch('subprocess.run')
    def test_workflow_dependency_chain(self, mock_subprocess, sample_cwl_workflow, temp_dir):
        """Test complete workflow: build Docker image, pack CWL, deploy to CGC."""
        # Mock all external commands
        def mock_all_commands(cmd, **kwargs):
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            
            if 'docker' in cmd:
                if 'login' in cmd:
                    result.stdout = "Login Succeeded"
                elif 'build' in cmd:
                    result.stdout = "Successfully built abc123"
                elif 'push' in cmd:
                    result.stdout = "Push complete"
            elif 'sbpack' in cmd:
                if '--version' in cmd:
                    result.stdout = "sbpack 2024.12.17"
                else:
                    # Create packed file
                    packed_file = temp_dir / "gdc-uploader-packed.cwl"
                    packed_content = {"cwlVersion": "v1.2", "class": "Workflow"}
                    packed_file.write_text(json.dumps(packed_content))
            elif 'sb' in cmd and 'apps' in cmd and 'create' in cmd:
                result.stdout = "App created: gdc-uploader"
            elif 'sb' in cmd and 'projects' in cmd:
                result.stdout = '[{"id": "test/project"}]'
            
            return result
        
        mock_subprocess.side_effect = mock_all_commands
        
        # Create Dockerfile
        dockerfile = temp_dir / "Dockerfile"
        dockerfile.write_text("FROM ubuntu:latest")
        
        # 1. Build and push Docker image
        ghcr_manager = GHCRManager("testuser")
        assert ghcr_manager.login("github-token") is True
        assert ghcr_manager.build_image("gdc-uploader:latest", dockerfile=str(dockerfile)) is True
        assert ghcr_manager.push_image("gdc-uploader:latest") is True
        
        # 2. Pack CWL workflow
        sbpack_manager = SBPackManager()
        sbpack_manager.cred_manager.set_credential('cgc', 'auth_token', 'cgc-token')
        
        packed_file = sbpack_manager.pack_workflow(str(sample_cwl_workflow), "gdc-uploader-packed.cwl")
        assert packed_file == "gdc-uploader-packed.cwl"
        assert Path(packed_file).exists()
        
        # 3. Deploy to CGC
        assert sbpack_manager.deploy_to_cgc(
            packed_file,
            "testuser/cancer-genomics",
            "gdc-uploader"
        ) is True

    def test_configuration_persistence(self, temp_dir):
        """Test that configuration persists across component instances."""
        config_dir = temp_dir / ".owlkit"
        
        # Create first credential manager and store data
        cred_manager1 = CredentialManager(config_dir)
        cred_manager1.set_credential("github", "user1", "token1")
        cred_manager1.set_credential("cgc", "auth_token", "cgc-token1")
        
        # Create second credential manager (simulating new session)
        cred_manager2 = CredentialManager(config_dir)
        
        # Should be able to retrieve stored credentials
        assert cred_manager2.get_credential("github", "user1") == "token1"
        assert cred_manager2.get_credential("cgc", "auth_token") == "cgc-token1"
        
        # Update credentials
        cred_manager2.set_credential("github", "user1", "token2")
        
        # Create third instance to verify update persisted
        cred_manager3 = CredentialManager(config_dir)
        assert cred_manager3.get_credential("github", "user1") == "token2"

    def test_cross_component_error_handling(self, temp_dir):
        """Test error handling across component boundaries."""
        # Test scenario where Docker login fails but CWL operations can still work
        ghcr_manager = GHCRManager("testuser")
        cwl_runner = CWLRunner()
        
        # GHCR operations might fail due to network issues
        with patch('subprocess.run', side_effect=Exception("Network error")):
            assert ghcr_manager.login("token") is False
            # But CWL operations should still be independent
            assert cwl_runner._check_cwltool_available() is False  # Because subprocess fails
        
        # Test graceful degradation
        sbpack_manager = SBPackManager()
        
        # If sbpack is not available, should handle gracefully
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            assert sbpack_manager.check_sbpack_available() is False
            
            # Install should fail gracefully
            assert sbpack_manager.install_sbpack() is False