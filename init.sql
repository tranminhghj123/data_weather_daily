-- Creates airflow_db so Airflow has its own metadata database
-- weather_db is already created by POSTGRES_DB env var
CREATE DATABASE airflow_db;