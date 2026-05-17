# packages/dqt/tests/checks/test_suggest_eval.py
"""Eval gate: ≥70% of labeled fixtures must produce at least one expected suggestion slug."""
from dqt.checks.suggest import ColumnProfile, suggest_checks_for_column

FIXTURES = [
    # (profile_kwargs, accepted_slugs_set, description)
    ({"name": "id", "data_type": "integer", "null_fraction": 0.0, "distinct_count": 100000, "is_likely_pk": True}, {"null_fraction", "uniqueness"}, "integer PK"),
    ({"name": "user_id", "data_type": "integer", "null_fraction": 0.02, "distinct_count": 5000, "is_likely_fk": True}, {"referential_integrity"}, "FK column"),
    ({"name": "email", "data_type": "text", "null_fraction": 0.0, "distinct_count": 50000, "is_likely_email": True, "sample_values": ["alice@example.com"]}, {"regex_match"}, "email column"),
    ({"name": "status", "data_type": "text", "null_fraction": 0.01, "distinct_count": 4, "is_likely_enum": True, "sample_values": ["active", "inactive", "pending", "deleted"]}, {"set_membership"}, "enum column"),
    ({"name": "country_code", "data_type": "text", "null_fraction": 0.0, "distinct_count": 50, "is_likely_country": True, "sample_values": ["US", "GB", "DE"]}, {"set_membership"}, "country code"),
    ({"name": "created_at", "data_type": "timestamp", "null_fraction": 0.0, "distinct_count": 90000, "is_likely_timestamp": True}, {"freshness_seconds_behind"}, "timestamp"),
    ({"name": "amount", "data_type": "float", "null_fraction": 0.0, "distinct_count": 10000, "is_likely_currency": True, "min_value": -5.0, "max_value": 5000.0}, {"value_in_range"}, "currency with negatives"),
    ({"name": "price", "data_type": "float", "null_fraction": 0.0, "distinct_count": 1000, "is_likely_currency": True, "min_value": 0.0, "max_value": 999.0}, {"value_in_range"}, "price no negatives"),
    ({"name": "revenue", "data_type": "decimal", "null_fraction": 0.0, "distinct_count": 50000, "min_value": 0.0, "max_value": 1e6}, {"mad_outlier_fraction"}, "heavy-tailed numeric"),
    ({"name": "score", "data_type": "float", "null_fraction": 0.05, "distinct_count": 10000, "min_value": 0.0, "max_value": 1.0}, {"mad_outlier_fraction", "null_fraction"}, "score with nulls"),
    ({"name": "transaction_id", "data_type": "varchar", "null_fraction": 0.0, "distinct_count": 1000000, "is_likely_pk": True}, {"uniqueness"}, "varchar PK"),
    ({"name": "product_id", "data_type": "bigint", "null_fraction": 0.0, "distinct_count": 50000, "is_likely_fk": True}, {"referential_integrity"}, "bigint FK"),
    ({"name": "user_email", "data_type": "varchar", "null_fraction": 0.0, "distinct_count": 8000, "is_likely_email": True, "sample_values": ["b@c.net"]}, {"regex_match"}, "user_email"),
    ({"name": "payment_status", "data_type": "varchar", "null_fraction": 0.0, "distinct_count": 3, "is_likely_enum": True, "sample_values": ["paid", "unpaid", "refunded"]}, {"set_membership"}, "payment status enum"),
    ({"name": "country", "data_type": "char", "null_fraction": 0.0, "distinct_count": 40, "is_likely_country": True, "sample_values": ["US", "CA", "MX"]}, {"set_membership"}, "country char"),
    ({"name": "updated_at", "data_type": "datetime", "null_fraction": 0.1, "distinct_count": 80000, "is_likely_timestamp": True}, {"freshness_seconds_behind"}, "nullable updated_at"),
    ({"name": "order_total", "data_type": "numeric", "null_fraction": 0.0, "distinct_count": 20000, "is_likely_currency": True, "min_value": -100.0, "max_value": 10000.0}, {"value_in_range"}, "order_total with refunds"),
    ({"name": "session_duration", "data_type": "integer", "null_fraction": 0.15, "distinct_count": 3000, "min_value": 0, "max_value": 7200}, {"mad_outlier_fraction", "null_fraction"}, "session duration"),
    ({"name": "category", "data_type": "text", "null_fraction": 0.02, "distinct_count": 12, "is_likely_enum": True, "sample_values": ["electronics", "books", "clothing"]}, {"set_membership"}, "category enum"),
    ({"name": "discount_pct", "data_type": "float", "null_fraction": 0.3, "distinct_count": 50, "min_value": 0.0, "max_value": 1.0}, {"null_fraction"}, "discount percentage"),
    ({"name": "vendor_id", "data_type": "integer", "null_fraction": 0.0, "distinct_count": 500, "is_likely_fk": True}, {"referential_integrity"}, "vendor FK"),
    ({"name": "signup_email", "data_type": "text", "null_fraction": 0.0, "distinct_count": 100000, "is_likely_email": True, "sample_values": ["x@y.com"]}, {"regex_match"}, "signup email"),
    ({"name": "plan_type", "data_type": "varchar", "null_fraction": 0.0, "distinct_count": 5, "is_likely_enum": True, "sample_values": ["free", "starter", "pro", "enterprise", "trial"]}, {"set_membership"}, "plan type enum"),
    ({"name": "invoice_date", "data_type": "date", "null_fraction": 0.0, "distinct_count": 365, "is_likely_timestamp": True}, {"freshness_seconds_behind"}, "invoice date"),
    ({"name": "mrr", "data_type": "float", "null_fraction": 0.0, "distinct_count": 5000, "is_likely_currency": True, "min_value": 0.0, "max_value": 50000.0}, {"value_in_range"}, "MRR metric"),
    ({"name": "churn_flag", "data_type": "boolean", "null_fraction": 0.0, "distinct_count": 2, "is_likely_enum": True, "sample_values": ["true", "false"]}, {"set_membership"}, "boolean flag enum"),
    ({"name": "lat", "data_type": "float", "null_fraction": 0.05, "distinct_count": 100000, "min_value": -90.0, "max_value": 90.0}, {"mad_outlier_fraction", "null_fraction"}, "latitude"),
    ({"name": "record_id", "data_type": "uuid", "null_fraction": 0.0, "distinct_count": 500000, "is_likely_pk": True}, {"null_fraction", "uniqueness"}, "UUID PK"),
    ({"name": "tax_rate", "data_type": "float", "null_fraction": 0.0, "distinct_count": 20, "is_likely_enum": True, "sample_values": ["0.0", "0.1", "0.15", "0.2"]}, {"set_membership"}, "tax rate enum"),
    ({"name": "session_count", "data_type": "integer", "null_fraction": 0.0, "distinct_count": 1000, "min_value": 0, "max_value": 500}, {"mad_outlier_fraction"}, "integer count column"),
]


def _defaults() -> dict:
    return dict(
        null_fraction=0.0, distinct_count=100, sample_values=[],
        min_value=None, max_value=None,
        is_likely_pk=False, is_likely_fk=False, is_likely_enum=False,
        is_likely_email=False, is_likely_timestamp=False,
        is_likely_currency=False, is_likely_country=False,
        data_type="text",
    )


def test_suggestion_eval_gate():
    passed = 0
    failed_descriptions = []
    for kwargs, expected_slugs, description in FIXTURES:
        profile = ColumnProfile(**{**_defaults(), **kwargs})
        suggestions = suggest_checks_for_column(profile, use_llm=False)
        got_slugs = {s.detector_slug for s in suggestions}
        if got_slugs.intersection(expected_slugs):
            passed += 1
        else:
            failed_descriptions.append(
                f"  FAIL [{description}]: expected one of {expected_slugs}, got {got_slugs}"
            )

    total = len(FIXTURES)
    rate = passed / total
    print(f"\nSuggestion eval: {passed}/{total} = {rate:.1%}")
    for msg in failed_descriptions:
        print(msg)

    assert rate >= 0.70, (
        f"Suggestion acceptance rate {rate:.1%} is below the 70% gate "
        f"({passed}/{total} passed)"
    )
