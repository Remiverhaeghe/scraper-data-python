"""Tests du lancement automatique à l'ouverture de session Windows"""

from tools.windows_startup import SCRIPT_NAME, build_script, install, main, remove


def test_script_starts_web_and_scheduler_from_the_project():
    """Vérifie que le fichier se place dans le projet et lance les deux programmes."""

    vScript = build_script(r"D:\projet", r"C:\Users\rémi\Python\python.exe")

    assert vScript.startswith("@echo off\r\n")
    assert 'cd /d "D:\\projet"' in vScript
    assert '"C:\\Users\\rémi\\Python\\python.exe" -m web' in vScript
    assert '"C:\\Users\\rémi\\Python\\python.exe" -m scheduler' in vScript


def test_install_then_remove(tmp_path):
    """Vérifie l'écriture du fichier, lisible par cmd malgré l'accent, puis son retrait."""

    vPath = install(tmp_path, r"D:\projet", r"C:\Users\rémi\python.exe")

    assert vPath == tmp_path / SCRIPT_NAME
    assert "rémi" in vPath.read_text(encoding="oem")
    assert remove(tmp_path)
    assert not vPath.exists()
    assert not remove(tmp_path)


def test_main_uses_the_user_startup_folder(tmp_path, monkeypatch, capsys):
    """Vérifie que la commande écrit dans le dossier Démarrage de APPDATA."""

    monkeypatch.setenv("APPDATA", str(tmp_path))
    vStartup = (
        tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    )
    vStartup.mkdir(parents=True)

    assert main([]) == 0
    assert (vStartup / SCRIPT_NAME).exists()
    assert main(["--remove"]) == 0
    assert "retiré" in capsys.readouterr().out
