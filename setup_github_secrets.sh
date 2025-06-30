#!/bin/bash

# GitHub Environment Setup Script
# This helps you create the required GitHub environments for deployment

echo "🔧 GitHub Repository Setup Guide"
echo "=================================="
echo ""

echo "📋 Step 1: Add Repository Secrets"
echo "1. Go to: https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions"
echo "2. Click 'New repository secret'"
echo "3. Add each of these secrets:"
echo ""
echo "   POSTGRES_PASSWORD_STAGING = staging_postgres_secure_password_2024"
echo "   FERNET_KEY_STAGING = lB-MQaHU5X8p7BmyIe5FUtKOAkyn29MwWRs8kjBAZfk="
echo "   WEBSERVER_SECRET_KEY_STAGING = SAVivIh4sMRqexCls6dpfrs2gnVf_UA9AgTBhH52Tgs"
echo "   AIRFLOW_PASSWORD_STAGING = staging_airflow_admin_2024"
echo ""

echo "🌍 Step 2: Create GitHub Environments (Optional but Recommended)"
echo "1. Go to: https://github.com/YOUR_USERNAME/YOUR_REPO/settings/environments"
echo "2. Click 'New environment'"
echo "3. Create 'staging' environment"
echo "4. Create 'production' environment"
echo "5. Add protection rules (require reviews, restrict branches, etc.)"
echo ""

echo "🔀 Step 3: Create develop branch (if not exists)"
echo "Run these commands:"
echo "   git checkout -b develop"
echo "   git push origin develop"
echo ""

echo "✅ Step 4: Test the pipeline"
echo "1. Make a small change to any file"
echo "2. Commit and push to develop:"
echo "   git add ."
echo "   git commit -m 'Test staging deployment'"
echo "   git push origin develop"
echo "3. Check GitHub Actions tab for deployment progress"
echo ""

echo "📊 Step 5: Monitor deployment"
echo "If successful, staging will be available at:"
echo "   - Airflow UI: http://localhost:8081"
echo "   - Database: localhost:5433"
echo "   - Username: airflow"
echo "   - Password: staging_airflow_admin_2024"
echo ""

echo "🐛 Troubleshooting:"
echo "- Check GitHub Actions logs if deployment fails"
echo "- Verify all secrets are set correctly"
echo "- Ensure no port conflicts on the runner"
echo ""

echo "Ready to proceed? (y/n)"
