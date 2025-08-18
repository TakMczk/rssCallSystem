# OpenAI API 401 Organization Access Error - Diagnosis and Solutions

## Problem
OpenAI API key is returning error: "You do not have access to the organization tied to the API key" (Error code: 401, invalid_organization)

## Current API Key Type
- **Key format**: `sk-proj-UUTFG9DX8SDN...` (Project-based API key)
- **Status**: Valid key format but organization access denied

## Root Causes and Solutions

### 1. Project API Key Configuration Issue
**Problem**: Project API keys (`sk-proj-*`) require specific organization/project configuration
**Solutions**:
- Check if the API key belongs to the correct organization
- Verify project permissions in OpenAI Platform dashboard
- Ensure the project has sufficient credits/billing setup

### 2. Missing Organization Header (Most Common Fix)
**Problem**: Project API keys sometimes require explicit organization ID in requests
**Solution**: Add organization ID to API requests

### 3. Account/Billing Status
**Problem**: Account may have billing issues or be suspended
**Solutions**:
- Check OpenAI account billing status
- Ensure payment method is active
- Verify account is not suspended

### 4. Key Permissions
**Problem**: API key may not have required permissions
**Solutions**:
- Regenerate API key from OpenAI dashboard
- Check key permissions in project settings
- Ensure key has Chat Completions access

## Immediate Action Items

### Option 1: Try Organization Header (Quick Fix)
Add organization ID to API requests. We need to:
1. Find the organization ID from OpenAI dashboard
2. Add `OpenAI-Organization` header to requests

### Option 2: Use User/Service Account Key
Instead of project key, create a user-level API key:
1. Go to OpenAI Platform → API Keys
2. Create new "User" type key (starts with `sk-`)
3. Replace current project key

### Option 3: Verify Project Setup
1. Login to OpenAI Platform
2. Check project billing and permissions
3. Verify API key is active and valid

## Next Steps
1. Check OpenAI dashboard for organization ID
2. Try adding organization header to requests
3. If that fails, create new user-level API key
4. Test API connectivity with new configuration

## Technical Implementation
Once we identify the solution, we'll need to update:
- `src/scorer.py`: Add organization header if needed
- `.env`: Update API key if using new key
- Test the API connection again
