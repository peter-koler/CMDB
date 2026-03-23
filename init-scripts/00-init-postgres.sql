-- PostgreSQL initialization baseline for arco
-- Run with psql against maintenance DB (usually postgres):
--   psql -h <host> -p <port> -U postgres -d postgres -f init-scripts/00-init-postgres.sql

SELECT 'CREATE ROLE arco_user LOGIN PASSWORD ''arco_password'''
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'arco_user')
\gexec

SELECT 'CREATE DATABASE arco_db OWNER arco_user'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'arco_db')
\gexec

\connect arco_db
CREATE EXTENSION IF NOT EXISTS pgcrypto;
