"""Keep Track C fail-closed when Track B adds optional corpus integration tests."""

import pytest
from scripts.validate_phase1_track_c import validate_native_ci


def matrix():
    return {
        "source_sha256": "current-source",
        "conclusion": "success",
        "jobs": [
            {
                "platform": f"track-c-{platform}-latest",
                "passed": 871,
                "errors": 0,
                "failures": 0,
                "skipped": 0,
            }
            for platform in ("windows", "ubuntu", "macos")
        ],
    }


def optional_case():
    return {
        "classname": "tests.unit.test_gold",
        "name": "test_each_dev_gold_span_is_verbatim_in_the_corpus[dev-oil-why]",
        "reason": "corpus payload is not in git",
    }


def test_accepts_existing_zero_skip_receipts():
    validate_native_ci(matrix(), "current-source")


def test_accepts_only_named_optional_cases_with_recorded_reasons():
    ci = matrix()
    ci["jobs"][0].update(skipped=1, skipped_cases=[optional_case()])
    validate_native_ci(ci, "current-source")


@pytest.mark.parametrize("field", ["classname", "name", "reason"])
def test_rejects_unknown_skip_identity_or_reason(field):
    ci = matrix()
    case = optional_case()
    case[field] = "unexpected"
    ci["jobs"][0].update(skipped=1, skipped_cases=[case])
    with pytest.raises(ValueError, match="only named Track B skips"):
        validate_native_ci(ci, "current-source")


def test_rejects_unlisted_or_duplicate_skipped_cases():
    ci = matrix()
    ci["jobs"][0]["skipped"] = 1
    with pytest.raises(ValueError, match="only named Track B skips"):
        validate_native_ci(ci, "current-source")
    ci["jobs"][0].update(skipped=2, skipped_cases=[optional_case(), optional_case()])
    with pytest.raises(ValueError, match="only named Track B skips"):
        validate_native_ci(ci, "current-source")


def test_a_missing_reason_cannot_admit_an_unknown_case():
    ci = matrix()
    ci["jobs"][0].update(
        skipped=1,
        skipped_cases=[{"classname": "unknown", "name": "unknown", "reason": None}],
    )
    with pytest.raises(ValueError, match="only named Track B skips"):
        validate_native_ci(ci, "current-source")


@pytest.mark.parametrize("field", ["errors", "failures"])
def test_optional_skips_do_not_allow_failed_tests(field):
    ci = matrix()
    ci["jobs"][0][field] = 1
    with pytest.raises(ValueError, match="only named Track B skips"):
        validate_native_ci(ci, "current-source")


def test_rejects_stale_source_or_incomplete_platform_matrix():
    ci = matrix()
    with pytest.raises(ValueError, match="matrix is incomplete"):
        validate_native_ci(ci, "old-source")
    ci["jobs"][2]["platform"] = ci["jobs"][0]["platform"]
    with pytest.raises(ValueError, match="matrix is incomplete"):
        validate_native_ci(ci, "current-source")
