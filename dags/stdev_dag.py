"""
Standard Deviation Calculation DAG

This DAG orchestrates the calculation of rolling standard deviations for financial price data.
It follows an ETL pattern:
1. Extract data from parquet file
2. Load raw data into PostgreSQL
3. Transform by calculating standard deviations
4. Load results into both file and PostgreSQL

The DAG uses the efficient incremental standard deviation calculator that maintains
calculation state for optimal performance.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os
from sqlalchemy import create_engine

# Add plugins directory to path for imports
sys.path.append('/opt/airflow/plugins')
from stdev_calculator import IncrementalStdevCalculator

# Default arguments for the DAG
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2021, 11, 20),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(seconds=5),
}

# DAG definition
dag = DAG(
    'stdev_calculation_pipeline',
    default_args=default_args,
    description='Calculate rolling standard deviations for financial price data',
    schedule_interval=timedelta(hours=1),  # Run every hour
    catchup=False,
    max_active_runs=1,
    tags=['finance', 'standard-deviation', 'etl'],
)

def extract_and_validate_data(**context):
    """
    Extract data from parquet file and perform basic validation.
    """
    data_path = Path('/opt/airflow/data/stdev_price_data.parq.gzip')
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    # Load and validate data
    df = pd.read_parquet(data_path)
    
    # Basic validation
    required_columns = ['security_id', 'snap_time', 'bid', 'mid', 'ask']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Check for data in the expected date range
    df['snap_time'] = pd.to_datetime(df['snap_time'])
    min_date = df['snap_time'].min()
    max_date = df['snap_time'].max()
    
    print(f"Data validation successful:")
    print(f"  - Records: {len(df):,}")
    print(f"  - Securities: {df['security_id'].nunique()}")
    print(f"  - Date range: {min_date} to {max_date}")
    print(f"  - Columns: {list(df.columns)}")
    
    return {
        'records_count': len(df),
        'securities_count': df['security_id'].nunique(),
        'min_date': str(min_date),
        'max_date': str(max_date)
    }

def load_raw_data_to_postgres(**context):
    """
    Load raw price data into PostgreSQL.
    """
    data_path = Path('/opt/airflow/data/stdev_price_data.parq.gzip')
    df = pd.read_parquet(data_path)
    df['snap_time'] = pd.to_datetime(df['snap_time'])
    
    # Connect to PostgreSQL - use the main airflow database for now
    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    engine = postgres_hook.get_sqlalchemy_engine()
    
    # Insert data using pandas to_sql with conflict handling
    records_inserted = 0
    batch_size = 1000
    
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        try:
            batch.to_sql(
                'price_data',
                engine,
                if_exists='append',
                index=False,
                method='multi'
            )
            records_inserted += len(batch)
        except Exception as e:
            # Handle duplicates gracefully
            if 'unique constraint' in str(e).lower():
                print(f"Skipping batch {i//batch_size + 1} due to duplicate records")
                continue
            else:
                raise e
    
    print(f"Successfully loaded {records_inserted:,} records to PostgreSQL")
    return {'records_inserted': records_inserted}

def calculate_standard_deviations(**context):
    """
    Calculate rolling standard deviations using the incremental calculator.
    """
    # Get execution date from context
    execution_date = context['execution_date']
    
    # Define calculation period (you can adjust this based on your needs)
    start_time = '2021-11-20 00:00:00'
    end_time = '2021-11-23 09:00:00'
    
    # Initialize calculator
    price_path = Path('/opt/airflow/data/stdev_price_data.parq.gzip')
    state_path = Path('/opt/airflow/results/calculation_state.json')
    
    calculator = IncrementalStdevCalculator(
        price_path=price_path,
        window_size=20,
        state_path=state_path
    )
    
    # Load data and calculate
    calculator.load_data()
    result_df = calculator.process(start_time, end_time)
    
    # Store results for next task
    results_path = Path('/opt/airflow/results/stdev_results.csv')
    calculator.save(result_df, results_path)
    
    print(f"Calculated standard deviations for {len(result_df):,} records")
    print(f"Results saved to: {results_path}")
    
    return {
        'results_count': len(result_df),
        'results_path': str(results_path),
        'securities_processed': result_df['security_id'].nunique()
    }

def save_results_to_postgres(**context):
    """
    Save standard deviation results to PostgreSQL.
    """
    results_path = Path('/opt/airflow/results/stdev_results.csv')
    
    if not results_path.exists():
        raise FileNotFoundError(f"Results file not found: {results_path}")
    
    # Load results
    df = pd.read_csv(results_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Connect to PostgreSQL - use the main airflow database for now
    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    engine = postgres_hook.get_sqlalchemy_engine()
    
    # Insert results
    records_inserted = 0
    batch_size = 1000
    
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        try:
            batch.to_sql(
                'stdev_results',
                engine,
                if_exists='append',
                index=False,
                method='multi'
            )
            records_inserted += len(batch)
        except Exception as e:
            if 'unique constraint' in str(e).lower():
                print(f"Skipping batch {i//batch_size + 1} due to duplicate records")
                continue
            else:
                raise e
    
    print(f"Successfully saved {records_inserted:,} results to PostgreSQL")
    return {'records_inserted': records_inserted}

def cleanup_temp_files(**context):
    """
    Clean up temporary files and perform housekeeping.
    """
    # You can add cleanup logic here if needed
    # For now, we'll just report on the files
    results_dir = Path('/opt/airflow/results')
    
    files_info = []
    for file_path in results_dir.glob('*'):
        if file_path.is_file():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            files_info.append(f"  - {file_path.name}: {size_mb:.2f} MB")
    
    print("Files in results directory:")
    print("\n".join(files_info))
    
    return {'files_count': len(files_info)}

# Define tasks
extract_task = PythonOperator(
    task_id='extract_and_validate_data',
    python_callable=extract_and_validate_data,
    dag=dag,
)

load_raw_data_task = PythonOperator(
    task_id='load_raw_data_to_postgres',
    python_callable=load_raw_data_to_postgres,
    dag=dag,
)

calculate_task = PythonOperator(
    task_id='calculate_standard_deviations',
    python_callable=calculate_standard_deviations,
    dag=dag,
)

save_results_task = PythonOperator(
    task_id='save_results_to_postgres',
    python_callable=save_results_to_postgres,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id='cleanup_temp_files',
    python_callable=cleanup_temp_files,
    dag=dag,
)

# Define task dependencies
extract_task >> load_raw_data_task >> calculate_task >> [save_results_task, cleanup_task]
