-- Create tables in the main airflow database

-- Create table for raw price data
CREATE TABLE IF NOT EXISTS price_data (
    id SERIAL PRIMARY KEY,
    security_id VARCHAR(50) NOT NULL,
    snap_time TIMESTAMP NOT NULL,
    bid DECIMAL(10, 4),
    mid DECIMAL(10, 4),
    ask DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(security_id, snap_time)
);

-- Create table for standard deviation results
CREATE TABLE IF NOT EXISTS stdev_results (
    id SERIAL PRIMARY KEY,
    security_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    bid_stdev DECIMAL(10, 6),
    mid_stdev DECIMAL(10, 6),
    ask_stdev DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(security_id, timestamp)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_price_data_security_time ON price_data(security_id, snap_time);
CREATE INDEX IF NOT EXISTS idx_stdev_results_security_time ON stdev_results(security_id, timestamp);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow;
