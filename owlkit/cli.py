"""Command-line interface for OWLKit."""

import click
import subprocess
from rich.console import Console
from .docker.ghcr import GHCRManager
from .cwl.runner import CWLRunner
from .sbpack.manager import SBPackManager
from . import __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="owlkit")
def main():
    """OWLKit - Open Workflow Library Toolkit
    
    Manage CWL workflows, Docker images, and Seven Bridges integration.
    """
    pass


@main.group()
def docker():
    """Docker/GHCR management commands."""
    pass


@docker.command()
@click.option('--username', '-u', help='GitHub username or organization (auto-detected in Codespaces)')
@click.option('--token', '-t', help='GitHub token')
@click.option('--force-pat', is_flag=True, help='Force PAT input even in Codespaces')
def login(username, token, force_pat):
    """Login to GitHub Container Registry."""
    ghcr = GHCRManager(username)
    
    if force_pat and not token:
        # Force PAT input
        from getpass import getpass
        token = getpass("Enter GitHub Personal Access Token: ")
    
    if ghcr.login(token):
        console.print("\n[bold green]Successfully authenticated to ghcr.io![/bold green]")
        console.print("\nYou can now:")
        console.print("  • Build and push Docker images")
        console.print("  • Pull private images")
        console.print("  • Manage container packages")
    else:
        console.print("[bold red]Authentication failed[/bold red]")
        raise click.Abort()


@docker.command()
def logout():
    """Logout from GitHub Container Registry."""
    ghcr = GHCRManager()
    if ghcr.logout():
        console.print("[bold green]Successfully logged out[/bold green]")
    else:
        console.print("[bold red]Logout failed[/bold red]")


@docker.command()
@click.option('--dockerfile', '-f', default='Dockerfile', help='Path to Dockerfile')
@click.option('--tag', '-t', required=True, help='Image tag (e.g., myapp:latest)')
@click.option('--context', '-c', default='.', help='Build context directory')
@click.option('--username', '-u', help='GitHub username or organization')
@click.option('--push', is_flag=True, help='Push after building')
def build(dockerfile, tag, context, username, push):
    """Build a Docker image for GHCR."""
    ghcr = GHCRManager(username)
    
    console.print(f"\n[bold]Building Docker image[/bold]")
    console.print(f"  Dockerfile: {dockerfile}")
    console.print(f"  Tag: {tag}")
    console.print(f"  Context: {context}")
    
    if ghcr.build(dockerfile, tag, context):
        console.print("\n[bold green]Build successful![/bold green]")
        
        if push:
            console.print("\n[bold]Pushing to GHCR...[/bold]")
            if ghcr.push(tag):
                console.print("[bold green]Push successful![/bold green]")
            else:
                console.print("[bold red]Push failed[/bold red]")
    else:
        console.print("[bold red]Build failed[/bold red]")
        raise click.Abort()


@docker.command()
@click.argument('tag')
@click.option('--username', '-u', help='GitHub username or organization')
def push(tag, username):
    """Push a Docker image to GHCR."""
    ghcr = GHCRManager(username)
    
    if ghcr.push(tag):
        console.print("[bold green]Push successful![/bold green]")
    else:
        console.print("[bold red]Push failed[/bold red]")
        raise click.Abort()


@docker.command()
@click.argument('image')
@click.option('--tag', '-t', default='latest', help='Image tag')
def pull(image, tag):
    """Pull a Docker image from GHCR."""
    ghcr = GHCRManager()
    
    if ghcr.pull(image, tag):
        console.print("[bold green]Pull successful![/bold green]")
    else:
        console.print("[bold red]Pull failed[/bold red]")
        raise click.Abort()


@docker.command()
def images():
    """List local GHCR images."""
    ghcr = GHCRManager()
    ghcr.show_images()


@docker.command()
@click.argument('local_tag')
@click.option('--remote-tag', '-r', help='Remote tag (defaults to local tag)')
def tag(local_tag, remote_tag):
    """Tag a local image for GHCR."""
    ghcr = GHCRManager()
    
    if ghcr.tag_for_ghcr(local_tag, remote_tag):
        console.print("[bold green]Tagging successful![/bold green]")
    else:
        console.print("[bold red]Tagging failed[/bold red]")
        raise click.Abort()


@main.group()
def cwl():
    """CWL workflow commands."""
    pass


@cwl.command()
@click.argument('workflow_path')
@click.option('--metadata-file', '-m', help='Metadata file path')
@click.option('--files-directory', '-f', help='Files directory path')
@click.option('--token-file', '-t', help='Token file path')
@click.option('--thread-count', '-j', default=4, help='Number of threads')
@click.option('--retry-count', '-r', default=3, help='Number of retries')
@click.option('--output-dir', '-o', default='./output', help='Output directory')
@click.option('--enable-pull/--no-pull', default=True, help='Enable Docker pull')
@click.option('--strict-limits', is_flag=True, help='Enforce strict resource limits')
def run(workflow_path, metadata_file, files_directory, token_file, 
        thread_count, retry_count, output_dir, enable_pull, strict_limits):
    """Run a CWL workflow."""
    runner = CWLRunner(enable_pull=enable_pull, strict_limits=strict_limits)
    
    # Build job parameters
    job_params = {}
    if metadata_file:
        job_params['metadata_file'] = metadata_file
    if files_directory:
        job_params['files_directory'] = files_directory
    if token_file:
        job_params['token_file'] = token_file
    if thread_count:
        job_params['thread_count'] = thread_count
    if retry_count:
        job_params['retry_count'] = retry_count
    
    try:
        result = runner.run_workflow(workflow_path, job_params, output_dir)
        console.print("\n[bold green]Workflow completed successfully![/bold green]")
        
        # Show output files
        outputs = runner.list_outputs(output_dir)
        if outputs:
            console.print(f"\n[bold]Output files in {output_dir}:[/bold]")
            for output in outputs:
                console.print(f"  • {output}")
    except subprocess.CalledProcessError:
        console.print("[bold red]Workflow failed[/bold red]")
        raise click.Abort()


@cwl.command()
@click.argument('workflow_path')
@click.argument('job_file')
@click.option('--output-dir', '-o', default='./output', help='Output directory')
@click.option('--enable-pull/--no-pull', default=True, help='Enable Docker pull')
@click.option('--strict-limits', is_flag=True, help='Enforce strict resource limits')
def run_job(workflow_path, job_file, output_dir, enable_pull, strict_limits):
    """Run a CWL workflow with a job file."""
    runner = CWLRunner(enable_pull=enable_pull, strict_limits=strict_limits)
    
    try:
        result = runner.run_workflow_file(workflow_path, job_file, output_dir)
        console.print("\n[bold green]Workflow completed successfully![/bold green]")
        
        outputs = runner.list_outputs(output_dir)
        if outputs:
            console.print(f"\n[bold]Output files in {output_dir}:[/bold]")
            for output in outputs:
                console.print(f"  • {output}")
    except subprocess.CalledProcessError:
        console.print("[bold red]Workflow failed[/bold red]")
        raise click.Abort()


@cwl.command()
@click.argument('workflow_path')
def validate(workflow_path):
    """Validate a CWL workflow."""
    runner = CWLRunner()
    
    if runner.validate_workflow(workflow_path):
        console.print("[bold green]Workflow is valid![/bold green]")
    else:
        console.print("[bold red]Workflow validation failed[/bold red]")
        raise click.Abort()


@main.group()
def sbpack():
    """Seven Bridges packing commands."""
    pass


@sbpack.command()
@click.option('--token', '-t', help='Authentication token')
@click.option('--force-new', is_flag=True, help='Force new token input even if one is stored')
@click.option('--platform', '-p', default='cgc', help='Seven Bridges platform (cgc, sbg-us, sbg-eu, biodata-catalyst, cavatica)')
@click.option('--non-interactive', is_flag=True, help='Run in non-interactive mode (no prompts)')
def login(token, force_new, platform, non_interactive):
    """Login to a Seven Bridges platform and store credentials."""
    manager = SBPackManager()
    
    if not manager.login_to_platform(platform, token, force_new, non_interactive):
        raise click.Abort()


@sbpack.command()
@click.argument('cwl_file')
@click.option('--output', '-o', help='Output filename')
@click.option('--validate', is_flag=True, help='Validate the packed workflow')
def pack(cwl_file, output, validate):
    """Pack a CWL workflow for Seven Bridges."""
    manager = SBPackManager()
    
    if not manager.check_sbpack_available():
        console.print("[bold yellow]sbpack not found. Attempting to install...[/bold yellow]")
        if not manager.install_sbpack():
            console.print("[bold red]Failed to install sbpack. Please install manually:[/bold red]")
            console.print("  pip install sbpack")
            raise click.Abort()
    
    try:
        packed_file = manager.pack_workflow(cwl_file, output)
        
        if validate:
            console.print("\n[bold blue]Validating packed workflow...[/bold blue]")
            if not manager.validate_packed_workflow(packed_file):
                raise click.Abort()
                
    except Exception as e:
        console.print(f"[bold red]Packing failed: {e}[/bold red]")
        raise click.Abort()


@sbpack.command()
@click.argument('packed_file')
@click.argument('project_id')
@click.argument('app_name')
@click.option('--token', '-t', help='Authentication token')
@click.option('--platform', '-p', default='cgc', help='Seven Bridges platform (cgc, sbg-us, sbg-eu, biodata-catalyst, cavatica)')
@click.option('--non-interactive', is_flag=True, help='Run in non-interactive mode (no prompts)')
def deploy(packed_file, project_id, app_name, token, platform, non_interactive):
    """Deploy a packed workflow to a Seven Bridges platform."""
    manager = SBPackManager()
    
    if not manager.deploy_to_cgc(packed_file, project_id, app_name, token, platform, non_interactive):
        raise click.Abort()


@sbpack.command()
@click.argument('project_id')
@click.option('--token', '-t', help='Authentication token')
@click.option('--platform', '-p', default='cgc', help='Seven Bridges platform (cgc, sbg-us, sbg-eu, biodata-catalyst, cavatica)')
@click.option('--non-interactive', is_flag=True, help='Run in non-interactive mode (no prompts)')
def list_apps(project_id, token, platform, non_interactive):
    """List apps in a Seven Bridges project."""
    manager = SBPackManager()
    apps = manager.list_apps(project_id, token, platform, non_interactive)
    
    if not apps:
        if not non_interactive:
            console.print("No apps found or failed to retrieve apps.")
        return
    
    console.print(f"\n[bold]Apps in project {project_id} on {platform}:[/bold]\n")
    for app in apps:
        name = app.get('name', 'Unknown')
        app_id = app.get('id', 'Unknown')
        revision = app.get('revision', 'Unknown')
        console.print(f"  • {name} (ID: {app_id}, Rev: {revision})")


@sbpack.command()
@click.argument('packed_file')
def validate(packed_file):
    """Validate a packed CWL workflow."""
    manager = SBPackManager()
    
    if not manager.validate_packed_workflow(packed_file):
        raise click.Abort()


@sbpack.command()
def install():
    """Install sbpack using npm."""
    manager = SBPackManager()
    
    if manager.check_sbpack_available():
        console.print("[bold green]sbpack is already installed![/bold green]")
        return
    
    if not manager.install_sbpack():
        raise click.Abort()


@sbpack.command()
def configure():
    """Configure authentication tokens for Seven Bridges platforms."""
    manager = SBPackManager()
    manager.configure_platforms()


@sbpack.command()
@click.option('--platform', '-p', default='cgc', help='Seven Bridges platform to logout from')
def logout(platform):
    """Remove stored credentials for a Seven Bridges platform."""
    manager = SBPackManager()
    manager.cred_manager.delete_credential(platform, 'auth_token')
    console.print(f"[bold green]{platform} credentials removed[/bold green]")


@main.command()
def test():
    """Test Codespaces environment detection."""
    import os
    
    console.print("\n[bold]Codespaces Environment Check[/bold]\n")
    
    env_vars = [
        'GITHUB_TOKEN',
        'GITHUB_USER', 
        'GITHUB_ACTOR',
        'GITHUB_REPOSITORY_OWNER',
        'CODESPACES',
        'GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN'
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            if var == 'GITHUB_TOKEN':
                # Don't show the full token
                console.print(f"✓ {var}: {'*' * 10}{value[-4:]}")
            else:
                console.print(f"✓ {var}: {value}")
        else:
            console.print(f"✗ {var}: [dim]Not set[/dim]")
    
    # Test auto-detection
    console.print("\n[bold]Auto-detection Test[/bold]")
    ghcr = GHCRManager()
    username = ghcr._get_username()
    console.print(f"Detected username: {username}")


if __name__ == "__main__":
    main()