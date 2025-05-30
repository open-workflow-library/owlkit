"""CWL workflow execution wrapper using cwltool."""

import subprocess
import json
import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


class CWLRunner:
    """Manages CWL workflow execution using cwltool."""
    
    def __init__(self, enable_pull: bool = True, strict_limits: bool = False):
        """Initialize CWL runner.
        
        Args:
            enable_pull: Enable Docker image pulling
            strict_limits: Enforce strict memory/CPU limits
        """
        self.enable_pull = enable_pull
        self.strict_limits = strict_limits
        self.console = Console()
        
    def run_workflow(self, 
                    workflow_path: str,
                    job_params: Dict[str, Any],
                    output_dir: Optional[str] = None,
                    additional_args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run a CWL workflow.
        
        Args:
            workflow_path: Path to CWL workflow file
            job_params: Job parameters as dictionary
            output_dir: Output directory (defaults to ./output)
            additional_args: Additional cwltool arguments
            
        Returns:
            Workflow output as dictionary
        """
        if not output_dir:
            output_dir = "./output"
            
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Build cwltool command
        cmd = ["cwltool"]
        
        if self.enable_pull:
            cmd.append("--enable-pull")
            
        if self.strict_limits:
            cmd.extend(["--strict-memory-limit", "--strict-cpu-limit"])
            
        cmd.extend(["--outdir", output_dir])
        
        if additional_args:
            cmd.extend(additional_args)
            
        cmd.append(workflow_path)
        
        # Add job parameters as command line arguments
        for key, value in job_params.items():
            cmd.extend([f"--{key}", str(value)])
            
        self.console.print(f"[bold]Running CWL workflow:[/bold] {workflow_path}")
        self.console.print(f"[dim]Command:[/dim] {' '.join(cmd)}")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Executing workflow...", total=None)
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                progress.update(task, description="[green]Workflow completed!")
                
            self.console.print("[green]✓[/green] Workflow executed successfully")
            
            # Try to parse JSON output
            try:
                output = json.loads(result.stdout.split('\n')[-2])
                return output
            except (json.JSONDecodeError, IndexError):
                # Return raw output if JSON parsing fails
                return {"stdout": result.stdout, "stderr": result.stderr}
                
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗[/red] Workflow failed with exit code: {e.returncode}")
            self.console.print(f"[red]Error output:[/red]\n{e.stderr}")
            raise
            
    def run_workflow_file(self,
                         workflow_path: str,
                         job_file: str,
                         output_dir: Optional[str] = None,
                         additional_args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run a CWL workflow with a job file.
        
        Args:
            workflow_path: Path to CWL workflow file
            job_file: Path to job file (YAML or JSON)
            output_dir: Output directory
            additional_args: Additional cwltool arguments
            
        Returns:
            Workflow output as dictionary
        """
        if not output_dir:
            output_dir = "./output"
            
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        cmd = ["cwltool"]
        
        if self.enable_pull:
            cmd.append("--enable-pull")
            
        if self.strict_limits:
            cmd.extend(["--strict-memory-limit", "--strict-cpu-limit"])
            
        cmd.extend(["--outdir", output_dir])
        
        if additional_args:
            cmd.extend(additional_args)
            
        cmd.extend([workflow_path, job_file])
        
        self.console.print(f"[bold]Running CWL workflow:[/bold] {workflow_path}")
        self.console.print(f"[bold]Job file:[/bold] {job_file}")
        self.console.print(f"[dim]Command:[/dim] {' '.join(cmd)}")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Executing workflow...", total=None)
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                progress.update(task, description="[green]Workflow completed!")
                
            self.console.print("[green]✓[/green] Workflow executed successfully")
            
            try:
                output = json.loads(result.stdout.split('\n')[-2])
                return output
            except (json.JSONDecodeError, IndexError):
                return {"stdout": result.stdout, "stderr": result.stderr}
                
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗[/red] Workflow failed with exit code: {e.returncode}")
            self.console.print(f"[red]Error output:[/red]\n{e.stderr}")
            raise
            
    def validate_workflow(self, workflow_path: str) -> bool:
        """Validate a CWL workflow.
        
        Args:
            workflow_path: Path to CWL workflow file
            
        Returns:
            True if valid
        """
        try:
            result = subprocess.run(
                ["cwltool", "--validate", workflow_path],
                capture_output=True,
                text=True,
                check=True
            )
            self.console.print(f"[green]✓[/green] Workflow {workflow_path} is valid")
            return True
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗[/red] Workflow {workflow_path} is invalid:")
            self.console.print(f"[red]{e.stderr}[/red]")
            return False
            
    def list_outputs(self, output_dir: str) -> List[str]:
        """List output files from a workflow run.
        
        Args:
            output_dir: Output directory to scan
            
        Returns:
            List of output file paths
        """
        output_path = Path(output_dir)
        if not output_path.exists():
            return []
            
        outputs = []
        for file_path in output_path.rglob("*"):
            if file_path.is_file():
                outputs.append(str(file_path))
                
        return sorted(outputs)