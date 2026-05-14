-- Idempotent seed for BigQuery live adapter tests.
-- Replace {project} with your GCP_PROJECT_ID before running.
CREATE SCHEMA IF NOT EXISTS `{project}.dqt_test`;

CREATE TABLE IF NOT EXISTS `{project}.dqt_test.orders` (
    order_id    INT64,
    amount      FLOAT64,
    status      STRING,
    created_at  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `{project}.dqt_test.daily_metrics` (
    date        DATE,
    value       FLOAT64,
    metric_name STRING
);

-- BigQuery does not support INSERT ... WHERE NOT EXISTS natively.
-- Use MERGE for idempotent row inserts.
MERGE `{project}.dqt_test.orders` AS t
USING (
    SELECT
        ord + 1                                              AS order_id,
        ROUND(RAND() * 499 + 1, 2)                          AS amount,
        CASE MOD(ord, 3)
            WHEN 0 THEN 'pending'
            WHEN 1 THEN 'complete'
            ELSE 'cancelled'
        END                                                  AS status,
        TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 365) AS INT64) DAY) AS created_at
    FROM UNNEST(GENERATE_ARRAY(0, 999)) AS ord
) AS s
ON t.order_id = s.order_id
WHEN NOT MATCHED THEN
    INSERT (order_id, amount, status, created_at)
    VALUES (s.order_id, s.amount, s.status, s.created_at);

MERGE `{project}.dqt_test.daily_metrics` AS t
USING (
    SELECT
        DATE_SUB(CURRENT_DATE(), INTERVAL d DAY) AS date,
        ROUND(RAND() * 99 + 1, 4)               AS value,
        'revenue'                                AS metric_name
    FROM UNNEST(GENERATE_ARRAY(0, 89)) AS d
) AS s
ON t.date = s.date AND t.metric_name = s.metric_name
WHEN NOT MATCHED THEN
    INSERT (date, value, metric_name)
    VALUES (s.date, s.value, s.metric_name);
