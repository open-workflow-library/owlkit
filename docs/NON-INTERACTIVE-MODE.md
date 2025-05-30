# Non-Interactive Mode Guide

## Overview

OWLKit's sbpack commands support non-interactive mode for CI/CD pipelines and automated deployments. This mode ensures commands never prompt for user input and fail gracefully when credentials are missing.

## Usage

### Interactive Mode (Default)

In interactive mode, commands will prompt for missing credentials:

```bash
# Will prompt for token if not stored
owlkit sbpack login --platform cgc

# Will prompt if no token found
owlkit sbpack deploy workflow.cwl project/name app-name --platform cgc
```

### Non-Interactive Mode

Add the `--non-interactive` flag to prevent prompts:

```bash
# Will fail if no token is available
owlkit sbpack login --platform cgc --non-interactive

# Will fail if no token found
owlkit sbpack deploy workflow.cwl project/name app-name --platform cgc --non-interactive
```

## Credential Sources

In non-interactive mode, credentials are checked in this order:

1. **Command line**: `--token` parameter
2. **Stored credentials**: Previously saved via `owlkit sbpack login`
3. **Environment variables**: Platform-specific variables

### Environment Variables

Each platform has its own environment variable:

- **CGC**: `SB_CGC_TOKEN`
- **SBG US**: `SB_SBG_US_TOKEN`
- **SBG EU**: `SB_SBG_EU_TOKEN`
- **BioData Catalyst**: `SB_BIODATA_CATALYST_TOKEN`
- **Cavatica**: `SB_CAVATICA_TOKEN`

## Examples

### CI/CD Pipeline

```bash
#!/bin/bash
# deploy.sh - Automated deployment script

# Set token via environment variable
export SB_CGC_TOKEN="${CGC_TOKEN}"

# Deploy workflow (will fail if token is invalid)
owlkit sbpack deploy \
  workflow.cwl \
  my-project/workflows \
  my-app-v1.0 \
  --platform cgc \
  --non-interactive

# Check deployment
owlkit sbpack list-apps my-project/workflows \
  --platform cgc \
  --non-interactive
```

### GitHub Actions

```yaml
name: Deploy to CGC

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install OWLKit
        run: pip install owlkit
      
      - name: Deploy to CGC
        env:
          SB_CGC_TOKEN: ${{ secrets.CGC_TOKEN }}
        run: |
          owlkit sbpack deploy \
            cwl/workflow.cwl \
            ${{ vars.CGC_PROJECT }} \
            my-app-${{ github.ref_name }} \
            --platform cgc \
            --non-interactive
```

### GitLab CI

```yaml
deploy:
  stage: deploy
  script:
    - pip install owlkit
    - |
      owlkit sbpack deploy \
        workflow.cwl \
        ${CI_PROJECT_NAME}/workflows \
        app-${CI_COMMIT_TAG} \
        --platform cgc \
        --non-interactive
  variables:
    SB_CGC_TOKEN: ${CGC_TOKEN}
  only:
    - tags
```

### Docker Container

```dockerfile
FROM python:3.11-slim

# Install owlkit
RUN pip install owlkit

# Copy workflow
COPY workflow.cwl /app/

# Deploy script
COPY deploy.sh /app/
RUN chmod +x /app/deploy.sh

# Run with: docker run -e SB_CGC_TOKEN=xxx myimage
CMD ["/app/deploy.sh"]
```

```bash
# deploy.sh
#!/bin/bash
owlkit sbpack deploy \
  /app/workflow.cwl \
  project/workflows \
  my-app \
  --platform cgc \
  --non-interactive
```

## Multi-Platform Deployment

Deploy to multiple platforms in non-interactive mode:

```bash
#!/bin/bash
# deploy-all.sh

# Deploy to all configured platforms
for platform in cgc sbg-us biodata-catalyst; do
  echo "Deploying to $platform..."
  
  # Set the appropriate token variable
  token_var="SB_${platform^^}_TOKEN"
  token_var="${token_var//-/_}"
  
  if [ -n "${!token_var}" ]; then
    owlkit sbpack deploy \
      workflow.cwl \
      project/workflows \
      my-app \
      --platform "$platform" \
      --non-interactive
  else
    echo "Skipping $platform - no token found"
  fi
done
```

## Error Handling

In non-interactive mode, commands will:

1. Exit with non-zero status on failure
2. Print minimal output (errors only)
3. Never prompt for input
4. Fail fast when credentials are missing

Example error checking:

```bash
#!/bin/bash
set -e  # Exit on error

# This will exit if deployment fails
owlkit sbpack deploy workflow.cwl project app --platform cgc --non-interactive

# Check specific exit codes
if owlkit sbpack list-apps project --platform cgc --non-interactive; then
  echo "Successfully listed apps"
else
  echo "Failed to list apps (exit code: $?)"
  exit 1
fi
```

## Best Practices

1. **Always test interactively first** to ensure credentials work
2. **Use environment variables** for CI/CD pipelines
3. **Check exit codes** in scripts
4. **Log output** for debugging
5. **Use specific platform names** to avoid ambiguity
6. **Store tokens securely** in CI/CD secret stores

## Troubleshooting

### No Token Found

```bash
# Error: No cgc token found and running in non-interactive mode.
# Set token via environment variable SB_CGC_TOKEN
```

**Solution**: Set the appropriate environment variable or use `--token` parameter.

### Invalid Token

```bash
# Error: Unauthorized
```

**Solution**: Verify token is valid and has appropriate permissions.

### Platform Not Found

```bash
# Error: Unknown platform: xyz
# Available platforms: cgc, sbg-us, sbg-eu, biodata-catalyst, cavatica
```

**Solution**: Use one of the supported platform identifiers.