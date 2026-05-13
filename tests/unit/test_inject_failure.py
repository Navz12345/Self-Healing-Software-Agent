import subprocess

import inject_failure


def test_inject_divide_by_zero_writes_bug(monkeypatch, tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(inject_failure.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        inject_failure.subprocess,
        "run",
        lambda *_, **__: subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        inject_failure.requests,
        "get",
        lambda *_, **__: (_ for _ in ()).throw(RuntimeError("expected failure")),
    )

    inject_failure.inject_divide_by_zero()

    assert "amount / 0" in (app_dir / "payments.py").read_text(encoding="utf-8")


def test_inject_ambiguous_writes_random_failure(monkeypatch, tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(inject_failure.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        inject_failure.subprocess,
        "run",
        lambda *_, **__: subprocess.CompletedProcess(args=[], returncode=0),
    )
    monkeypatch.setattr(inject_failure.requests, "get", lambda *_, **__: None)

    inject_failure.inject_ambiguous()

    text = (app_dir / "payments.py").read_text(encoding="utf-8")
    assert "intermittent_failure" in text


def test_inject_infra_crash_uses_container_command(monkeypatch):
    called = []
    monkeypatch.setattr(
        inject_failure, "_run_container_command", lambda command: called.append(command)
    )

    inject_failure.inject_infra_crash()

    assert called == [["docker", "stop", "sha-app"]]
