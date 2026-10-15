"""Tests du dépôt simulé du bac à sable Git et de son graphe"""

import pytest

from job.git_graph import FADED_OPACITY, compute_layout, render_graph
from job.git_sandbox import Repository, replay, run_command


def run_all(pRepository, *pCommands):
    """Joue des commandes et retourne le message de la dernière."""

    rMessage = ""

    for vCommand in pCommands:
        rMessage = run_command(pRepository, vCommand)

    return rMessage


def test_commits_and_branches_move_with_head():
    """Vérifie commit, création de branche, changement de branche et suppression."""

    vRepository = Repository()

    assert run_command(vRepository, 'git commit -m "premier essai"') == (
        "Commit C1 enregistré"
    )
    assert run_all(vRepository, "git branch essai", "git branch") == (
        "Branches : essai, main"
    )

    run_all(vRepository, "git switch essai", "git commit")

    assert vRepository.branches == {"main": "C1", "essai": "C2"}
    assert run_command(vRepository, "git status") == "Sur la branche essai, commit C2"

    with pytest.raises(ValueError, match="HEAD s'y trouve"):
        run_command(vRepository, "git branch -d essai")

    run_all(vRepository, "git checkout main", "git branch -d essai")

    assert vRepository.branches == {"main": "C1"}


def test_switch_create_detach_and_force():
    """Vérifie switch -c, checkout -b, HEAD détaché et branch -f."""

    vRepository = replay(("git commit", "git commit"))

    assert run_command(vRepository, "git switch -c a C1") == "Sur la branche a"
    assert vRepository.branches["a"] == "C1"
    assert run_command(vRepository, "git checkout -b b") == "Sur la branche b"
    assert run_command(vRepository, "git checkout main^") == "HEAD détaché sur C1"
    assert run_command(vRepository, "git status") == "HEAD détaché sur C1"
    assert run_command(vRepository, "git switch --detach main") == (
        "HEAD détaché sur C2"
    )

    run_command(vRepository, "git commit")

    assert vRepository.head == "C3" and vRepository.branches["main"] == "C2"
    assert run_command(vRepository, "git branch -f a HEAD") == (
        "Branche a déplacée sur C3"
    )

    run_command(vRepository, "git switch a")

    with pytest.raises(ValueError, match="HEAD s'y trouve"):
        run_command(vRepository, "git branch -f a C0")

    with pytest.raises(ValueError, match="git switch -c pour la créer"):
        run_command(vRepository, "git switch inconnue")


def test_merge_fast_forward_and_merge_commit():
    """Vérifie l'avance rapide, le « déjà à jour » et le commit de fusion."""

    vRepository = replay(("git switch -c f", "git commit", "git switch main"))

    assert run_command(vRepository, "git merge f") == "Avance rapide jusqu'à C1"
    assert run_command(vRepository, "git merge f") == "Déjà à jour"

    run_all(vRepository, "git commit", "git switch f", "git commit")

    assert run_command(vRepository, "git merge main") == "Commit de fusion C4 créé"
    assert vRepository.commits["C4"].parents == ("C3", "C2")
    assert vRepository.resolve("HEAD^2") == "C2"


def test_rebase_copies_own_commits_only_once():
    """Vérifie le rebase : copies, fusion ignorée, commit déjà recopié ignoré."""

    vRepository = replay(
        (
            "git switch -c f",
            "git commit",
            "git commit",
            "git switch main",
            "git commit",
            "git cherry-pick C1",
            "git switch f",
        )
    )

    assert run_command(vRepository, "git rebase main") == (
        "1 commit(s) rejoué(s) sur C1'"
    )
    assert vRepository.branches["f"] == "C2'"
    assert vRepository.commits["C2'"].parents == ("C1'",)
    assert run_command(vRepository, "git rebase main") == "Déjà à jour"

    run_command(vRepository, "git switch main")

    assert run_command(vRepository, "git rebase f") == "Avance rapide jusqu'à C2'"


def test_reset_revert_cherry_pick_and_amend():
    """Vérifie reset, revert, cherry-pick et commit --amend."""

    vRepository = replay(("git commit", "git commit", "git commit"))

    assert run_command(vRepository, "git reset --hard HEAD~2") == "HEAD ramené sur C1"
    assert vRepository.reachable() == {"C0", "C1"}
    assert run_command(vRepository, "git revert C1") == ("Commit C4 : annulation de C1")
    assert run_command(vRepository, "git cherry-pick C2 C3") == (
        "Commit(s) recopié(s) : C2', C3'"
    )
    assert run_command(vRepository, "git commit --amend") == (
        "Commit C3' remplacé par C3''"
    )

    with pytest.raises(ValueError, match="déjà présent"):
        run_command(vRepository, "git cherry-pick C1")

    for vCommand, vMessage in (
        ("git reset --keep C1", "Option non prise en charge"),
        ("git revert C0", "premier commit"),
    ):
        with pytest.raises(ValueError, match=vMessage):
            run_command(vRepository, vCommand)

    with pytest.raises(ValueError, match="premier commit"):
        run_command(replay(()), "git commit --amend")


@pytest.mark.parametrize(
    ("pCommand", "pMessage"),
    [
        ("", "Saisissez une commande"),
        ("ls", "commencent par git"),
        ("git", "commencent par git"),
        ("git push", "non prise en charge"),
        ('git commit -m "oubli', "Guillemet"),
        ("git commit " + "x" * 120, "trop longue"),
        ("git branch C5", "Nom de branche invalide"),
        ("git branch HEAD", "Nom de branche invalide"),
        ("git branch main", "existe déjà"),
        ("git branch -m a b", "Option non prise en charge"),
        ("git branch -d absente", "n'existe pas"),
        ("git checkout absente", "Référence inconnue"),
        ("git checkout main~5", "remonte avant"),
        ("git checkout main^2", "ce parent n'existe pas"),
        ("git checkout main@", "Référence invalide"),
        ("git switch -x main", "Option non prise en charge"),
        ("git merge", "Usage : git merge"),
        ("git status court", "Usage : git status"),
    ],
)
def test_invalid_commands_are_refused(pCommand, pMessage):
    """Vérifie le refus explicite des commandes invalides."""

    with pytest.raises(ValueError, match=pMessage):
        run_command(replay(("git commit",)), pCommand)


def test_failed_command_leaves_repository_unchanged():
    """Vérifie qu'une commande en échec n'applique rien, même à moitié."""

    vRepository = replay(("git switch -c f", "git commit", "git switch main"))
    vCommits = dict(vRepository.commits)

    with pytest.raises(ValueError, match="Référence inconnue"):
        run_command(vRepository, "git cherry-pick C1 C9")

    assert vRepository.commits == vCommits
    assert vRepository.branches == {"main": "C0", "f": "C1"}
    assert run_command(vRepository, "git commit") == "Commit C2 enregistré"


def test_graph_places_branches_and_fades_lost_commits():
    """Vérifie la disposition, les étiquettes et l'estompage du graphe."""

    vRepository = replay(
        ("git switch -c f", "git commit", "git switch main", "git commit")
    )

    assert compute_layout(vRepository) == {"C0": (0, 0), "C1": (1, 0), "C2": (1, 1)}

    run_command(vRepository, "git reset C0")
    vSvg = render_graph(vRepository, "Dépôt <test>")

    assert vSvg.startswith("<svg") and "<title>Dépôt &lt;test&gt;</title>" in vSvg
    assert ">main*</text>" in vSvg and ">f</text>" in vSvg
    assert vSvg.count(f'opacity="{FADED_OPACITY}"') == 2

    run_command(vRepository, "git checkout C1")

    assert ">f, HEAD</text>" in render_graph(vRepository, "Dépôt")
