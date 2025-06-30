# Deployment Guide

This document outlines the deployment strategy and processes for the STDEV DAG project.

## Deployment Environments

### 1. Development
- **Branch**: `feature/*`, local development
- **Purpose**: Local development and testing
- **Access**: `docker-compose up -d`
- **URL**: http://localhost:8080

### 2. Staging
- **Branch**: `develop`
- **Purpose**: Integration testing and validation
- **Deployment**: Automated via GitHub Actions
- **URL**: http://staging.your-domain.com:8081
- **Database**: `stdev_calculations_staging` (port 5433)

### 3. Production
- **Branch**: `main`
- **Purpose**: Live production workloads
- **Deployment**: Automated via GitHub Actions (with manual approval)
- **URL**: http://production.your-domain.com
- **Database**: `stdev_calculations_prod`

## CI/CD Pipeline Flow

```
Feature Branch → PR → develop → Staging Deploy → main → Production Deploy
```

### Automated Triggers
- **Push to `develop`**: Triggers staging deployment
- **Push to `main`**: Triggers production deployment (after staging success)
- **Pull Requests**: Run tests and validation only

## Environment Variables

### Staging Environment
Required secrets in GitHub repository settings:
- `POSTGRES_PASSWORD_STAGING`
- `FERNET_KEY_STAGING`
- `WEBSERVER_SECRET_KEY_STAGING`
- `AIRFLOW_PASSWORD_STAGING`

### Production Environment
Required secrets in GitHub repository settings:
- `POSTGRES_PASSWORD_PROD`
- `FERNET_KEY_PROD`
- `WEBSERVER_SECRET_KEY_PROD`
- `AIRFLOW_PASSWORD_PROD`

## Deployment Steps

### Manual Staging Deployment
```bash
# Set environment variables
export POSTGRES_PASSWORD_STAGING="your-staging-password"
export FERNET_KEY_STAGING="your-staging-fernet-key"
export WEBSERVER_SECRET_KEY_STAGING="your-staging-webserver-key"
export AIRFLOW_PASSWORD_STAGING="your-staging-airflow-password"

# Deploy to staging
docker-compose -f docker-compose.staging.yml up -d --build

# Check deployment health
curl -f http://localhost:8081/health
```

### Manual Production Deployment
```bash
# Production deployment (to be implemented)
# Would typically involve:
# 1. Blue-green deployment
# 2. Database migrations
# 3. Rolling updates
# 4. Health checks
# 5. Rollback procedures
```

## Health Checks

### Staging Health Checks
- ✅ Airflow webserver responding
- ✅ PostgreSQL connection
- ✅ DAG loading without errors
- ✅ Task execution capability

### Production Health Checks
- ✅ All staging checks
- ✅ Database replication status
- ✅ Backup verification
- ✅ Performance metrics
- ✅ Security validation

## Rollback Procedures

### Staging Rollback
```bash
# Stop current deployment
docker-compose -f docker-compose.staging.yml down

# Revert to previous version
git checkout <previous-commit>
docker-compose -f docker-compose.staging.yml up -d --build
```

### Production Rollback
```bash
# Production rollback procedures (to be implemented)
# Would involve blue-green switch or container rollback
```

## Monitoring and Alerting

### Current Status
- ❌ Application monitoring (not implemented)
- ❌ Infrastructure monitoring (not implemented)
- ❌ Log aggregation (not implemented)
- ❌ Alerting system (not implemented)

### To Be Implemented
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or similar
- **Alerting**: PagerDuty/Slack integration
- **Metrics**: DAG success rates, execution times, resource utilization

## Security Considerations

### Current
- ✅ Environment-specific credentials
- ✅ GitHub secrets management
- ✅ Non-root container execution
- ✅ Network isolation

### To Be Implemented
- ⚠️ SSL/TLS termination
- ⚠️ Authentication integration (LDAP/SSO)
- ⚠️ Network security policies
- ⚠️ Vulnerability scanning

## Disaster Recovery

### Backup Strategy
- **Database**: Daily automated backups
- **Configuration**: Version controlled
- **Data**: Persistent volume backups

### Recovery Procedures
1. Restore database from backup
2. Deploy from known good commit
3. Verify data integrity
4. Resume operations

## Next Steps for Full Production Readiness

1. **Infrastructure as Code**: Terraform/CloudFormation
2. **Container Orchestration**: Kubernetes deployment
3. **Service Mesh**: Istio for advanced traffic management
4. **Observability**: Full monitoring stack
5. **Security**: Complete security hardening
6. **Load Testing**: Performance validation
7. **Documentation**: Runbooks and procedures
