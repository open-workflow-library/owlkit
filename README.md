# 🦉 OWLKit

OWLKit is a developer-first command-line toolkit that unifies Docker, CWL workflows, and Seven Bridges platform operations. It simplifies complex workflow toolchains with secure credential management and intuitive commands.

## Features

- **CWL Workflow Management**
  - Validate CWL workflows with comprehensive error reporting
  - Execute workflows with rich progress indicators
  - Browse and manage workflow outputs
  - Better UX than raw `cwltool` commands

- **GitHub Container Registry (GHCR) Integration**
  - Automatic authentication in GitHub Codespaces
  - Build, push, pull, and tag Docker images
  - Secure credential storage with keyring support
  - Organization-level package management
  
- **Seven Bridges Integration**
  - Pack CWL workflows with sbpack
  - Deploy to multiple Seven Bridges platforms:
    - Cancer Genomics Cloud (CGC)
    - Seven Bridges Platform (US & EU)
    - BioData Catalyst
    - Cavatica
  - Validate packed workflows
  - List and manage apps across platforms
  
- **Developer Experience**
  - Unified CLI interface for multiple tools
  - Rich console output with progress bars
  - Intuitive command structure
  - Cross-platform compatibility
  
- **Security**
  - Uses system keyring when available (macOS Keychain, Linux Secret Service)
  - Falls back to encrypted file storage
  - Automatic GitHub token detection in Codespaces
  - No credentials exposed in shell history

## Installation

```bash
# Install in development mode
pip install -e .

# Or install from PyPI (when published)
pip install owlkit
```

## Quick Start

### In GitHub Codespaces

OWLKit automatically detects Codespaces environment, but the built-in GITHUB_TOKEN 
has limited permissions. For pushing packages, you'll need a Personal Access Token:

```bash
# Login with a PAT (Personal Access Token)
owlkit docker login -t YOUR_GITHUB_PAT

# Or let it prompt you
owlkit docker login
# (It will detect Codespaces but ask for a PAT with write:packages scope)

# Build and push an image
owlkit docker build -t myapp:latest --push

# List your GHCR images
owlkit docker images
```

### Outside Codespaces

```bash
# Login with your GitHub Personal Access Token
owlkit docker login

# The tool will prompt for:
# - GitHub username (if not provided)
# - GitHub Personal Access Token (needs 'write:packages' scope)
```

## Command Reference

### CWL Workflow Commands

```bash
# Validate a CWL workflow
owlkit cwl validate workflow.cwl

# Run a workflow with inputs
owlkit cwl run workflow.cwl \
  --metadata-file input.json \
  --files-directory /path/to/data \
  --output-dir ./results

# List workflow outputs
owlkit cwl list ./results
```

### Seven Bridges/CGC Commands

```bash
# Login to CGC and store credentials securely
owlkit sbpack login

# Pack a CWL workflow for Seven Bridges
owlkit sbpack pack workflow.cwl --output packed-workflow.cwl --validate

# Deploy to Cancer Genomics Cloud (uses stored credentials)
owlkit sbpack deploy packed-workflow.cwl my-project/analysis-workflows my-app-name

# List apps in a CGC project
owlkit sbpack list-apps my-project/analysis-workflows

# Validate a packed workflow
owlkit sbpack validate packed-workflow.cwl

# Install sbpack (if not available)
owlkit sbpack install

# Or install manually:
# pip install sbpack

# Remove stored credentials
owlkit sbpack logout

# Configure multiple platforms
owlkit sbpack configure

# Use specific platform
owlkit sbpack deploy workflow.cwl project/name app-name --platform sbg-us
owlkit sbpack list-apps project-name --platform biodata-catalyst

# Non-interactive mode for CI/CD
export SB_CGC_TOKEN="your-token"
owlkit sbpack deploy workflow.cwl project app --platform cgc --non-interactive
```

#### Multi-Platform Support

OWLKit supports all Seven Bridges platforms. Configure once, deploy anywhere:

```bash
# Interactive configuration for all platforms
owlkit sbpack configure

# This will prompt you to set up tokens for:
# - cgc: Cancer Genomics Cloud
# - sbg-us: Seven Bridges Platform (US)
# - sbg-eu: Seven Bridges Platform (EU)
# - biodata-catalyst: NHLBI BioData Catalyst
# - cavatica: Cavatica (pediatric data)

# Deploy to specific platforms
owlkit sbpack deploy workflow.cwl username/project app-name --platform cgc
owlkit sbpack deploy workflow.cwl username/project app-name --platform sbg-eu
owlkit sbpack deploy workflow.cwl username/project app-name --platform biodata-catalyst

# List apps on different platforms
owlkit sbpack list-apps username/project --platform cgc
owlkit sbpack list-apps username/project --platform cavatica

# Platform-specific logout
owlkit sbpack logout --platform sbg-us
```

#### Real-World Success Example

**Deploying gdc-uploader to CGC:**
```bash
# Login and store CGC token
owlkit sbpack login

# Prepare workflow
owlkit sbpack pack /workspaces/gdc-uploader/cwl/gdc_upload.cwl --output gdc-uploader-packed.cwl --validate

# Deploy to CGC project
owlkit sbpack deploy gdc-uploader-packed.cwl szotcs/mp2prt-ec gdc-uploader-owlkit-test

# Result: Successfully deployed!
# App ID: szotcs/mp2prt-ec/gdc-uploader-owlkit-test
# Status: Available in CGC for workflow execution
```

**What happens behind the scenes:**
1. Sets up `~/.sevenbridges/credentials` file automatically
2. Validates CWL workflow structure  
3. Calls `sbpack cgc szotcs/mp2prt-ec/gdc-uploader-owlkit-test workflow.cwl`
4. Deploys using Docker image `ghcr.io/open-workflow-library/gdc-uploader:latest`

### Docker/GHCR Commands

```bash
# Login to GitHub Container Registry
owlkit docker login

# Build an image
owlkit docker build -f Dockerfile -t myapp:latest

# Build and push in one command
owlkit docker build -t myapp:latest --push

# Push an existing image
owlkit docker push myapp:latest

# Pull an image
owlkit docker pull username/myapp:latest

# Tag for GHCR
owlkit docker tag myapp:latest

# List local GHCR images
owlkit docker images

# Logout
owlkit docker logout
```

## CI/CD Integration

OWLKit supports non-interactive mode for automated deployments:

```bash
# Set credentials via environment variables
export SB_CGC_TOKEN="your-cgc-token"
export SB_SBG_US_TOKEN="your-sbg-token"

# Deploy without prompts (fails if no token)
owlkit sbpack deploy workflow.cwl project/name app-name \
  --platform cgc \
  --non-interactive

# Use in GitHub Actions
- name: Deploy to CGC
  env:
    SB_CGC_TOKEN: ${{ secrets.CGC_TOKEN }}
  run: |
    owlkit sbpack deploy workflow.cwl \
      my-project/workflows \
      my-app-${{ github.sha }} \
      --platform cgc \
      --non-interactive
```

See [Non-Interactive Mode Guide](docs/NON-INTERACTIVE-MODE.md) for detailed CI/CD examples.

## Why Choose OWLKit?

### Before OWLKit (Traditional Workflow)
```bash
# Multiple tools, complex authentication, verbose commands
docker login ghcr.io -u $USER -p $TOKEN
docker build -t ghcr.io/org/tool:latest .
docker push ghcr.io/org/tool:latest
cwltool --outdir ./results workflow.cwl inputs.json
sbpack workflow.cwl  # Separate sbpack installation and usage
sb apps create --project my-project --name my-app --cwl packed.cwl
# Handle errors manually, no progress indicators
```

### With OWLKit (Unified Experience)
```bash
# Single tool, auto-authentication, intuitive commands
owlkit docker login ghcr.io  # Auto-detects credentials
owlkit docker build -t ghcr.io/org/tool:latest . --push
owlkit cwl run workflow.cwl --input inputs.json --output-dir ./results
owlkit sbpack pack workflow.cwl --validate
owlkit sbpack deploy packed.cwl my-project my-app
# Rich progress indicators, better error messages, unified interface
```

## Environment Detection

Test what OWLKit can auto-detect:

```bash
owlkit test
```

## Creating a GitHub Personal Access Token

If not using Codespaces, you'll need a GitHub Personal Access Token:

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token (classic)"
3. Give it a name (e.g., "owlkit-docker")
4. Select scopes:
   - `write:packages` - Upload packages to GitHub Package Registry
   - `read:packages` - Download packages from GitHub Package Registry
   - `delete:packages` - Delete packages from GitHub Package Registry (optional)
5. Generate and save the token

## Security

- In Codespaces: Uses built-in `GITHUB_TOKEN`
- On macOS: Stores credentials in Keychain
- On Linux: Uses Secret Service (if available)
- Fallback: Encrypted file in `~/.owlkit/`

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black owlkit tests

# Type check
mypy owlkit
```

## License

MIT License - see LICENSE file for details.