<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Apache Airflow DAG Project Instructions

This is an Apache Airflow project for calculating rolling standard deviations of financial price data. The project uses Docker for containerization and PostgreSQL for data storage.

## Project Structure
- `dags/`: Contains Airflow DAG definitions
- `plugins/`: Contains custom Python modules and operators
- `data/`: Input data directory (parquet files)
- `results/`: Output directory for results
- `docker-compose.yml`: Docker orchestration configuration
- `Dockerfile`: Airflow container configuration
- `init-db.sql`: PostgreSQL database initialization

## Key Components
- **IncrementalStdevCalculator**: Efficient rolling standard deviation calculator with state persistence
- **PostgreSQL Integration**: Stores both raw data and calculated results
- **Docker Containerization**: Complete containerized environment with Airflow + PostgreSQL

## Coding Guidelines
- Follow PEP 8 Python coding standards
- Use type hints where appropriate
- Include comprehensive docstrings for functions and classes
- Implement proper error handling and logging
- Use Airflow best practices for DAG definition and task dependencies
- Optimize for performance when processing large datasets
- Maintain state persistence for incremental calculations

## Data Processing Notes
- Input data is hourly price snapshots with bid/mid/ask prices
- Rolling window size is 20 periods
- Gap detection resets calculation state for data integrity
- Results include standard deviations for each price type per security per timestamp
