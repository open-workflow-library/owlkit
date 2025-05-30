"""Pytest configuration and fixtures for owlkit tests."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from owlkit.config.credentials import CredentialManager
from owlkit.docker.ghcr import GHCRManager
from owlkit.cwl.runner import CWLRunner
from owlkit.sbpack.manager import SBPackManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config_dir(temp_dir):
    """Mock configuration directory."""
    config_dir = temp_dir / ".owlkit"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def credential_manager(mock_config_dir):
    """Create a CredentialManager with temporary config directory."""
    return CredentialManager(config_dir=mock_config_dir)


@pytest.fixture
def ghcr_manager():
    """Create a GHCRManager instance."""
    return GHCRManager()


@pytest.fixture
def cwl_runner():
    """Create a CWLRunner instance."""
    return CWLRunner()


@pytest.fixture
def sbpack_manager():
    """Create a SBPackManager instance."""
    return SBPackManager()


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for testing."""
    with patch('subprocess.run') as mock:
        yield mock


@pytest.fixture
def mock_keyring():
    """Mock keyring operations."""
    with patch('keyring.get_password') as mock_get, \
         patch('keyring.set_password') as mock_set, \
         patch('keyring.delete_password') as mock_delete:
        yield {
            'get': mock_get,
            'set': mock_set,
            'delete': mock_delete
        }


@pytest.fixture
def sample_cwl_workflow(temp_dir):
    """Create a sample CWL workflow for testing."""
    cwl_content = """
cwlVersion: v1.2
class: Workflow

inputs:
  input_file:
    type: File
    doc: "Input file"

outputs:
  output_file:
    type: File
    outputSource: step1/output

steps:
  step1:
    run:
      class: CommandLineTool
      baseCommand: ["echo", "hello"]
      inputs:
        input:
          type: File
          inputBinding:
            position: 1
      outputs:
        output:
          type: stdout
      stdout: output.txt
    in:
      input: input_file
    out: [output]
"""
    cwl_file = temp_dir / "test_workflow.cwl"
    cwl_file.write_text(cwl_content.strip())
    return cwl_file


@pytest.fixture
def sample_packed_workflow(temp_dir):
    """Create a sample packed CWL workflow for testing."""
    packed_content = {
        "cwlVersion": "v1.2",
        "class": "Workflow",
        "$graph": [
            {
                "class": "Workflow",
                "id": "#main",
                "inputs": [
                    {
                        "id": "#main/input_file",
                        "type": "File"
                    }
                ],
                "outputs": [
                    {
                        "id": "#main/output_file",
                        "type": "File",
                        "outputSource": "#main/step1/output"
                    }
                ],
                "steps": [
                    {
                        "id": "#main/step1",
                        "in": [
                            {
                                "id": "#main/step1/input",
                                "source": "#main/input_file"
                            }
                        ],
                        "out": [
                            "#main/step1/output"
                        ],
                        "run": "#step1.cwl"
                    }
                ]
            }
        ]
    }
    
    import json
    packed_file = temp_dir / "test_packed_workflow.cwl"
    packed_file.write_text(json.dumps(packed_content, indent=2))
    return packed_file


@pytest.fixture
def mock_environment():
    """Mock environment variables."""
    env_vars = {
        'GITHUB_TOKEN': 'fake-github-token',
        'GITHUB_USER': 'testuser',
        'GITHUB_ACTOR': 'testuser',
        'GITHUB_REPOSITORY_OWNER': 'testorg',
        'CODESPACES': 'true',
        'SB_AUTH_TOKEN': 'fake-sb-token'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_docker_commands(mock_subprocess):
    """Mock docker command responses."""
    def side_effect(cmd, **kwargs):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        
        if cmd[0] == 'docker':
            if 'login' in cmd:
                mock_result.stdout = "Login Succeeded"
            elif 'build' in cmd:
                mock_result.stdout = "Successfully built abc123"
            elif 'push' in cmd:
                mock_result.stdout = "The push refers to repository"
            elif 'pull' in cmd:
                mock_result.stdout = "Pull complete"
            elif 'images' in cmd:
                mock_result.stdout = "REPOSITORY    TAG    IMAGE ID    CREATED    SIZE"
        
        return mock_result
    
    mock_subprocess.side_effect = side_effect
    return mock_subprocess


@pytest.fixture
def mock_cwl_commands(mock_subprocess):
    """Mock CWL command responses."""
    def side_effect(cmd, **kwargs):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        
        if 'cwltool' in cmd:
            if '--validate' in cmd:
                mock_result.stdout = "Workflow is valid"
            else:
                mock_result.stdout = "Workflow executed successfully"
        
        return mock_result
    
    mock_subprocess.side_effect = side_effect
    return mock_subprocess


@pytest.fixture
def mock_sbpack_commands(mock_subprocess):
    """Mock sbpack and sb command responses."""
    def side_effect(cmd, **kwargs):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        
        if cmd[0] == 'sbpack':
            if '--version' in cmd:
                mock_result.stdout = "sbpack 2024.12.17"
            else:
                mock_result.stdout = "Packing complete"
        elif cmd[0] == 'sb':
            if 'projects' in cmd and 'list' in cmd:
                mock_result.stdout = '[{"id": "test/project", "name": "Test Project"}]'
            elif 'apps' in cmd:
                if 'create' in cmd:
                    mock_result.stdout = "App created successfully"
                elif 'list' in cmd:
                    mock_result.stdout = '[{"id": "test/app", "name": "Test App", "revision": 1}]'
        elif cmd[0] == 'pip' and 'install' in cmd and 'sbpack' in cmd:
            mock_result.stdout = "Successfully installed sbpack"
        
        return mock_result
    
    mock_subprocess.side_effect = side_effect
    return mock_subprocess