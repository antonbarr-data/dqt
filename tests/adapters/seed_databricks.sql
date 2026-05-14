-- Idempotent seed for Databricks live adapter tests
CREATE SCHEMA IF NOT EXISTS dqt_test;

CREATE TABLE IF NOT EXISTS dqt_test.orders (
    order_id    BIGINT,
    amount      DOUBLE,
    status      STRING,
    created_at  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dqt_test.daily_metrics (
    date        DATE,
    value       DOUBLE,
    metric_name STRING
);

INSERT INTO dqt_test.orders (order_id, amount, status, created_at)
SELECT
    id + 1,
    round(rand() * 499 + 1, 2),
    CASE MOD(id, 3)
        WHEN 0 THEN 'pending'
        WHEN 1 THEN 'complete'
        ELSE 'cancelled'
    END,
    current_timestamp() - INTERVAL (CAST(rand() * 364 AS INT)) DAYS
FROM (SELECT explode(sequence(0, 999)) AS id)
WHERE (id + 1) NOT IN (SELECT order_id FROM dqt_test.orders);

INSERT INTO dqt_test.daily_metrics (date, value, metric_name)
SELECT
    current_date() - INTERVAL d DAYS,
    round(rand() * 99 + 1, 4),
    'revenue'
FROM (SELECT explode(sequence(0, 89)) AS d)
WHERE (current_date() - INTERVAL d DAYS) NOT IN (
    SELECT date FROM dqt_test.daily_metrics WHERE metric_name = 'revenue'
);
