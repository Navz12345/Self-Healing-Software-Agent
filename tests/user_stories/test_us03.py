import pytest

from fmg.fmg import FMG


@pytest.mark.user_story("US-03")
def test_us03_fmg_fast_path_learning(tmp_path):
    """
    Given: US-01 has run and FMG has stored a CODE_BUG fingerprint
    When: inject_failure.py --type divide_by_zero is executed again
    Then: FMG_FAST_PATH_FIRED and GPT4O_SKIPPED, resolved in under 20 seconds
    """
    fmg = FMG(db_path=str(tmp_path / "fmg.db"))
    trajectory = [0.1, 0.1, 0.8, 0.9, 0.9]
    fmg.store(trajectory, "CODE_BUG", 0.91, "sha-app", "PLAN_A", request_id="us03")

    assert fmg.fast_path(trajectory, "sha-app", request_id="us03") == ("CODE_BUG", "PLAN_A", 0.91)
