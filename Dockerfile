# Multi-stage Docker build for Apache Airflow with Standard Deviation Calculator
# Stage 1: Builder stage for dependencies
FROM apache/airflow:2.8.1-python3.11 as builder

USER root

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment directory with proper permissions
RUN mkdir -p /opt/venv && chown -R airflow:root /opt/venv

USER airflow

# Copy requirements first for better Docker layer caching
COPY requirements.txt /tmp/requirements.txt
COPY requirements-dev.txt /tmp/requirements-dev.txt

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Stage 2: Runtime stage
FROM apache/airflow:2.8.1-python3.11 as runtime

USER root

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for better security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

USER airflow

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application files with proper permissions
COPY --chown=airflow:root dags/ /opt/airflow/dags/
COPY --chown=airflow:root plugins/ /opt/airflow/plugins/

# Create config directory
RUN mkdir -p /opt/airflow/config

# Create directories with proper permissions
RUN mkdir -p /opt/airflow/data /opt/airflow/results /opt/airflow/logs \
    && chown -R airflow:root /opt/airflow/data /opt/airflow/results

# Set environment variables
ENV PYTHONPATH=/opt/airflow/plugins:$PYTHONPATH
ENV AIRFLOW_HOME=/opt/airflow
ENV AIRFLOW__CORE__LOAD_EXAMPLES=false
ENV AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=true
ENV AIRFLOW__WEBSERVER__EXPOSE_CONFIG=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Labels for better container management
LABEL maintainer="data-engineering@company.com"
LABEL version="1.0.0"
LABEL description="Apache Airflow with Standard Deviation Calculator"
LABEL org.opencontainers.image.source="https://github.com/company/stdev_dag"

# Switch to non-root user
USER airflow

# Default command
CMD ["airflow", "webserver"]
