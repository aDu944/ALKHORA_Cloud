# Deployment Guide - Branch-Based Updates

## Using Different Branches for Faster Updates

Instead of using the `main` branch for all updates, you can use a separate branch for faster processing and testing.

## Recommended Branch Strategy

### 1. Create a Development/Quick Update Branch

```bash
# Create and switch to a new branch
git checkout -b develop

# Or create a branch specifically for quick updates
git checkout -b quick-updates

# Push the branch to GitHub
git push -u origin develop
```

### 2. Configure Frappe Cloud to Use the Branch

#### Method A: Via Frappe Cloud Dashboard

1. Log in to [Frappe Cloud](https://frappecloud.com)
2. Go to your site/app settings
3. Navigate to **Apps** → **nextcloud_integration**
4. Find **Repository Settings** or **Source Configuration**
5. Change **Branch** from `main` to `develop` (or your branch name)
6. Save the changes
7. Frappe Cloud will automatically deploy from the new branch

#### Method B: Via Frappe Cloud CLI (if available)

```bash
# Update app branch configuration
frappe cloud app update-branch --app nextcloud_integration --branch develop
```

### 3. Workflow for Faster Updates

#### Quick Update Workflow:

```bash
# 1. Make your changes
# ... edit files ...

# 2. Commit to the quick branch
git add .
git commit -m "Quick update: Add new feature"
git push origin develop

# 3. Frappe Cloud will automatically detect and deploy
# (or trigger manual deployment if needed)
```

#### Production Deployment Workflow:

```bash
# 1. When ready for production, merge to main
git checkout main
git merge develop
git push origin main

# 2. Update Frappe Cloud to use main branch
# (via dashboard or keep develop for continuous updates)
```

## Benefits of Using a Separate Branch

1. **Faster Processing**: Development branches often have faster CI/CD pipelines
2. **Testing**: Test changes before merging to main
3. **Rollback**: Easy to switch back to main if issues occur
4. **Parallel Development**: Multiple developers can work on different branches

## Branch Naming Conventions

- `main` / `master`: Production-ready code
- `develop`: Development/testing branch
- `staging`: Pre-production testing
- `quick-updates`: Fast iteration branch
- `feature/*`: Feature-specific branches

## Switching Branches in Frappe Cloud

### To Switch Back to Main:

1. Go to Frappe Cloud Dashboard
2. Navigate to App Settings
3. Change branch back to `main`
4. Save and redeploy

### To Use Multiple Branches:

You can have different sites using different branches:
- **Production Site**: Uses `main` branch
- **Staging Site**: Uses `develop` branch
- **Test Site**: Uses `feature/*` branches

## Best Practices

1. **Keep main stable**: Only merge tested code to main
2. **Use develop for daily updates**: Faster iteration and testing
3. **Tag releases**: Tag main branch when deploying to production
4. **Document changes**: Keep changelog updated

## Current Setup

Your repository: `https://github.com/aDu944/ALKHORA_Cloud`

### Recommended Branch Structure:

```
main (production)
  └── develop (development/quick updates)
      └── feature/* (feature branches)
```

## Quick Commands

```bash
# Create and push develop branch
git checkout -b develop
git push -u origin develop

# Switch to develop for quick updates
git checkout develop

# Make changes and push
git add .
git commit -m "Quick update"
git push origin develop

# When ready, merge to main
git checkout main
git merge develop
git push origin main
```

## Troubleshooting

### Branch Not Updating in Frappe Cloud

1. Verify branch exists on GitHub
2. Check branch name spelling in Frappe Cloud settings
3. Trigger manual deployment if auto-deploy is disabled
4. Check Frappe Cloud logs for deployment errors

### Deployment Fails

1. Check if branch has all required files
2. Verify `hooks.py` and `setup.py` exist
3. Check for syntax errors in the branch
4. Review Frappe Cloud error logs

## Notes

- Frappe Cloud typically auto-deploys on push to the configured branch
- Some plans may require manual deployment triggers
- Branch changes take effect on the next deployment
- Always test in a development branch before merging to main
