# SBPack Deployment Guide

## Overview

This document describes the successful deployment process using `sbpack` to deploy CWL workflows to the Cancer Genomics Cloud (CGC) and other Seven Bridges platforms.

## Key Requirements

### 1. Seven Bridges Credentials File

`sbpack` requires a credentials file at `~/.sevenbridges/credentials` with the following format:

```ini
[profile_name]
api_endpoint = https://api.endpoint.com/v2
auth_token = your_token_here
```

### 2. Example for CGC

```ini
[cgc]
api_endpoint = https://cgc-api.sbgenomics.com/v2
auth_token = your_cgc_dev_token
```

## Successful Deployment Process

### Step 1: Login and Store Credentials
```bash
owlkit sbpack login
```
This prompts for your CGC token and stores it securely in owlkit's credential manager.

### Step 2: Prepare Workflow
```bash
owlkit sbpack pack /path/to/workflow.cwl --output packed-workflow.cwl --validate
```
This copies and validates the CWL workflow (no actual packing needed for direct deployment).

### Step 3: Deploy to CGC
```bash
owlkit sbpack deploy packed-workflow.cwl project-id/project-name app-name
```
This:
1. Sets up the `~/.sevenbridges/credentials` file automatically
2. Calls `sbpack cgc project-id/project-name/app-name /path/to/workflow.cwl`
3. Deploys the workflow to the specified CGC project

## Real Example - GDC Uploader Deployment

**Successful deployment to `szotcs/mp2prt-ec` project:**

```bash
# Login to CGC
owlkit sbpack login

# Prepare workflow
owlkit sbpack pack /workspaces/gdc-uploader/cwl/gdc_upload.cwl --output gdc-uploader-packed.cwl --validate

# Deploy to CGC project
owlkit sbpack deploy gdc-uploader-packed.cwl szotcs/mp2prt-ec gdc-uploader-owlkit-test

# Verify deployment
owlkit sbpack list-apps szotcs/mp2prt-ec
```

**Result:**
- **App ID**: `szotcs/mp2prt-ec/gdc-uploader-owlkit-test`
- **Status**: Successfully deployed and available in CGC
- **Docker Image**: `ghcr.io/open-workflow-library/gdc-uploader:latest`

## Implementation Details

### Credentials File Setup

The `SBPackManager._setup_sbpack_credentials()` method:

1. Creates `~/.sevenbridges/` directory with secure permissions (700)
2. Uses `configparser` to manage the credentials file
3. Adds/updates the CGC profile with correct endpoint and token
4. Sets file permissions to 600 for security

### SBPack Command Format

```bash
sbpack profile appid cwl_path
```

Where:
- `profile`: Profile name from credentials file (e.g., "cgc")
- `appid`: Full app identifier `{project}/{app_name}`
- `cwl_path`: Path to the CWL workflow file

### Error Handling

The implementation provides detailed error reporting:
- Validates workflow files before deployment
- Checks sbpack availability
- Reports both stdout and stderr from sbpack
- Handles missing credentials gracefully

## Troubleshooting

### Common Issues

1. **"Bad Request" errors**: Usually indicate API endpoint or authentication issues
2. **"sbpack not found"**: Install with `pip install sbpack`
3. **Permission errors**: Check credentials file permissions (should be 600)
4. **App already exists**: Use a different app name or update existing app

### Debugging

```bash
# Check sbpack directly
sbpack --help

# Verify credentials file
cat ~/.sevenbridges/credentials

# Test with environment variables
export SB_API_ENDPOINT=https://cgc-api.sbgenomics.com/v2
export SB_AUTH_TOKEN=your_token
sbpack . project/app-name workflow.cwl
```

## Best Practices

1. **Use descriptive app names** to avoid conflicts
2. **Validate workflows** before deployment with `--validate` flag
3. **Store credentials securely** using owlkit's credential manager
4. **Test in development projects** before production deployment
5. **Use version numbers** in app names for tracking (e.g., `app-name-v1.2`)

## Multi-Platform Support

OWLKit now provides full support for all Seven Bridges platforms with automatic credential management:

### Available Platforms

- **cgc**: Cancer Genomics Cloud - `https://cgc-api.sbgenomics.com/v2`
- **sbg-us**: Seven Bridges Platform (US) - `https://api.sbgenomics.com/v2`
- **sbg-eu**: Seven Bridges Platform (EU) - `https://eu-api.sbgenomics.com/v2`
- **biodata-catalyst**: BioData Catalyst - `https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2`
- **cavatica**: Cavatica - `https://cavatica-api.sbgenomics.com/v2`

### Configuration

Use the interactive configuration command to set up all platforms:

```bash
# Configure all platforms interactively
owlkit sbpack configure
```

This will:
1. Show a table of available platforms
2. Prompt for tokens for each platform
3. Test each token before storing
4. Create appropriate entries in `~/.sevenbridges/credentials`

### Using Different Platforms

```bash
# Deploy to different platforms
owlkit sbpack deploy workflow.cwl project/name app-name --platform cgc
owlkit sbpack deploy workflow.cwl project/name app-name --platform sbg-eu
owlkit sbpack deploy workflow.cwl project/name app-name --platform biodata-catalyst

# List apps on different platforms
owlkit sbpack list-apps project-name --platform cgc
owlkit sbpack list-apps project-name --platform cavatica

# Platform-specific logout
owlkit sbpack logout --platform sbg-us
```

### Credentials File Format

After configuration, your `~/.sevenbridges/credentials` file will contain:

```ini
[cgc]
api_endpoint = https://cgc-api.sbgenomics.com/v2
auth_token = your_cgc_token

[sbg-us]
api_endpoint = https://api.sbgenomics.com/v2
auth_token = your_sbg_us_token

[sbg-eu]
api_endpoint = https://eu-api.sbgenomics.com/v2
auth_token = your_sbg_eu_token

[biodata-catalyst]
api_endpoint = https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2
auth_token = your_biodata_token

[cavatica]
api_endpoint = https://cavatica-api.sbgenomics.com/v2
auth_token = your_cavatica_token
```

## Integration with OWL Pattern

This deployment process follows the OWL (Open Workflow Library) pattern:
1. Workflows stored in `/cwl` directory with flat structure
2. Docker images in GitHub Container Registry (`ghcr.io`)
3. Metadata and documentation co-located
4. Reproducible deployment with version tracking

## Future Enhancements

Potential improvements:
1. **Batch deployment** of multiple workflows
2. **Version management** with automatic revision handling
3. **Project templates** for common deployment patterns
4. **Integration testing** with actual CGC deployments
5. **Rollback functionality** for failed deployments