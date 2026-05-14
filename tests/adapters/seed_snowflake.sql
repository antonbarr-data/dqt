-- Idempotent seed for Snowflake live adapter tests
CREATE SCHEMA IF NOT EXISTS dqt_test;

CREATE TABLE IF NOT EXISTS dqt_test.orders (
    order_id    INTEGER,
    amount      FLOAT,
    status      VARCHAR(20),
    created_at  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dqt_test.daily_metrics (
    date        DATE,
    value       FLOAT,
    metric_name VARCHAR(50)
);

INSERT INTO dqt_test.orders (order_id, amount, status, created_at)
SELECT
    seq4() + 1,
    round(uniform(1::float, 500::float, random()), 2),
    CASE mod(seq4(), 3)
        WHEN 0 THEN 'pending'
        WHEN 1 THEN 'complete'
        ELSE 'cancelled'
    END,
    dateadd('day', -uniform(0, 364, random()), current_timestamp())
FROM table(generator(rowcount => 1000))
WHERE (seq4() + 1) NOT IN (SELECT order_id FROM dqt_test.orders);

INSERT INTO dqt_test.daily_metrics (date, value, metric_name)
SELECT
    dateadd('day', -seq4(), current_date()),
    round(uniform(1::float, 100::float, random()), 4),
    'revenue'
FROM table(generator(rowcount => 90))
WHERE dateadd('day', -seq4(), current_date()) NOT IN (
    SELECT date FROM dqt_test.daily_metrics WHERE metric_name = 'revenue'
);
