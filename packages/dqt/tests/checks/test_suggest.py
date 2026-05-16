# packages/dqt/tests/checks/test_suggest.py
from dqt.checks.suggest import ColumnProfile, SuggestedCheck, suggest_checks_for_column


def _prof(**kw) -> ColumnProfile:
    defaults = dict(
        name="col", data_type="text", null_fraction=0.0, distinct_count=10,
        sample_values=[], min_value=None, max_value=None,
        is_likely_pk=False, is_likely_fk=False, is_likely_enum=False,
        is_likely_email=False, is_likely_timestamp=False,
        is_likely_currency=False, is_likely_country=False,
    )
    return ColumnProfile(**{**defaults, **kw})


def test_pk_gets_null_fraction_and_uniqueness():
    prof = _prof(name="id", data_type="integer", is_likely_pk=True, null_fraction=0.0)
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "null_fraction" in slugs
    assert "uniqueness" in slugs


def test_email_gets_regex():
    prof = _prof(name="email", data_type="text", is_likely_email=True,
                 sample_values=["a@b.com", "c@d.org"])
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "regex_match" in slugs


def test_enum_gets_set_membership():
    prof = _prof(name="status", data_type="text", is_likely_enum=True, distinct_count=3,
                 sample_values=["active", "inactive", "pending"])
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "set_membership" in slugs


def test_timestamp_gets_freshness():
    prof = _prof(name="created_at", data_type="timestamp", is_likely_timestamp=True)
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "freshness_seconds_behind" in slugs


def test_currency_negative_min_gets_value_in_range():
    prof = _prof(name="amount", data_type="float", is_likely_currency=True,
                 min_value=-5.0, max_value=1000.0)
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "value_in_range" in slugs


def test_country_gets_set_membership_iso():
    prof = _prof(name="country_code", data_type="text", is_likely_country=True,
                 distinct_count=30, sample_values=["US", "GB", "DE"])
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "set_membership" in slugs
    sm = next(s for s in suggestions if s.detector_slug == "set_membership")
    assert "US" in sm.params.get("allowed_values", [])


def test_fk_gets_referential_integrity():
    prof = _prof(name="user_id", data_type="integer", is_likely_fk=True)
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "referential_integrity" in slugs


def test_numeric_heavy_tailed_gets_mad():
    prof = _prof(name="revenue", data_type="float", distinct_count=5000,
                 min_value=0.0, max_value=1_000_000.0)
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "mad_outlier_fraction" in slugs


def test_all_columns_get_null_fraction_baseline():
    prof = _prof(name="any_col")
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "null_fraction" in slugs


def test_confidence_scores_in_range():
    prof = _prof(name="id", is_likely_pk=True)
    for s in suggest_checks_for_column(prof, use_llm=False):
        assert 0.0 <= s.confidence <= 1.0


def test_rationale_is_non_empty():
    prof = _prof(name="email", is_likely_email=True)
    for s in suggest_checks_for_column(prof, use_llm=False):
        assert s.rationale.strip()


def test_no_duplicate_slugs():
    prof = _prof(name="id", is_likely_pk=True, is_likely_country=True)
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert len(slugs) == len(set(slugs)), "Duplicate detector slugs in suggestions"
