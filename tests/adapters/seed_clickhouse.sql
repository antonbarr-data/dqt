-- Idempotent seed for ClickHouse live adapter tests
CREATE DATABASE IF NOT EXISTS dqt_test;

CREATE TABLE IF NOT EXISTS dqt_test.orders (
    order_id    Int64,
    amount      Float64,
    status      String,
    created_at  DateTime
) ENGINE = MergeTree() ORDER BY order_id;

CREATE TABLE IF NOT EXISTS dqt_test.daily_metrics (
    date        Date,
    value       Float64,
    metric_name String
) ENGINE = MergeTree() ORDER BY (date, metric_name);

INSERT INTO dqt_test.orders
SELECT
    number + 1                            AS order_id,
    round(rand() % 50000 / 100.0, 2)     AS amount,
    ['pending','complete','cancelled'][rand() % 3 + 1] AS status,
    now() - toIntervalDay(rand() % 365)   AS created_at
FROM numbers(1000)
WHERE (number + 1) NOT IN (SELECT order_id FROM dqt_test.orders);

INSERT INTO dqt_test.daily_metrics
SELECT
    today() - toIntervalDay(number)       AS date,
    round(rand() % 10000 / 100.0, 4)     AS value,
    'revenue'                             AS metric_name
FROM numbers(90)
WHERE (today() - toIntervalDay(number)) NOT IN (
    SELECT date FROM dqt_test.daily_metrics WHERE metric_name = 'revenue'
);
