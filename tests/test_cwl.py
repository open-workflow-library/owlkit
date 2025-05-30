"""Tests for CWL workflow operations."""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from owlkit.cwl.runner import CWLRunner


class TestCWLRunner:
    """Test CWL workflow execution and validation."""

    def test_init(self, cwl_runner):
        """Test CWLRunner initialization."""
        assert cwl_runner.console is not None

    def test_validate_workflow_success(self, cwl_runner, sample_cwl_workflow, mock_cwl_commands):
        """Test successful workflow validation."""
        result = cwl_runner.validate_workflow(str(sample_cwl_workflow))
        
        assert result is True
        mock_cwl_commands.assert_called()
        
        call_args = mock_cwl_commands.call_args[0][0]
        assert "cwltool" in call_args
        assert "--validate" in call_args
        assert str(sample_cwl_workflow) in call_args

    def test_validate_workflow_file_not_found(self, cwl_runner):
        """Test workflow validation with non-existent file."""
        result = cwl_runner.validate_workflow("/path/to/nonexistent.cwl")
        
        assert result is False

    def test_validate_workflow_failure(self, cwl_runner, sample_cwl_workflow, mock_subprocess):
        """Test failed workflow validation."""
        mock_subprocess.side_effect = Exception("Validation failed")

        result = cwl_runner.validate_workflow(str(sample_cwl_workflow))
        
        assert result is False

    def test_run_workflow_success(self, cwl_runner, sample_cwl_workflow, temp_dir, mock_cwl_commands):
        """Test successful workflow execution."""
        output_dir = temp_dir / "outputs"
        output_dir.mkdir()
        
        inputs = {
            "input_file": {
                "class": "File",
                "path": str(temp_dir / "input.txt")
            }
        }
        
        # Create input file
        (temp_dir / "input.txt").write_text("test content")
        
        result = cwl_runner.run_workflow(
            workflow_path=str(sample_cwl_workflow),
            inputs=inputs,
            output_dir=str(output_dir)
        )
        
        assert result is True
        mock_cwl_commands.assert_called()

    def test_run_workflow_with_parameters(self, cwl_runner, sample_cwl_workflow, temp_dir, mock_cwl_commands):
        """Test workflow execution with various parameters."""
        output_dir = temp_dir / "outputs"
        output_dir.mkdir()
        
        result = cwl_runner.run_workflow(
            workflow_path=str(sample_cwl_workflow),
            inputs={},
            output_dir=str(output_dir),
            metadata_file=str(temp_dir / "metadata.json"),
            files_directory=str(temp_dir / "files"),
            token_file=str(temp_dir / "token.txt"),
            thread_count=4,
            retry_count=2,
            strict_limits=True
        )
        
        assert result is True
        call_args = mock_cwl_commands.call_args[0][0]
        assert "--metadata-file" in call_args
        assert "--files-directory" in call_args
        assert "--token-file" in call_args
        assert "--thread-count" in call_args
        assert "--retry-count" in call_args
        assert "--strict-limits" in call_args

    def test_run_workflow_file_not_found(self, cwl_runner):
        """Test workflow execution with non-existent workflow file."""
        result = cwl_runner.run_workflow(
            workflow_path="/path/to/nonexistent.cwl",
            inputs={},
            output_dir="/tmp/output"
        )
        
        assert result is False

    def test_run_workflow_failure(self, cwl_runner, sample_cwl_workflow, temp_dir, mock_subprocess):
        """Test failed workflow execution."""
        mock_subprocess.side_effect = Exception("Execution failed")

        result = cwl_runner.run_workflow(
            workflow_path=str(sample_cwl_workflow),
            inputs={},
            output_dir=str(temp_dir / "outputs")
        )
        
        assert result is False

    def test_create_inputs_file(self, cwl_runner, temp_dir):
        """Test inputs file creation."""
        inputs = {
            "input_file": {
                "class": "File",
                "path": "/path/to/file.txt"
            },
            "thread_count": 4
        }
        
        inputs_file = cwl_runner._create_inputs_file(inputs, temp_dir)
        
        assert inputs_file.exists()
        assert inputs_file.suffix == ".json"
        
        with open(inputs_file) as f:
            loaded_inputs = json.load(f)
        
        assert loaded_inputs == inputs

    def test_create_inputs_file_with_metadata(self, cwl_runner, temp_dir):
        """Test inputs file creation with metadata parameters."""
        metadata_file = temp_dir / "metadata.json"
        metadata_file.write_text('{"test": "data"}')
        
        inputs_file = cwl_runner._create_inputs_file(
            inputs={},
            temp_dir=temp_dir,
            metadata_file=str(metadata_file),
            files_directory="/path/to/files",
            token_file="/path/to/token.txt",
            thread_count=8,
            retry_count=3
        )
        
        with open(inputs_file) as f:
            loaded_inputs = json.load(f)
        
        assert loaded_inputs["metadata_file"]["path"] == str(metadata_file)
        assert loaded_inputs["files_directory"]["path"] == "/path/to/files"
        assert loaded_inputs["token_file"]["path"] == "/path/to/token.txt"
        assert loaded_inputs["thread_count"] == 8
        assert loaded_inputs["retry_count"] == 3

    def test_build_cwltool_command(self, cwl_runner, temp_dir):
        """Test CWL tool command building."""
        workflow_path = temp_dir / "workflow.cwl"
        inputs_file = temp_dir / "inputs.json"
        output_dir = temp_dir / "outputs"
        
        cmd = cwl_runner._build_cwltool_command(
            workflow_path=str(workflow_path),
            inputs_file=str(inputs_file),
            output_dir=str(output_dir),
            strict_limits=True
        )
        
        assert "cwltool" in cmd
        assert "--outdir" in cmd
        assert str(output_dir) in cmd
        assert "--strict-limits" in cmd
        assert str(workflow_path) in cmd
        assert str(inputs_file) in cmd

    def test_build_cwltool_command_minimal(self, cwl_runner, temp_dir):
        """Test minimal CWL tool command building."""
        workflow_path = temp_dir / "workflow.cwl"
        inputs_file = temp_dir / "inputs.json"
        output_dir = temp_dir / "outputs"
        
        cmd = cwl_runner._build_cwltool_command(
            workflow_path=str(workflow_path),
            inputs_file=str(inputs_file),
            output_dir=str(output_dir)
        )
        
        assert "cwltool" in cmd
        assert "--outdir" in cmd
        assert "--strict-limits" not in cmd

    def test_list_outputs_success(self, cwl_runner, temp_dir):
        """Test successful output listing."""
        output_dir = temp_dir / "outputs"
        output_dir.mkdir()
        
        # Create some output files
        (output_dir / "result.txt").write_text("result")
        (output_dir / "report.tsv").write_text("report")
        (output_dir / "log.log").write_text("log")
        
        outputs = cwl_runner.list_outputs(str(output_dir))
        
        assert len(outputs) == 3
        assert any(f["name"] == "result.txt" for f in outputs)
        assert any(f["name"] == "report.tsv" for f in outputs)
        assert any(f["name"] == "log.log" for f in outputs)

    def test_list_outputs_empty_directory(self, cwl_runner, temp_dir):
        """Test output listing with empty directory."""
        output_dir = temp_dir / "empty_outputs"
        output_dir.mkdir()
        
        outputs = cwl_runner.list_outputs(str(output_dir))
        
        assert len(outputs) == 0

    def test_list_outputs_nonexistent_directory(self, cwl_runner):
        """Test output listing with non-existent directory."""
        outputs = cwl_runner.list_outputs("/path/to/nonexistent")
        
        assert len(outputs) == 0

    def test_list_outputs_with_subdirectories(self, cwl_runner, temp_dir):
        """Test output listing with subdirectories."""
        output_dir = temp_dir / "outputs"
        output_dir.mkdir()
        
        # Create files and subdirectories
        (output_dir / "result.txt").write_text("result")
        subdir = output_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")
        
        outputs = cwl_runner.list_outputs(str(output_dir))
        
        # Should include both files and directories
        assert len(outputs) >= 2
        assert any(f["name"] == "result.txt" and f["type"] == "file" for f in outputs)
        assert any(f["name"] == "subdir" and f["type"] == "directory" for f in outputs)

    def test_cleanup_temp_files(self, cwl_runner, temp_dir):
        """Test temporary file cleanup."""
        # Create some temporary files
        temp_files = [
            temp_dir / "inputs_123.json",
            temp_dir / "temp_456.txt"
        ]
        
        for temp_file in temp_files:
            temp_file.write_text("temp content")
            assert temp_file.exists()
        
        cwl_runner._cleanup_temp_files(temp_files)
        
        for temp_file in temp_files:
            assert not temp_file.exists()

    def test_validate_inputs(self, cwl_runner):
        """Test input validation."""
        # Valid inputs
        valid_inputs = {
            "input_file": {
                "class": "File",
                "path": "/path/to/file.txt"
            },
            "thread_count": 4
        }
        
        assert cwl_runner._validate_inputs(valid_inputs) is True

        # Invalid inputs
        invalid_inputs = {
            "input_file": "not_a_dict",
            "thread_count": "not_a_number"
        }
        
        assert cwl_runner._validate_inputs(invalid_inputs) is False

    def test_handle_cwltool_output(self, cwl_runner, temp_dir):
        """Test CWL tool output handling."""
        # Mock successful execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "INFO: Workflow completed successfully"
        mock_result.stderr = ""
        
        success = cwl_runner._handle_cwltool_output(mock_result, str(temp_dir))
        assert success is True

        # Mock failed execution
        mock_result.returncode = 1
        mock_result.stderr = "ERROR: Workflow failed"
        
        success = cwl_runner._handle_cwltool_output(mock_result, str(temp_dir))
        assert success is False

    def test_check_cwltool_available(self, cwl_runner, mock_subprocess):
        """Test CWL tool availability check."""
        # cwltool available
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "cwltool 3.1.20210628163208"
        
        assert cwl_runner._check_cwltool_available() is True

        # cwltool not available
        mock_subprocess.side_effect = FileNotFoundError()
        
        assert cwl_runner._check_cwltool_available() is False

    def test_parse_cwl_outputs_json(self, cwl_runner, temp_dir):
        """Test parsing CWL outputs from JSON."""
        outputs_json = {
            "output_file": {
                "class": "File",
                "path": str(temp_dir / "result.txt"),
                "basename": "result.txt",
                "size": 1024
            }
        }
        
        # Create the output file
        (temp_dir / "result.txt").write_text("test result")
        
        outputs_file = temp_dir / "outputs.json"
        outputs_file.write_text(json.dumps(outputs_json))
        
        parsed_outputs = cwl_runner._parse_cwl_outputs(str(outputs_file))
        
        assert len(parsed_outputs) == 1
        assert parsed_outputs[0]["name"] == "result.txt"
        assert parsed_outputs[0]["type"] == "file"