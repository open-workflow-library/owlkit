"""Seven Bridges sbpack wrapper for packing and deploying CWL workflows."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm

from ..config.credentials import CredentialManager

console = Console()


# Platform configurations
PLATFORMS = {
    'cgc': {
        'name': 'Cancer Genomics Cloud',
        'api_endpoint': 'https://cgc-api.sbgenomics.com/v2',
        'description': 'NCI Cancer Genomics Cloud for cancer research'
    },
    'sbg-us': {
        'name': 'Seven Bridges Platform (US)',
        'api_endpoint': 'https://api.sbgenomics.com/v2',
        'description': 'Seven Bridges Platform - US region'
    },
    'sbg-eu': {
        'name': 'Seven Bridges Platform (EU)',
        'api_endpoint': 'https://eu-api.sbgenomics.com/v2',
        'description': 'Seven Bridges Platform - EU region'
    },
    'biodata-catalyst': {
        'name': 'BioData Catalyst',
        'api_endpoint': 'https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2',
        'description': 'NHLBI BioData Catalyst powered by Seven Bridges'
    },
    'cavatica': {
        'name': 'Cavatica',
        'api_endpoint': 'https://cavatica-api.sbgenomics.com/v2',
        'description': 'Pediatric data platform for childhood diseases'
    }
}


class SBPackManager:
    """Manages Seven Bridges sbpack operations for CWL workflow packing and deployment."""
    
    def __init__(self):
        self.console = console
        self.cred_manager = CredentialManager()
        self.platforms = PLATFORMS
        
    def check_sbpack_available(self) -> bool:
        """Check if sbpack is available in the system."""
        try:
            result = subprocess.run(['sbpack', '--help'], 
                                  capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def pack_workflow(self, 
                     cwl_file: str, 
                     output_file: Optional[str] = None,
                     include_secondary_files: bool = True) -> str:
        """Prepare a CWL workflow for Seven Bridges platform.
        
        Since we're using the Python SDK for deployment, we don't need 
        actual packing - just validation and copying the file.
        
        Args:
            cwl_file: Path to the CWL workflow file
            output_file: Output workflow filename (optional)
            include_secondary_files: Include secondary files in the package
            
        Returns:
            Path to the prepared workflow file
        """
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
            task = progress.add_task(f"Preparing {cwl_path.name}...", total=None)
            
            try:
                # Simply copy the workflow file (no actual packing needed for Python SDK)
                import shutil
                shutil.copy2(cwl_path, output_path)
                
                progress.update(task, description=f"✓ Prepared {cwl_path.name}")
                
                self.console.print(f"\n[bold green]Successfully prepared workflow![/bold green]")
                self.console.print(f"Input:  {cwl_path}")
                self.console.print(f"Output: {output_path}")
                
                return str(output_path)
                
            except Exception as e:
                progress.update(task, description=f"✗ Failed to prepare {cwl_path.name}")
                self.console.print(f"\n[bold red]Preparation failed:[/bold red] {str(e)}")
                raise
    
    def validate_packed_workflow(self, packed_file: str) -> bool:
        """Validate a CWL workflow file.
        
        Args:
            packed_file: Path to the workflow file
            
        Returns:
            True if validation passes, False otherwise
        """
        packed_path = Path(packed_file)
        if not packed_path.exists():
            self.console.print(f"[bold red]Workflow file not found: {packed_file}[/bold red]")
            return False
        
        try:
            import yaml
            
            with open(packed_path, 'r') as f:
                content = f.read()
            
            # Try to parse as YAML first (CWL files are usually YAML)
            try:
                workflow_data = yaml.safe_load(content)
            except yaml.YAMLError:
                # If YAML fails, try JSON
                try:
                    workflow_data = json.loads(content)
                except json.JSONDecodeError as e:
                    self.console.print(f"[bold red]Invalid YAML/JSON in workflow: {e}[/bold red]")
                    return False
            
            # Basic validation checks
            if not isinstance(workflow_data, dict):
                self.console.print("[bold red]Error: Workflow must be a valid object[/bold red]")
                return False
                
            if 'cwlVersion' not in workflow_data:
                self.console.print("[bold yellow]Warning: No cwlVersion found in workflow[/bold yellow]")
            
            if 'class' not in workflow_data:
                self.console.print("[bold red]Error: No class field found in workflow[/bold red]")
                return False
            
            self.console.print(f"[bold green]✓ Workflow validation passed[/bold green]")
            self.console.print(f"  - Class: {workflow_data.get('class', 'Unknown')}")
            self.console.print(f"  - CWL Version: {workflow_data.get('cwlVersion', 'Unknown')}")
            
            return True
            
        except Exception as e:
            self.console.print(f"[bold red]Validation error: {e}[/bold red]")
            return False
    
    def login_to_platform(self, 
                         platform: str = 'cgc',
                         token: Optional[str] = None, 
                         force_new: bool = False,
                         non_interactive: bool = False) -> bool:
        """Login to a Seven Bridges platform and store credentials.
        
        Args:
            platform: Platform to login to (cgc, sbg-us, sbg-eu, biodata-catalyst, cavatica)
            token: Authentication token (optional, will prompt if not provided)
            force_new: Force new token input even if one is stored
            non_interactive: If True, never prompt for input (fail if no token provided)
            
        Returns:
            True if login succeeds, False otherwise
        """
        # Validate platform
        if platform not in self.platforms:
            self.console.print(f"[bold red]Unknown platform: {platform}[/bold red]")
            self.console.print(f"Available platforms: {', '.join(self.platforms.keys())}")
            return False
            
        platform_info = self.platforms[platform]
        
        # Get or prompt for token
        if not token:
            if non_interactive:
                # In non-interactive mode, check for stored token only
                token = self.cred_manager.get_credential(platform, 'auth_token')
                if not token:
                    self.console.print(f"[bold red]No token provided and no stored token found for {platform}[/bold red]")
                    return False
            else:
                # Interactive mode
                if force_new:
                    token = self.cred_manager.prompt_and_store(
                        platform, 'auth_token', 
                        f'Enter your {platform_info["name"]} Authentication Token: '
                    )
                else:
                    # Check for stored token first
                    stored_token = self.cred_manager.get_credential(platform, 'auth_token')
                    if stored_token:
                        use_stored = input(f"Found stored {platform} token. Use it? [Y/n]: ")
                        if use_stored.lower() != 'n':
                            token = stored_token
                        else:
                            token = self.cred_manager.prompt_and_store(
                                platform, 'auth_token',
                                f'Enter your {platform_info["name"]} Authentication Token: '
                            )
                    else:
                        token = self.cred_manager.prompt_and_store(
                            platform, 'auth_token',
                            f'Enter your {platform_info["name"]} Authentication Token: '
                        )
        
        # Test the token by trying to list projects
        try:
            import sevenbridges as sbg
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task(f"Testing {platform_info['name']} connection...", total=None)
                
                # Initialize API client
                api = sbg.Api(token=token, url=platform_info['api_endpoint'])
                
                # Test connection by listing projects
                projects = api.projects.query(limit=1)
                list(projects)  # Force evaluation
                
                progress.update(task, description=f"✓ {platform_info['name']} connection verified")
            
            # Store the token if it works and wasn't already stored
            stored_token = self.cred_manager.get_credential(platform, 'auth_token')
            if not stored_token or stored_token != token:
                self.cred_manager.set_credential(platform, 'auth_token', token)
                # Also update credentials file
                self._setup_sbpack_credentials(token, platform)
                self.console.print(f"\n[bold green]Successfully authenticated to {platform_info['name']}![/bold green]")
                self.console.print("Token stored securely for future use.")
                self.console.print("Ready for sbpack deployment operations.")
            else:
                self.console.print(f"\n[bold green]{platform_info['name']} authentication verified![/bold green]")
                
            return True
            
        except Exception as e:
            self.console.print(f"\n[bold red]{platform_info['name']} authentication failed:[/bold red] {str(e)}")
            return False
    
    def login_to_cgc(self, token: Optional[str] = None, force_new: bool = False) -> bool:
        """Legacy method for backward compatibility. Use login_to_platform instead."""
        return self.login_to_platform('cgc', token, force_new)
    
    def get_stored_token(self, platform: str = 'cgc') -> Optional[str]:
        """Get stored token for a platform."""
        return self.cred_manager.get_credential(platform, 'auth_token')
    
    def configure_platforms(self) -> None:
        """Interactive configuration for platform tokens."""
        self.console.print("\n[bold blue]Seven Bridges Platform Configuration[/bold blue]\n")
        self.console.print("This will help you configure authentication tokens for different Seven Bridges platforms.")
        self.console.print("You can skip platforms you don't use.\n")
        
        # Create a table showing available platforms
        table = Table(title="Available Platforms")
        table.add_column("Platform ID", style="cyan")
        table.add_column("Platform Name", style="green")
        table.add_column("Description", style="white")
        
        for platform_id, info in self.platforms.items():
            table.add_row(platform_id, info['name'], info['description'])
        
        self.console.print(table)
        self.console.print()
        
        # Configure each platform
        for platform_id, info in self.platforms.items():
            self.console.print(f"\n[bold cyan]Configure {info['name']} ({platform_id})[/bold cyan]")
            
            # Check if token already exists
            existing_token = self.get_stored_token(platform_id)
            if existing_token:
                update = Confirm.ask(f"Token already exists for {platform_id}. Update it?", default=False)
                if not update:
                    continue
            else:
                configure = Confirm.ask(f"Configure {info['name']}?", default=True)
                if not configure:
                    self.console.print(f"[yellow]Skipping {platform_id}[/yellow]")
                    continue
            
            # Get token
            token = Prompt.ask(f"Enter your {info['name']} authentication token", password=True)
            
            if token:
                # Test the token
                self.console.print(f"Testing connection to {info['name']}...")
                if self._test_platform_token(platform_id, token):
                    # Store in credentials manager
                    self.cred_manager.set_credential(platform_id, 'auth_token', token)
                    # Also update credentials file
                    self._setup_sbpack_credentials(token, platform_id)
                    self.console.print(f"[green]✓ Successfully configured {platform_id}[/green]")
                else:
                    self.console.print(f"[red]✗ Failed to validate token for {platform_id}[/red]")
            else:
                self.console.print(f"[yellow]No token provided for {platform_id}[/yellow]")
        
        self.console.print("\n[bold green]Configuration complete![/bold green]")
        self.console.print("\nYou can now use these platforms with the --platform flag:")
        self.console.print("  owlkit sbpack deploy workflow.cwl project/name app-name --platform cgc")
        self.console.print("  owlkit sbpack list-apps project-name --platform sbg-us")
    
    def _test_platform_token(self, platform: str, token: str) -> bool:
        """Test if a token is valid for a platform."""
        try:
            import sevenbridges as sbg
            
            platform_info = self.platforms.get(platform)
            if not platform_info:
                return False
            
            # Initialize API client
            api = sbg.Api(token=token, url=platform_info['api_endpoint'])
            
            # Test connection by listing projects
            projects = api.projects.query(limit=1)
            list(projects)  # Force evaluation
            
            return True
        except Exception:
            return False
    
    def _setup_sbpack_credentials(self, token: str, profile_name: str = "cgc") -> bool:
        """Setup Seven Bridges credentials file for sbpack.
        
        Args:
            token: CGC authentication token
            profile_name: Profile name to use (default: cgc)
            
        Returns:
            True if setup succeeds, False otherwise
        """
        try:
            # Create .sevenbridges directory
            sb_dir = Path.home() / ".sevenbridges"
            sb_dir.mkdir(exist_ok=True, mode=0o700)
            
            credentials_file = sb_dir / "credentials"
            
            # Check if credentials file exists and read existing content
            existing_content = ""
            if credentials_file.exists():
                with open(credentials_file, 'r') as f:
                    existing_content = f.read()
            
            # Create/update the profile section
            profile_section = f"""
[{profile_name}]
api_endpoint = https://cgc-api.sbgenomics.com/v2
auth_token = {token}
"""
            
            # Check if this profile already exists
            import configparser
            config = configparser.ConfigParser()
            
            if existing_content:
                config.read_string(existing_content)
            
            # Update or add the profile
            if not config.has_section(profile_name):
                config.add_section(profile_name)
            
            # Get the API endpoint for this platform
            platform_info = self.platforms.get(profile_name, {})
            api_endpoint = platform_info.get('api_endpoint', 'https://cgc-api.sbgenomics.com/v2')
            
            config.set(profile_name, 'api_endpoint', api_endpoint)
            config.set(profile_name, 'auth_token', token)
            
            # Write the updated configuration
            with open(credentials_file, 'w') as f:
                config.write(f)
            
            # Secure the credentials file
            os.chmod(credentials_file, 0o600)
            
            return True
            
        except Exception as e:
            self.console.print(f"[bold red]Failed to setup sbpack credentials: {e}[/bold red]")
            return False

    def deploy_to_cgc(self, 
                     packed_file: str,
                     project_id: str,
                     app_name: str,
                     token: Optional[str] = None,
                     platform: str = 'cgc',
                     non_interactive: bool = False) -> bool:
        """Deploy a workflow to a Seven Bridges platform using sbpack.
        
        Args:
            packed_file: Path to the workflow file
            project_id: Project ID (e.g., 'username/project-name')
            app_name: Name for the app
            token: Authentication token (optional, can use stored token)
            platform: Platform to deploy to (cgc, sbg-us, sbg-eu, biodata-catalyst, cavatica)
            non_interactive: If True, fail instead of prompting for missing credentials
            
        Returns:
            True if deployment succeeds, False otherwise
        """
        if not self.check_sbpack_available():
            self.console.print("[bold red]sbpack not available. Please install sbpack first.[/bold red]")
            return False
        
        packed_path = Path(packed_file)
        if not packed_path.exists():
            self.console.print(f"[bold red]Workflow file not found: {packed_file}[/bold red]")
            return False
        
        # Validate before deployment
        if not self.validate_packed_workflow(packed_file):
            self.console.print("[bold red]Workflow validation failed. Aborting deployment.[/bold red]")
            return False
        
        # Validate platform
        if platform not in self.platforms:
            self.console.print(f"[bold red]Unknown platform: {platform}[/bold red]")
            self.console.print(f"Available platforms: {', '.join(self.platforms.keys())}")
            return False
        
        platform_info = self.platforms[platform]
        
        # Get token (from parameter, stored, or environment)
        if not token:
            token = self.get_stored_token(platform)
        
        # Check environment variable as fallback
        if not token:
            import os
            env_var_name = f"SB_{platform.upper().replace('-', '_')}_TOKEN"
            token = os.environ.get(env_var_name)
            if token:
                self.console.print(f"[dim]Using token from environment variable {env_var_name}[/dim]")
        
        if not token:
            if non_interactive:
                self.console.print(f"[bold red]No {platform} token found and running in non-interactive mode.[/bold red]")
                self.console.print(f"[dim]Set token via environment variable SB_{platform.upper().replace('-', '_')}_TOKEN[/dim]")
                return False
            else:
                self.console.print(f"[bold yellow]No {platform} token found. Please configure first with:[/bold yellow]")
                self.console.print("  owlkit sbpack configure")
                self.console.print("  or")
                self.console.print(f"  owlkit sbpack login --platform {platform}")
                return False

        # Setup sbpack credentials file
        if not self._setup_sbpack_credentials(token, platform):
            return False

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(f"Deploying {app_name} to {platform_info['name']}...", total=None)
            
            try:
                # Setup sbpack command: sbpack profile appid cwl_path
                profile_name = platform
                app_id = f"{project_id}/{app_name}"
                
                cmd = ['sbpack', profile_name, app_id, str(packed_path)]
                
                # Execute sbpack deployment
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                progress.update(task, description=f"✓ Deployed {app_name}")
                
                self.console.print(f"\n[bold green]Successfully deployed to {platform_info['name']}![/bold green]")
                self.console.print(f"Platform: {platform} ({platform_info['name']})")
                self.console.print(f"Project: {project_id}")
                self.console.print(f"App: {app_name}")
                self.console.print(f"App ID: {app_id}")
                
                if result.stdout:
                    self.console.print(f"[green]Output:[/green] {result.stdout}")
                
                return True
                
            except subprocess.CalledProcessError as e:
                progress.update(task, description=f"✗ Failed to deploy {app_name}")
                self.console.print(f"\n[bold red]Deployment failed:[/bold red]")
                if e.stdout:
                    self.console.print(f"[yellow]stdout:[/yellow] {e.stdout}")
                if e.stderr:
                    self.console.print(f"[red]stderr:[/red] {e.stderr}")
                return False
            except Exception as e:
                progress.update(task, description=f"✗ Failed to deploy {app_name}")
                self.console.print(f"\n[bold red]Deployment failed:[/bold red] {str(e)}")
                return False
    
    def list_apps(self, project_id: str, token: Optional[str] = None, platform: str = 'cgc', non_interactive: bool = False) -> List[Dict]:
        """List apps in a project on a Seven Bridges platform.
        
        Args:
            project_id: Project ID
            token: Authentication token (optional)
            platform: Platform to query (cgc, sbg-us, sbg-eu, biodata-catalyst, cavatica)
            non_interactive: If True, fail instead of prompting for missing credentials
            
        Returns:
            List of app dictionaries
        """
        # Validate platform
        if platform not in self.platforms:
            self.console.print(f"[bold red]Unknown platform: {platform}[/bold red]")
            self.console.print(f"Available platforms: {', '.join(self.platforms.keys())}")
            return []
        
        platform_info = self.platforms[platform]
        
        # Get token (from parameter, stored, or environment)
        if not token:
            token = self.get_stored_token(platform)
        
        # Check environment variable as fallback
        if not token:
            import os
            env_var_name = f"SB_{platform.upper().replace('-', '_')}_TOKEN"
            token = os.environ.get(env_var_name)
            if token and not non_interactive:
                self.console.print(f"[dim]Using token from environment variable {env_var_name}[/dim]")
        
        if not token:
            if non_interactive:
                # Silent failure in non-interactive mode
                return []
            else:
                self.console.print(f"[bold yellow]No {platform} token found. Please configure first with:[/bold yellow]")
                self.console.print("  owlkit sbpack configure")
                return []
        
        try:
            import sevenbridges as sbg
            
            # Initialize API client with platform-specific endpoint
            api = sbg.Api(token=token, url=platform_info['api_endpoint'])
            
            # List apps in the project
            apps = api.apps.query(project=project_id)
            
            # Convert to list of dictionaries
            app_list = []
            for app in apps:
                app_list.append({
                    'id': app.id,
                    'name': app.name,
                    'revision': app.revision,
                    'project': app.project
                })
            
            return app_list
            
        except Exception as e:
            self.console.print(f"[bold red]Failed to list apps: {str(e)}[/bold red]")
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