# Standard Deviation Calculation DAG

This project implements an Apache Airflow DAG for calculating rolling standard deviations of financial price data. It uses an efficient incremental calculation approach with state persistence and includes full Docker containerization with PostgreSQL integration.

## Problem Statement

Calculate rolling standard deviations for financial price data (bid, mid, ask) across multiple securities. The calculation requires:
- 20-period rolling window
- Hourly price snapshots
- Gap detection and state reset for data integrity
- High-performance processing (< 1 second benchmark)
- State persistence for incremental calculations

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Parquet File  │───▶│   Airflow DAG    │───▶│   PostgreSQL    │
│  (Input Data)   │    │                  │    │   (Results)     │
└─────────────────┘    │  ┌─────────────┐ │    └─────────────────┘
                       │  │  Extract    │ │
                       │  │  Transform  │ │    ┌─────────────────┐
                       │  │  Load       │ │───▶│   CSV Files     │
                       │  └─────────────┘ │    │   (Results)     │
                       └──────────────────┘    └─────────────────┘
```

## Project Structure

```
stdev_dag/
├── dags/
│   └── stdev_dag.py              # Main Airflow DAG
├── plugins/
│   └── stdev_calculator.py       # Incremental standard deviation calculator
├── data/
│   └── stdev_price_data.parq.gzip # Input data file (place here)
├── results/                      # Output directory
├── docker-compose.yml            # Docker orchestration
├── Dockerfile                    # Airflow container
├── init-db.sql                  # PostgreSQL initialization
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Features

### Efficient Incremental Calculation
- **O(1) window updates** using deques
- **State persistence** for resuming calculations
- **Gap detection** with automatic state reset
- **Memory efficient** processing of large datasets

### Airflow DAG Tasks
1. **Extract & Validate Data** - Load and validate parquet file
2. **Load Raw Data to PostgreSQL** - Insert price data into database
3. **Calculate Standard Deviations** - Run incremental calculations
4. **Save Results to PostgreSQL** - Store results in database
5. **Save Results to File** - Export results to CSV
6. **Cleanup** - Housekeeping tasks

### Docker Integration
- **Airflow 2.8.1** with LocalExecutor
- **PostgreSQL 13** for data storage
- **Automated database initialization**
- **Volume persistence** for data and logs

## Quick Start

### Prerequisites
- Docker and Docker Compose
- At least 4GB RAM available
- Input data file: `stdev_price_data.parq.gzip`

### Setup and Run

1. **Clone and prepare the project:**
   ```bash
   cd stdev_dag
   # Place your data file in the data/ directory
   cp /path/to/stdev_price_data.parq.gzip ./data/
   ```

2. **Start the services:**
   ```powershell
   docker-compose up -d
   ```

3. **Access Airflow Web UI:**
   - URL: http://localhost:8080
   - Username: `airflow`
   - Password: `airflow`

4. **Trigger the DAG:**
   - Navigate to the `stdev_calculation_pipeline` DAG
   - Toggle it ON and trigger a run

### Database Access

PostgreSQL is accessible at:
- Host: `localhost:5432`
- Database: `stdev_calculations`
- Username: `airflow`
- Password: `airflow`

## Data Schema

### Input Data (`price_data` table)
```sql
CREATE TABLE price_data (
    id SERIAL PRIMARY KEY,
    security_id VARCHAR(50) NOT NULL,
    snap_time TIMESTAMP NOT NULL,
    bid DECIMAL(10, 4),
    mid DECIMAL(10, 4),
    ask DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Output Data (`stdev_results` table)
```sql
CREATE TABLE stdev_results (
    id SERIAL PRIMARY KEY,
    security_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    bid_stdev DECIMAL(10, 6),
    mid_stdev DECIMAL(10, 6),
    ask_stdev DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Configuration

### Environment Variables
- `AIRFLOW_UID`: User ID for Airflow (default: 50000)
- `_AIRFLOW_WWW_USER_USERNAME`: Web UI username (default: airflow)
- `_AIRFLOW_WWW_USER_PASSWORD`: Web UI password (default: airflow)

### DAG Configuration
- **Schedule**: Every hour (`timedelta(hours=1)`)
- **Start Date**: 2021-11-20
- **Catchup**: Disabled
- **Max Active Runs**: 1

## Performance

The incremental calculator is optimized for high performance:
- **Benchmark**: < 1 second processing time
- **Memory Efficient**: Uses deques for O(1) operations
- **State Persistence**: Avoids recalculation of existing data
- **Vectorized Operations**: Leverages pandas/numpy optimizations

## Monitoring and Troubleshooting

### Airflow Logs
```bash
# View logs
docker-compose logs airflow-scheduler
docker-compose logs airflow-webserver

# Follow logs in real-time
docker-compose logs -f airflow-scheduler
```

### Database Queries
```sql
-- Check data loading progress
SELECT security_id, COUNT(*) as records, 
       MIN(snap_time) as first_snap, 
       MAX(snap_time) as last_snap
FROM price_data 
GROUP BY security_id;

-- Check results
SELECT security_id, COUNT(*) as calculations,
       MIN(timestamp) as first_calc,
       MAX(timestamp) as last_calc
FROM stdev_results 
GROUP BY security_id;
```

### Common Issues

1. **Data file not found**: Ensure `stdev_price_data.parq.gzip` is in the `data/` directory
2. **PostgreSQL connection**: Check that the database service is healthy
3. **Memory issues**: Increase Docker memory allocation if needed
4. **Permission errors**: Ensure proper file permissions on volumes

## Extending the Project

### Adding New Tasks
1. Define the task function in the DAG file
2. Create a `PythonOperator` instance
3. Add task dependencies using `>>` operator

### Custom Calculations
1. Extend the `IncrementalStdevCalculator` class
2. Add new methods for additional statistical measures
3. Update the DAG to include new calculation tasks

### Additional Data Sources
1. Create new operators for different data sources
2. Update the database schema as needed
3. Modify the DAG to handle multiple input sources

## Development

### Debugging
- Use Airflow's built-in logging
- Add print statements for debugging (they appear in task logs)
- Use the Airflow web UI to inspect task instances and logs

### CI/CD Pipeline Status

#### ✅ Phase 1: Foundation (COMPLETED)
- GitHub Actions CI workflow
- Linting and formatting (Black, isort, Flake8)
- Pre-commit hooks
- Development environment setup

#### ✅ Phase 2: Testing (COMPLETED)
- Unit tests for calculator (100% coverage)
- Integration tests for DAGs
- Data quality validations
- Automated test execution in CI

#### 🚧 Phase 3: Deployment (IN PROGRESS)
- ✅ Staging deployment configuration
- ✅ Basic monitoring setup
- ⚠️ Production deployment (planned)
- ⚠️ Full monitoring and alerting (planned)

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment information.

### Running Tests
```bash
# Run all tests
python run_tests.py

# Run specific test types
pytest tests/unit/ -v
pytest tests/integration/ -v

# Run with coverage
pytest tests/unit/ --cov=plugins --cov-report=html
```

## License

This project is provided as-is for educational and development purposes.

## Support

For issues and questions:
1. Check the Airflow documentation: https://airflow.apache.org/docs/
2. Review task logs in the Airflow web UI
3. Check Docker container logs for infrastructure issues
