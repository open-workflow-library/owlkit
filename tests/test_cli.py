"""Tests for CLI interface."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, Mock

from owlkit.cli import main


class TestCLI:
    """Test command-line interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_main_help(self):
        """Test main help command."""
        result = self.runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert "OWLKit - Open Workflow Library Toolkit" in result.output
        assert "docker" in result.output
        assert "cwl" in result.output
        assert "sbpack" in result.output

    def test_main_version(self):
        """Test version command."""
        result = self.runner.invoke(main, ['--version'])
        
        assert result.exit_code == 0
        assert "owlkit" in result.output

    def test_docker_help(self):
        """Test docker subcommand help."""
        result = self.runner.invoke(main, ['docker', '--help'])
        
        assert result.exit_code == 0
        assert "Docker/GHCR management commands" in result.output
        assert "login" in result.output
        assert "build" in result.output
        assert "push" in result.output

    @patch('owlkit.cli.GHCRManager')
    def test_docker_login_success(self, mock_ghcr_class):
        """Test successful docker login."""
        mock_manager = Mock()
        mock_manager.login.return_value = True
        mock_ghcr_class.return_value = mock_manager

        result = self.runner.invoke(main, ['docker', 'login'])
        
        assert result.exit_code == 0
        mock_manager.login.assert_called_once()

    @patch('owlkit.cli.GHCRManager')
    def test_docker_login_failure(self, mock_ghcr_class):
        """Test failed docker login."""
        mock_manager = Mock()
        mock_manager.login.return_value = False
        mock_ghcr_class.return_value = mock_manager

        result = self.runner.invoke(main, ['docker', 'login'])
        
        assert result.exit_code == 1

    @patch('owlkit.cli.GHCRManager')
    def test_docker_login_with_token(self, mock_ghcr_class):
        """Test docker login with token parameter."""
        mock_manager = Mock()
        mock_manager.login.return_value = True
        mock_ghcr_class.return_value = mock_manager

        result = self.runner.invoke(main, ['docker', 'login', '--token', 'test-token'])
        
        assert result.exit_code == 0
        mock_manager.login.assert_called_with('test-token')

    @patch('owlkit.cli.GHCRManager')
    def test_docker_build_success(self, mock_ghcr_class):
        """Test successful docker build."""
        mock_manager = Mock()
        mock_manager.build_image.return_value = True
        mock_ghcr_class.return_value = mock_manager

        result = self.runner.invoke(main, ['docker', 'build', '-t', 'test:latest'])
        
        assert result.exit_code == 0
        mock_manager.build_image.assert_called()

    @patch('owlkit.cli.GHCRManager')
    def test_docker_push_success(self, mock_ghcr_class):
        """Test successful docker push."""
        mock_manager = Mock()
        mock_manager.push_image.return_value = True
        mock_ghcr_class.return_value = mock_manager

        result = self.runner.invoke(main, ['docker', 'push', 'test:latest'])
        
        assert result.exit_code == 0
        mock_manager.push_image.assert_called_with('test:latest')

    def test_cwl_help(self):
        """Test CWL subcommand help."""
        result = self.runner.invoke(main, ['cwl', '--help'])
        
        assert result.exit_code == 0
        assert "CWL workflow commands" in result.output
        assert "run" in result.output
        assert "validate" in result.output

    @patch('owlkit.cli.CWLRunner')
    def test_cwl_validate_success(self, mock_cwl_class):
        """Test successful CWL validation."""
        mock_runner = Mock()
        mock_runner.validate_workflow.return_value = True
        mock_cwl_class.return_value = mock_runner

        with self.runner.isolated_filesystem():
            # Create a test workflow file
            with open('test.cwl', 'w') as f:
                f.write('cwlVersion: v1.2\nclass: Workflow')
            
            result = self.runner.invoke(main, ['cwl', 'validate', 'test.cwl'])
        
        assert result.exit_code == 0
        assert "Workflow is valid" in result.output

    @patch('owlkit.cli.CWLRunner')
    def test_cwl_validate_failure(self, mock_cwl_class):
        """Test failed CWL validation."""
        mock_runner = Mock()
        mock_runner.validate_workflow.return_value = False
        mock_cwl_class.return_value = mock_runner

        with self.runner.isolated_filesystem():
            with open('test.cwl', 'w') as f:
                f.write('invalid cwl')
            
            result = self.runner.invoke(main, ['cwl', 'validate', 'test.cwl'])
        
        assert result.exit_code == 1

    @patch('owlkit.cli.CWLRunner')
    def test_cwl_run_success(self, mock_cwl_class):
        """Test successful CWL run."""
        mock_runner = Mock()
        mock_runner.run_workflow.return_value = True
        mock_cwl_class.return_value = mock_runner

        with self.runner.isolated_filesystem():
            with open('test.cwl', 'w') as f:
                f.write('cwlVersion: v1.2\nclass: Workflow')
            
            result = self.runner.invoke(main, [
                'cwl', 'run', 'test.cwl',
                '--metadata-file', 'metadata.json',
                '--files-directory', 'files/',
                '--output-dir', 'outputs/'
            ])
        
        assert result.exit_code == 0
        mock_runner.run_workflow.assert_called()

    def test_sbpack_help(self):
        """Test sbpack subcommand help."""
        result = self.runner.invoke(main, ['sbpack', '--help'])
        
        assert result.exit_code == 0
        assert "Seven Bridges packing commands" in result.output
        assert "login" in result.output
        assert "pack" in result.output
        assert "deploy" in result.output

    @patch('owlkit.cli.SBPackManager')
    def test_sbpack_login_success(self, mock_sbpack_class):
        """Test successful sbpack login."""
        mock_manager = Mock()
        mock_manager.login_to_cgc.return_value = True
        mock_sbpack_class.return_value = mock_manager

        result = self.runner.invoke(main, ['sbpack', 'login'])
        
        assert result.exit_code == 0
        mock_manager.login_to_cgc.assert_called()

    @patch('owlkit.cli.SBPackManager')
    def test_sbpack_login_failure(self, mock_sbpack_class):
        """Test failed sbpack login."""
        mock_manager = Mock()
        mock_manager.login_to_cgc.return_value = False
        mock_sbpack_class.return_value = mock_manager

        result = self.runner.invoke(main, ['sbpack', 'login'])
        
        assert result.exit_code == 1

    @patch('owlkit.cli.SBPackManager')
    def test_sbpack_pack_success(self, mock_sbpack_class):
        """Test successful sbpack pack."""
        mock_manager = Mock()
        mock_manager.check_sbpack_available.return_value = True
        mock_manager.pack_workflow.return_value = "packed.cwl"
        mock_manager.validate_packed_workflow.return_value = True
        mock_sbpack_class.return_value = mock_manager

        with self.runner.isolated_filesystem():
            with open('test.cwl', 'w') as f:
                f.write('cwlVersion: v1.2\nclass: Workflow')
            
            result = self.runner.invoke(main, ['sbpack', 'pack', 'test.cwl', '--validate'])
        
        assert result.exit_code == 0
        mock_manager.pack_workflow.assert_called()
        mock_manager.validate_packed_workflow.assert_called()

    @patch('owlkit.cli.SBPackManager')
    def test_sbpack_pack_auto_install(self, mock_sbpack_class):
        """Test sbpack pack with auto-installation."""
        mock_manager = Mock()
        mock_manager.check_sbpack_available.return_value = False
        mock_manager.install_sbpack.return_value = True
        mock_manager.pack_workflow.return_value = "packed.cwl"
        mock_sbpack_class.return_value = mock_manager

        with self.runner.isolated_filesystem():
            with open('test.cwl', 'w') as f:
                f.write('cwlVersion: v1.2\nclass: Workflow')
            
            result = self.runner.invoke(main, ['sbpack', 'pack', 'test.cwl'])
        
        assert result.exit_code == 0
        mock_manager.install_sbpack.assert_called()

    @patch('owlkit.cli.SBPackManager')
    def test_sbpack_deploy_success(self, mock_sbpack_class):
        """Test successful sbpack deploy."""
        mock_manager = Mock()
        mock_manager.deploy_to_cgc.return_value = True
        mock_sbpack_class.return_value = mock_manager

        with self.runner.isolated_filesystem():
            with open('packed.cwl', 'w') as f:
                f.write('{"cwlVersion": "v1.2", "class": "Workflow"}')
            
            result = self.runner.invoke(main, [
                'sbpack', 'deploy', 'packed.cwl', 'user/project', 'app-name'
            ])
        
        assert result.exit_code == 0
        mock_manager.deploy_to_cgc.assert_called_with('packed.cwl', 'user/project', 'app-name', None)

    @patch('owlkit.cli.SBPackManager')
    def test_sbpack_list_apps_success(self, mock_sbpack_class):
        """Test successful sbpack list-apps."""
        mock_manager = Mock()
        mock_manager.list_apps.return_value = [
            {"id": "app1", "name": "App 1", "revision": 1},
            {"id": "app2", "name": "App 2", "revision": 2}
        ]
        mock_sbpack_class.return_value = mock_manager

        result = self.runner.invoke(main, ['sbpack', 'list-apps', 'user/project'])
        
        assert result.exit_code == 0
        assert "App 1" in result.output
        assert "App 2" in result.output

    @patch('owlkit.cli.SBPackManager')
    def test_sbpack_validate_success(self, mock_sbpack_class):
        """Test successful sbpack validate."""
        mock_manager = Mock()
        mock_manager.validate_packed_workflow.return_value = True
        mock_sbpack_class.return_value = mock_manager

        with self.runner.isolated_filesystem():
            with open('packed.cwl', 'w') as f:
                f.write('{"cwlVersion": "v1.2", "class": "Workflow"}')
            
            result = self.runner.invoke(main, ['sbpack', 'validate', 'packed.cwl'])
        
        assert result.exit_code == 0

    @patch('owlkit.cli.SBPackManager')
    def test_sbpack_install_success(self, mock_sbpack_class):
        """Test successful sbpack install."""
        mock_manager = Mock()
        mock_manager.check_sbpack_available.return_value = False
        mock_manager.install_sbpack.return_value = True
        mock_sbpack_class.return_value = mock_manager

        result = self.runner.invoke(main, ['sbpack', 'install'])
        
        assert result.exit_code == 0
        mock_manager.install_sbpack.assert_called()

    @patch('owlkit.cli.SBPackManager')
    def test_sbpack_install_already_available(self, mock_sbpack_class):
        """Test sbpack install when already available."""
        mock_manager = Mock()
        mock_manager.check_sbpack_available.return_value = True
        mock_sbpack_class.return_value = mock_manager

        result = self.runner.invoke(main, ['sbpack', 'install'])
        
        assert result.exit_code == 0
        assert "already installed" in result.output

    @patch('owlkit.cli.SBPackManager')
    def test_sbpack_logout(self, mock_sbpack_class):
        """Test sbpack logout."""
        mock_manager = Mock()
        mock_manager.cred_manager = Mock()
        mock_sbpack_class.return_value = mock_manager

        result = self.runner.invoke(main, ['sbpack', 'logout'])
        
        assert result.exit_code == 0
        mock_manager.cred_manager.delete_credential.assert_called_with('cgc', 'auth_token')

    def test_test_command(self):
        """Test environment detection command."""
        result = self.runner.invoke(main, ['test'])
        
        assert result.exit_code == 0
        assert "Codespaces Environment Check" in result.output

    def test_invalid_command(self):
        """Test invalid command handling."""
        result = self.runner.invoke(main, ['invalid-command'])
        
        assert result.exit_code != 0
        assert "No such command" in result.output

    def test_missing_required_argument(self):
        """Test missing required argument handling."""
        result = self.runner.invoke(main, ['docker', 'push'])  # Missing image name
        
        assert result.exit_code != 0

    def test_cli_integration_workflow(self):
        """Test complete CLI workflow integration."""
        # This would test a complete workflow but would require more complex mocking
        # For now, we'll just test that the commands are properly wired
        
        # Test that all expected commands exist
        result = self.runner.invoke(main, ['--help'])
        assert "docker" in result.output
        assert "cwl" in result.output
        assert "sbpack" in result.output
        assert "test" in result.output

        # Test subcommand structure
        for subcommand in ['docker', 'cwl', 'sbpack']:
            result = self.runner.invoke(main, [subcommand, '--help'])
            assert result.exit_code == 0