# Staging Deployment Workflow Explanation

## How Automated Staging Deployment Works

### 🚀 **Trigger**: Push to `develop` Branch
When you run:
```bash
git push origin develop
```

### 📋 **What Happens Automatically**:

#### 1. **GitHub Actions Detects Push**
```yaml
if: github.ref == 'refs/heads/develop' && github.event_name == 'push'
```
- Only triggers on pushes to `develop` branch
- Not on pull requests or other branches

#### 2. **Prerequisites Run First**
```yaml
needs: [test, dag-validation]
```
- Waits for unit tests to pass
- Waits for integration tests to pass  
- Waits for DAG validation to pass
- **If any fail, staging deployment is skipped**

#### 3. **Environment Setup**
```yaml
environment: staging
```
- Uses GitHub "staging" environment
- Pulls secrets from GitHub repository settings
- Creates isolated staging configuration

#### 4. **Deployment Process**
The workflow automatically:

```bash
# Creates environment file with secrets
cat > .env.staging << EOF
POSTGRES_PASSWORD_STAGING=${{ secrets.POSTGRES_PASSWORD_STAGING }}
FERNET_KEY_STAGING=${{ secrets.FERNET_KEY_STAGING }}
# ... other secrets
EOF

# Builds and starts staging containers
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
```

#### 5. **Health Checks**
```bash
# Waits for services to be healthy
timeout 300 bash -c 'until docker-compose ps | grep -q "healthy"; do sleep 10; done'

# Tests Airflow web interface
curl -f http://localhost:8081/health || exit 1

# Verifies DAGs load correctly
docker-compose exec airflow-staging python -c "verify DAG loading script"
```

#### 6. **Results**
- ✅ **Success**: Staging environment is running and ready
- ❌ **Failure**: Deployment stops, logs show what went wrong
- 📧 **Notification**: GitHub shows deployment status

## 🎯 **End Result**

After successful staging deployment, you have:

### **Staging Environment Running**
- **Airflow Web UI**: http://localhost:8081
- **Database**: PostgreSQL on port 5433
- **Completely separate** from your dev environment (port 8080, 5432)
- **Same code** as what you pushed to `develop`

### **What You Can Do**
1. **Test your changes** in production-like environment
2. **Run DAGs** to verify they work end-to-end
3. **Check database** to see data processing results
4. **Share with team** for review before merging to `main`

### **Comparison: Dev vs Staging vs Production**

| Environment | Branch | Port | Database | Purpose |
|-------------|--------|------|----------|---------|
| **Development** | `feature/*` | 8080 | 5432 | Local coding |
| **Staging** | `develop` | 8081 | 5433 | Integration testing |
| **Production** | `main` | 80/443 | prod DB | Live workloads |

## 🔄 **Complete Workflow Example**

```bash
# 1. Developer makes changes
git checkout develop
git pull origin develop

# 2. Make changes to code
echo "# Updated feature" >> README.md

# 3. Commit and push
git add .
git commit -m "Add new feature"
git push origin develop

# 4. GitHub Actions automatically:
#    - Runs all tests
#    - If tests pass, deploys to staging
#    - Runs health checks
#    - Reports success/failure

# 5. Team can test at http://localhost:8081
# 6. If staging looks good, merge to main for production
```

## 🛡️ **Safety Features**

- **Tests must pass** before deployment
- **Isolated environment** (won't break dev or prod)
- **Automatic rollback** if health checks fail
- **GitHub environments** provide audit logs
- **Manual approval** can be required (optional)

This gives you **continuous deployment** to staging while maintaining safety and quality controls!
