"""GitHub Container Registry (ghcr.io) management."""

import subprocess
import json
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from ..config.credentials import CredentialManager
from rich.console import Console
from rich.table import Table


class GHCRManager:
    """Manages Docker operations with GitHub Container Registry."""
    
    REGISTRY = "ghcr.io"
    
    def __init__(self, username: Optional[str] = None):
        """Initialize GHCR manager.
        
        Args:
            username: GitHub username. If not provided, will prompt when needed.
        """
        self.username = username
        self.cred_manager = CredentialManager()
        self.console = Console()
        self._authenticated = False
        
    def _get_username(self) -> str:
        """Get GitHub username, checking environment or prompting if necessary."""
        if not self.username:
            # Check for Codespaces/GitHub environment
            self.username = (
                os.environ.get('GITHUB_USER') or 
                os.environ.get('GITHUB_ACTOR') or
                os.environ.get('GITHUB_REPOSITORY_OWNER')
            )
            
            if self.username:
                self.console.print(f"[green]Detected GitHub username:[/green] {self.username}")
            else:
                self.username = input("Enter your GitHub username: ")
                
        return self.username
    
    def login(self, token: Optional[str] = None) -> bool:
        """Login to GitHub Container Registry.
        
        Args:
            token: GitHub Personal Access Token. If not provided, will check 
                   for GITHUB_TOKEN env var (Codespaces), stored credentials, or prompt.
                   
        Returns:
            True if login successful
        """
        username = self._get_username()
        
        # Get token - check multiple sources
        if not token:
            # 1. Check stored credentials first
            stored_token = self.cred_manager.get_credential("ghcr", username)
            
            if stored_token:
                token = stored_token
                self.console.print("[green]Using stored GitHub token[/green]")
            else:
                # 2. Check for Codespaces/GitHub Actions token
                import os
                codespaces_token = os.environ.get('GITHUB_TOKEN')
                
                if codespaces_token:
                    self.console.print("[yellow]Note:[/yellow] Codespaces token has limited package permissions")
                    use_codespaces = input("Use Codespaces token anyway? (not recommended for pushing) [y/N]: ")
                    
                    if use_codespaces.lower() == 'y':
                        token = codespaces_token
                        self.console.print("[green]Using GitHub Codespaces/Actions token[/green]")
                    else:
                        # 3. Prompt for PAT
                        token = self.cred_manager.prompt_and_store(
                            "ghcr", 
                            username,
                            f"Enter GitHub Personal Access Token (needs 'write:packages' scope): "
                        )
                else:
                    # 4. Prompt for PAT
                    token = self.cred_manager.prompt_and_store(
                        "ghcr", 
                        username,
                        f"Enter GitHub Personal Access Token (needs 'write:packages' scope): "
                    )
        
        # Attempt login
        try:
            process = subprocess.run(
                ["docker", "login", self.REGISTRY, "-u", username, "--password-stdin"],
                input=token,
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                self.console.print(f"[green]✓[/green] Successfully logged in to {self.REGISTRY}")
                self._authenticated = True
                return True
            else:
                self.console.print(f"[red]✗[/red] Login failed: {process.stderr}")
                return False
                
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗[/red] Login error: {e}")
            return False
            
    def logout(self) -> bool:
        """Logout from GitHub Container Registry."""
        try:
            subprocess.run(["docker", "logout", self.REGISTRY], check=True)
            self.console.print(f"[green]✓[/green] Logged out from {self.REGISTRY}")
            self._authenticated = False
            return True
        except subprocess.CalledProcessError:
            return False
            
    def build(self, dockerfile: str, tag: str, context: str = ".", 
              build_args: Optional[Dict[str, str]] = None) -> bool:
        """Build a Docker image.
        
        Args:
            dockerfile: Path to Dockerfile
            tag: Image tag (e.g., "myimage:latest")
            context: Build context directory
            build_args: Build arguments
            
        Returns:
            True if build successful
        """
        username = self._get_username()
        full_tag = f"{self.REGISTRY}/{username}/{tag}"
        
        cmd = ["docker", "build", "-f", dockerfile, "-t", full_tag]
        
        if build_args:
            for key, value in build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])
                
        cmd.append(context)
        
        self.console.print(f"Building {full_tag}...")
        
        try:
            process = subprocess.run(cmd, check=True)
            self.console.print(f"[green]✓[/green] Successfully built {full_tag}")
            return True
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗[/red] Build failed: {e}")
            return False
            
    def push(self, tag: str) -> bool:
        """Push image to GitHub Container Registry.
        
        Args:
            tag: Image tag (without registry prefix)
            
        Returns:
            True if push successful
        """
        if not self._authenticated:
            self.console.print("[yellow]Not authenticated. Please login first.[/yellow]")
            if not self.login():
                return False
                
        username = self._get_username()
        full_tag = f"{self.REGISTRY}/{username}/{tag}"
        
        self.console.print(f"Pushing {full_tag}...")
        
        try:
            subprocess.run(["docker", "push", full_tag], check=True)
            self.console.print(f"[green]✓[/green] Successfully pushed {full_tag}")
            
            # Print visibility reminder
            self.console.print("\n[yellow]Note:[/yellow] New packages are private by default.")
            self.console.print(f"To make public, visit: https://github.com/{username}?tab=packages")
            
            return True
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗[/red] Push failed: {e}")
            return False
            
    def pull(self, image: str, tag: str = "latest") -> bool:
        """Pull image from GitHub Container Registry.
        
        Args:
            image: Image name (format: "username/imagename" or full URL)
            tag: Image tag
            
        Returns:
            True if pull successful
        """
        if image.startswith(self.REGISTRY):
            full_image = f"{image}:{tag}"
        elif "/" in image:
            full_image = f"{self.REGISTRY}/{image}:{tag}"
        else:
            username = self._get_username()
            full_image = f"{self.REGISTRY}/{username}/{image}:{tag}"
            
        self.console.print(f"Pulling {full_image}...")
        
        try:
            subprocess.run(["docker", "pull", full_image], check=True)
            self.console.print(f"[green]✓[/green] Successfully pulled {full_image}")
            return True
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗[/red] Pull failed: {e}")
            return False
            
    def list_images(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """List Docker images (local).
        
        Args:
            namespace: Filter by namespace (e.g., "ghcr.io/username")
            
        Returns:
            List of image dictionaries
        """
        if not namespace:
            username = self._get_username()
            namespace = f"{self.REGISTRY}/{username}"
            
        try:
            result = subprocess.run(
                ["docker", "images", "--format", "json", namespace],
                capture_output=True,
                text=True,
                check=True
            )
            
            images = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    images.append(json.loads(line))
                    
            return images
            
        except subprocess.CalledProcessError:
            return []
            
    def tag_for_ghcr(self, local_tag: str, remote_tag: Optional[str] = None) -> bool:
        """Tag a local image for GHCR.
        
        Args:
            local_tag: Local image tag
            remote_tag: Remote tag (if different from local)
            
        Returns:
            True if successful
        """
        username = self._get_username()
        
        if not remote_tag:
            remote_tag = local_tag
            
        full_remote_tag = f"{self.REGISTRY}/{username}/{remote_tag}"
        
        try:
            subprocess.run(
                ["docker", "tag", local_tag, full_remote_tag],
                check=True
            )
            self.console.print(f"[green]✓[/green] Tagged {local_tag} as {full_remote_tag}")
            return True
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗[/red] Tagging failed: {e}")
            return False
            
    def show_images(self) -> None:
        """Display local GHCR images in a nice table."""
        images = self.list_images()
        
        if not images:
            self.console.print("No GHCR images found locally.")
            return
            
        table = Table(title="Local GHCR Images")
        table.add_column("Repository", style="cyan")
        table.add_column("Tag", style="green")
        table.add_column("Image ID", style="yellow")
        table.add_column("Created", style="magenta")
        table.add_column("Size", style="blue")
        
        for img in images:
            table.add_row(
                img.get("Repository", ""),
                img.get("Tag", ""),
                img.get("ID", "")[:12],
                img.get("CreatedSince", ""),
                img.get("Size", "")
            )
            
        self.console.print(table)