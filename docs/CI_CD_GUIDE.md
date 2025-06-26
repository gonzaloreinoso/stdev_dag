# CI/CD Pipeline Documentation

## Overview

This project implements a comprehensive CI/CD pipeline for the Standard Deviation Calculation DAG using GitHub Actions. The pipeline ensures code quality, security, and reliable deployments across different environments.

## Pipeline Structure

### 1. Code Quality & Testing (`ci-cd.yml`)

The main pipeline includes the following stages:

#### Code Quality Stage
- **Black**: Code formatting verification
- **isort**: Import sorting verification  
- **flake8**: Linting and style checking
- **mypy**: Type checking (optional initially)
- **bandit**: Security vulnerability scanning

#### Testing Stages
- **Unit Tests**: Fast, isolated tests using pytest
- **DAG Validation**: Airflow DAG syntax and structure validation
- **Integration Tests**: End-to-end testing with PostgreSQL database

#### Docker Stage
- **Multi-stage build**: Optimized Docker image creation
- **Security scanning**: Trivy vulnerability assessment
- **Image publishing**: Container registry publishing

### 2. Security Pipeline (`security.yml`)

Dedicated security scanning workflow:

- **Static Analysis**: Bandit, Semgrep, Safety checks
- **Dependency Scanning**: Snyk vulnerability detection
- **Docker Security**: Trivy container scanning, Hadolint linting
- **Secrets Detection**: TruffleHog secret scanning

### 3. Deployment Stages

- **Staging Deployment**: Automatic deployment from `develop` branch
- **Production Deployment**: Automatic deployment from `main` branch
- **Health Checks**: Post-deployment verification

## Environment Configuration

### Development (`config/environments/dev.yaml`)
- Local development settings
- Minimal security requirements
- Debug capabilities enabled
- Small resource allocation

### Staging (`config/environments/staging.yaml`)
- Production-like environment
- Enhanced monitoring and alerting
- Moderate resource allocation
- SSL required

### Production (`config/environments/prod.yaml`)
- High availability configuration
- Maximum security settings
- Comprehensive monitoring
- Full resource allocation
- Backup and recovery enabled

## Code Quality Tools

### Pre-commit Hooks
The pipeline uses pre-commit hooks to catch issues early:

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Formatting and Linting
- **Black**: Code formatting (88 character line length)
- **isort**: Import sorting with Black compatibility
- **flake8**: Linting with custom configuration
- **mypy**: Type checking for better code quality

### Testing Strategy
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test complete workflows with database
- **DAG Tests**: Validate Airflow DAG structure and dependencies
- **Performance Tests**: Ensure processing meets time requirements

## Security Measures

### Static Analysis
- **Bandit**: Python security vulnerability scanning
- **Semgrep**: Advanced static analysis for security patterns
- **Safety**: Known vulnerability database checking

### Container Security
- **Multi-stage builds**: Reduced attack surface
- **Non-root user**: Container runs with limited privileges
- **Minimal base image**: Reduced package footprint
- **Security scanning**: Automated vulnerability assessment

### Secrets Management
- **Environment variables**: Sensitive data via environment
- **GitHub Secrets**: Secure storage of credentials
- **No hardcoded secrets**: Enforced through scanning

## Deployment Process

### Automated Deployment
1. **Code Push**: Developer pushes to branch
2. **Pipeline Trigger**: GitHub Actions workflow starts
3. **Quality Gates**: All quality checks must pass
4. **Security Scan**: Security vulnerabilities checked
5. **Build & Test**: Application built and tested
6. **Environment Deploy**: Automatic deployment to target environment
7. **Health Check**: Post-deployment verification

### Manual Deployment
For production deployments, manual approval can be required:

```yaml
environment: production
# Requires manual approval in GitHub
```

### Rollback Strategy
- **Docker tags**: Each build creates a unique tag
- **Database migrations**: Reversible migrations
- **Configuration rollback**: Previous configuration preserved

## Monitoring and Alerting

### Health Checks
- **Application health**: Airflow webserver health endpoint
- **Database connectivity**: PostgreSQL connection verification
- **DAG execution**: Task success/failure monitoring

### Alerting Channels
- **Email**: Development and operations teams
- **Slack**: Real-time notifications
- **PagerDuty**: Critical production alerts (production only)

### Metrics Collection
- **Task duration**: Processing time monitoring
- **Success rates**: DAG execution success tracking
- **Resource usage**: Memory and CPU utilization

## Troubleshooting

### Common Issues

#### Pipeline Failures
```bash
# Check workflow logs
gh run list
gh run view [run-id]

# Local debugging
pytest tests/unit/ -v
black --check .
flake8 .
```

#### Security Scan Failures
```bash
# Run security scans locally
bandit -r plugins/ dags/
safety check
semgrep --config=auto plugins/ dags/
```

#### Docker Build Issues
```bash
# Local Docker build
docker build -t stdev-dag:test .
docker run --rm stdev-dag:test python -c "import plugins.stdev_calculator"
```

### Performance Issues
- **Database connections**: Check connection pool settings
- **Memory usage**: Monitor container resource limits
- **Processing time**: Review algorithm efficiency

## Best Practices

### Code Quality
1. **Write tests first**: TDD approach for new features
2. **Keep functions small**: Single responsibility principle
3. **Use type hints**: Improve code readability and catch errors
4. **Document code**: Clear docstrings and comments

### Security
1. **Never commit secrets**: Use environment variables
2. **Keep dependencies updated**: Regular security updates
3. **Minimal permissions**: Principle of least privilege
4. **Regular security scans**: Automated vulnerability checking

### Performance
1. **Optimize queries**: Efficient database operations
2. **Cache results**: State persistence for incremental calculations
3. **Monitor resources**: Track memory and CPU usage
4. **Profile code**: Identify bottlenecks

### Deployment
1. **Test in staging**: Full validation before production
2. **Gradual rollouts**: Minimize risk of deployment issues
3. **Monitor closely**: Watch metrics after deployment
4. **Have rollback plan**: Quick recovery strategy
