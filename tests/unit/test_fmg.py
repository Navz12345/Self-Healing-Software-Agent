from fmg.fmg import FMG


def test_fmg_fast_path_returns_cached_plan(tmp_path):
    fmg = FMG(db_path=str(tmp_path / "fmg.db"))
    fmg.store(
        [0.1, 0.1, 0.8, 0.9],
        "CODE_BUG",
        0.91,
        "sha-app",
        "PLAN_A",
        request_id="fmgtest",
    )

    assert fmg.fast_path([0.1, 0.1, 0.8, 0.9], "sha-app", request_id="fmgtest") == (
        "CODE_BUG",
        "PLAN_A",
        0.91,
    )
