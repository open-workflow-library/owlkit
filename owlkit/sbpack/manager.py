"""Seven Bridges sbpack wrapper for packing and deploying CWL workflows."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config.credentials import CredentialManager

console = Console()


class SBPackManager:
    """Manages Seven Bridges sbpack operations for CWL workflow packing and deployment."""
    
    def __init__(self):
        self.console = console
        self.cred_manager = CredentialManager()
        
    def check_sbpack_available(self) -> bool:
        """Check if sbpack is available in the system."""
        try:
            result = subprocess.run(['sbpack', '--version'], 
                                  capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def pack_workflow(self, 
                     cwl_file: str, 
                     output_file: Optional[str] = None,
                     include_secondary_files: bool = True) -> str:
        """Pack a CWL workflow for Seven Bridges platform.
        
        Args:
            cwl_file: Path to the CWL workflow file
            output_file: Output packed workflow filename (optional)
            include_secondary_files: Include secondary files in the package
            
        Returns:
            Path to the packed workflow file
        """
        if not self.check_sbpack_available():
            raise RuntimeError("sbpack is not available. Please install sbpack first.")
        
        cwl_path = Path(cwl_file)
        if not cwl_path.exists():
            raise FileNotFoundError(f"CWL file not found: {cwl_file}")
        
        # Determine output filename
        if not output_file:
            output_file = f"{cwl_path.stem}-packed.cwl"
        
        output_path = Path(output_file)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(f"Packing {cwl_path.name}...", total=None)
            
            try:
                # Build sbpack command
                cmd = ['sbpack', str(cwl_path)]
                
                # Add output option
                if output_file:
                    cmd.extend(['--output', str(output_path)])
                
                # Execute sbpack
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                progress.update(task, description=f"✓ Packed {cwl_path.name}")
                
                self.console.print(f"\n[bold green]Successfully packed workflow![/bold green]")
                self.console.print(f"Input:  {cwl_path}")
                self.console.print(f"Output: {output_path}")
                
                return str(output_path)
                
            except subprocess.CalledProcessError as e:
                progress.update(task, description=f"✗ Failed to pack {cwl_path.name}")
                self.console.print(f"\n[bold red]sbpack failed:[/bold red] {e.stderr}")
                raise
    
    def validate_packed_workflow(self, packed_file: str) -> bool:
        """Validate a packed CWL workflow.
        
        Args:
            packed_file: Path to the packed workflow file
            
        Returns:
            True if validation passes, False otherwise
        """
        packed_path = Path(packed_file)
        if not packed_path.exists():
            self.console.print(f"[bold red]Packed file not found: {packed_file}[/bold red]")
            return False
        
        try:
            # Try to parse as JSON (packed workflows are typically JSON)
            with open(packed_path, 'r') as f:
                workflow_data = json.load(f)
            
            # Basic validation checks
            if 'cwlVersion' not in workflow_data:
                self.console.print("[bold yellow]Warning: No cwlVersion found in packed workflow[/bold yellow]")
            
            if 'class' not in workflow_data:
                self.console.print("[bold red]Error: No class field found in packed workflow[/bold red]")
                return False
            
            self.console.print(f"[bold green]✓ Packed workflow validation passed[/bold green]")
            self.console.print(f"  - Class: {workflow_data.get('class', 'Unknown')}")
            self.console.print(f"  - CWL Version: {workflow_data.get('cwlVersion', 'Unknown')}")
            
            return True
            
        except json.JSONDecodeError as e:
            self.console.print(f"[bold red]Invalid JSON in packed workflow: {e}[/bold red]")
            return False
        except Exception as e:
            self.console.print(f"[bold red]Validation error: {e}[/bold red]")
            return False
    
    def login_to_cgc(self, token: Optional[str] = None, force_new: bool = False) -> bool:
        """Login to Cancer Genomics Cloud and store credentials.
        
        Args:
            token: CGC authentication token (optional, will prompt if not provided)
            force_new: Force new token input even if one is stored
            
        Returns:
            True if login succeeds, False otherwise
        """
        # Get or prompt for token
        if not token:
            if force_new:
                token = self.cred_manager.prompt_and_store(
                    'cgc', 'auth_token', 
                    'Enter your CGC Authentication Token: '
                )
            else:
                # Check for stored token first
                stored_token = self.cred_manager.get_credential('cgc', 'auth_token')
                if stored_token:
                    use_stored = input("Found stored CGC token. Use it? [Y/n]: ")
                    if use_stored.lower() != 'n':
                        token = stored_token
                    else:
                        token = self.cred_manager.prompt_and_store(
                            'cgc', 'auth_token',
                            'Enter your CGC Authentication Token: '
                        )
                else:
                    token = self.cred_manager.prompt_and_store(
                        'cgc', 'auth_token',
                        'Enter your CGC Authentication Token: '
                    )
        
        # Test the token by trying to list projects
        try:
            cmd = ['sb', 'projects', 'list', '--format', 'json']
            env = os.environ.copy()
            env['SB_AUTH_TOKEN'] = token
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Testing CGC connection...", total=None)
                
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                      check=True, env=env)
                
                progress.update(task, description="✓ CGC connection verified")
            
            # Store the token if it works and wasn't already stored
            stored_token = self.cred_manager.get_credential('cgc', 'auth_token')
            if not stored_token or stored_token != token:
                self.cred_manager.set_credential('cgc', 'auth_token', token)
                self.console.print(f"\n[bold green]Successfully authenticated to CGC![/bold green]")
                self.console.print("Token stored securely for future use.")
            else:
                self.console.print(f"\n[bold green]CGC authentication verified![/bold green]")
                
            return True
            
        except subprocess.CalledProcessError as e:
            self.console.print(f"\n[bold red]CGC authentication failed:[/bold red] {e.stderr}")
            return False
    
    def get_stored_token(self) -> Optional[str]:
        """Get stored CGC token."""
        return self.cred_manager.get_credential('cgc', 'auth_token')
    
    def deploy_to_cgc(self, 
                     packed_file: str,
                     project_id: str,
                     app_name: str,
                     token: Optional[str] = None) -> bool:
        """Deploy a packed workflow to Cancer Genomics Cloud.
        
        Args:
            packed_file: Path to the packed workflow file
            project_id: CGC project ID (e.g., 'username/project-name')
            app_name: Name for the app on CGC
            token: CGC authentication token (optional, can use environment variable)
            
        Returns:
            True if deployment succeeds, False otherwise
        """
        # Check if sb-cli is available for deployment
        try:
            subprocess.run(['sb', '--version'], 
                          capture_output=True, text=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.console.print("[bold red]sb-cli not available. Cannot deploy to CGC.[/bold red]")
            self.console.print("Please install Seven Bridges CLI: https://docs.sevenbridges.com/docs/command-line-interface")
            return False
        
        packed_path = Path(packed_file)
        if not packed_path.exists():
            self.console.print(f"[bold red]Packed file not found: {packed_file}[/bold red]")
            return False
        
        # Validate before deployment
        if not self.validate_packed_workflow(packed_file):
            self.console.print("[bold red]Packed workflow validation failed. Aborting deployment.[/bold red]")
            return False
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(f"Deploying {app_name} to CGC...", total=None)
            
            try:
                # Build sb command for app creation
                cmd = [
                    'sb', 'apps', 'create',
                    '--project', project_id,
                    '--name', app_name,
                    '--cwl', str(packed_path)
                ]
                
                # Get token (from parameter, stored, or environment)
                if not token:
                    token = self.get_stored_token()
                
                env = os.environ.copy()
                if token:
                    env['SB_AUTH_TOKEN'] = token
                elif 'SB_AUTH_TOKEN' not in env:
                    self.console.print("[bold yellow]No CGC token found. Please login first with:[/bold yellow]")
                    self.console.print("  owlkit sbpack login")
                    return False
                
                # Execute deployment
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                      check=True, env=env)
                
                progress.update(task, description=f"✓ Deployed {app_name}")
                
                self.console.print(f"\n[bold green]Successfully deployed to CGC![/bold green]")
                self.console.print(f"Project: {project_id}")
                self.console.print(f"App: {app_name}")
                
                return True
                
            except subprocess.CalledProcessError as e:
                progress.update(task, description=f"✗ Failed to deploy {app_name}")
                self.console.print(f"\n[bold red]Deployment failed:[/bold red] {e.stderr}")
                return False
    
    def list_apps(self, project_id: str, token: Optional[str] = None) -> List[Dict]:
        """List apps in a CGC project.
        
        Args:
            project_id: CGC project ID
            token: CGC authentication token (optional)
            
        Returns:
            List of app dictionaries
        """
        try:
            cmd = ['sb', 'apps', 'list', '--project', project_id, '--format', 'json']
            
            # Get token (from parameter, stored, or environment)
            if not token:
                token = self.get_stored_token()
            
            env = os.environ.copy()
            if token:
                env['SB_AUTH_TOKEN'] = token
            elif 'SB_AUTH_TOKEN' not in env:
                self.console.print("[bold yellow]No CGC token found. Please login first with:[/bold yellow]")
                self.console.print("  owlkit sbpack login")
                return []
            
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  check=True, env=env)
            
            apps = json.loads(result.stdout)
            return apps
            
        except subprocess.CalledProcessError as e:
            self.console.print(f"[bold red]Failed to list apps: {e.stderr}[/bold red]")
            return []
        except json.JSONDecodeError:
            self.console.print("[bold red]Failed to parse app list response[/bold red]")
            return []
    
    def install_sbpack(self) -> bool:
        """Attempt to install sbpack using pip."""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Installing sbpack...", total=None)
                
                # Try to install sbpack via pip
                result = subprocess.run(['pip', 'install', 'sbpack'], 
                                      capture_output=True, text=True, check=True)
                
                progress.update(task, description="✓ sbpack installed")
                
                self.console.print("\n[bold green]sbpack installed successfully![/bold green]")
                return True
                
        except subprocess.CalledProcessError as e:
            self.console.print(f"\n[bold red]Failed to install sbpack:[/bold red] {e.stderr}")
            self.console.print("\nPlease install manually:")
            self.console.print("  pip install sbpack")
            return False
        except FileNotFoundError:
            self.console.print("[bold red]pip not found. Please install Python pip first.[/bold red]")
            return False