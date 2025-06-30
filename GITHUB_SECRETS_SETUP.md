# GitHub Secrets Setup Guide

## Required Secrets for Staging Environment

You need to add these secrets to your GitHub repository:

### 1. Navigate to Repository Settings
- Go to your GitHub repository
- Click on "Settings" tab
- Click on "Secrets and variables" → "Actions"

### 2. Add the following Repository Secrets:

#### POSTGRES_PASSWORD_STAGING
```
Value: staging_postgres_secure_password_2024
Description: PostgreSQL password for staging database
```

#### FERNET_KEY_STAGING
```
Value: Generate using Python:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Example: gAAAAABhZ9Q7... (32-byte base64 encoded key)
Description: Airflow Fernet key for encrypting connections/variables
```

#### WEBSERVER_SECRET_KEY_STAGING
```
Value: Generate using Python:
python -c "import secrets; print(secrets.token_urlsafe(32))"

Example: AbCdEf123... (random 32-character string)
Description: Flask secret key for Airflow webserver
```

#### AIRFLOW_PASSWORD_STAGING
```
Value: staging_airflow_admin_2024
Description: Password for Airflow admin user in staging
```

## Quick Setup Commands

Run these commands to generate the required keys:

```bash
# Generate Fernet Key
echo "FERNET_KEY_STAGING:"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate Webserver Secret Key  
echo "WEBSERVER_SECRET_KEY_STAGING:"
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Suggested passwords (or use your own)
echo "POSTGRES_PASSWORD_STAGING: staging_postgres_secure_password_2024"
echo "AIRFLOW_PASSWORD_STAGING: staging_airflow_admin_2024"
```

## Environment Setup

The staging environment will be created with:

- **Airflow Web UI**: http://localhost:8081 (different from dev port 8080)
- **PostgreSQL**: localhost:5433 (different from dev port 5432)  
- **Database**: `stdev_calculations_staging`
- **User**: `airflow_staging`
- **Separate volumes** for data isolation

## Testing the Setup

After adding secrets, test by:

1. Create a `develop` branch if you don't have one:
   ```bash
   git checkout -b develop
   git push origin develop
   ```

2. Make a small change and push to `develop`:
   ```bash
   # Make a small change (e.g., update README)
   git add .
   git commit -m "Test staging deployment"
   git push origin develop
   ```

3. Check GitHub Actions tab to see the deployment in progress

## Troubleshooting

If deployment fails, check:
- All 4 secrets are properly set in GitHub
- Secrets don't have extra spaces or newlines
- Docker is available in the GitHub runner (should be by default)
- Port conflicts (staging uses 8081, 5433)

## Security Notes

- These are staging credentials - use different ones for production
- Fernet key must be exactly 32 bytes when base64 decoded
- Store production secrets separately and never commit them to code
- Consider using GitHub Environments for additional protection
