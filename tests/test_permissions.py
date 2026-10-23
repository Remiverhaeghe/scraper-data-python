"""Tests du contrôle des moindres privilèges"""

import utils.permissions as permissions
from job.health import check_permissions


def test_problems_are_reported_on_linux(tmp_path, monkeypatch):
    """Vérifie root, un .env lisible par tous et data/ ouvert, puis tout corrigé."""

    vModes = {"env": 0o644, "data": 0o777}
    monkeypatch.setattr(permissions, "is_posix", lambda: True)
    monkeypatch.setattr(permissions, "get_user_id", lambda: 0)
    monkeypatch.setattr(
        permissions,
        "get_mode",
        lambda pPath: vModes["env" if pPath.name in ("env", ".env") else "data"],
    )

    vProblems = permissions.find_permission_problems(
        tmp_path / "env", tmp_path / "data"
    )

    assert [vProblem.split(" ")[0] for vProblem in vProblems] == [
        "lancée",
        ".env",
        "data/",
    ]

    vModes.update(env=0o600, data=0o750)
    monkeypatch.setattr(permissions, "get_user_id", lambda: 1000)

    assert (
        permissions.find_permission_problems(tmp_path / "env", tmp_path / "data") == []
    )
    assert check_permissions() == ("Compte dédié, .env et data/ protégés", "success")


def test_windows_is_not_checked(monkeypatch, caplog):
    """Vérifie qu'aucun contrôle n'est fait sous Windows, ni avertissement."""

    monkeypatch.setattr(permissions, "is_posix", lambda: False)

    assert permissions.find_permission_problems() is None
    assert check_permissions() == ("Non vérifiés sous Windows", "muted")

    permissions.warn_permission_problems()

    assert "Droits d'exécution" not in caplog.text


def test_startup_warning_lists_each_problem(monkeypatch, caplog):
    """Vérifie un avertissement par écart au démarrage."""

    monkeypatch.setattr(permissions, "find_permission_problems", lambda: ["un", "deux"])

    permissions.warn_permission_problems()

    assert caplog.text.count("Droits d'exécution") == 2


def test_mode_and_identity_helpers(tmp_path):
    """Vérifie la lecture des droits d'un fichier et d'un chemin absent."""

    vFile = tmp_path / "fichier"
    vFile.write_text("x", encoding="utf-8")

    assert permissions.get_mode(vFile) is not None
    assert permissions.get_mode(tmp_path / "absent") is None
    assert permissions.get_user_id() is None or permissions.get_user_id() >= 0
