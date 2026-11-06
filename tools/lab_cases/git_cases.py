"""Cas du bac à sable Git : commandes rejouées sur chaque niveau."""

from job.git_graph import render_graph
from job.git_levels import LEVELS as GIT_LEVELS
from job.git_levels import is_goal_reached
from job.git_sandbox import replay, run_command
from job.git_worktree import describe_worktree

# Commandes Git jouées à la suite sur chaque niveau, bonnes ou fautives
GIT_COMMANDS = (
    "git status",
    "git log",
    "git diff",
    "git branch",
    "modifier notes.txt",
    "modifier réglages.yml",
    "git stash",
    "git stash list",
    "git stash pop",
    "git add notes.txt",
    "git restore --staged notes.txt",
    "git commit",
    "git commit -am 'premier jet'",
    'git commit -m "message \\"cité\\""',
    "git switch -c essai",
    "modifier notes.txt",
    "git commit -a",
    "git switch main",
    "git merge essai",
    "git merge --abort",
    "git rebase essai",
    "git cherry-pick essai",
    "git checkout --ours notes.txt",
    "git reset --soft HEAD~1",
    "git status",
    "git reset --hard HEAD~1",
    "git revert HEAD",
    "git checkout C0",
    "git switch --detach HEAD^",
    "git branch -f essai C1",
    "git branch -d essai",
    "git push",
    "git pull --rebase",
    "git fetch",
    "git bisect",
    "git commit --amend",
    "rm -rf /",
    'git commit -m "non fermé',
    "modifier ../secret",
    "git log --oneline",
    "git merge couleur",
    "git status",
    "git switch main",
    "git checkout --theirs app.py",
    "git add .",
    "git commit",
    "git rebase --continue",
    "git stash pop",
    "git merge --abort",
    "git rebase --abort",
    "git reset --hard HEAD",
    "git stash list",
    "git stash drop",
    "git add absent.txt",
    "git restore absent.txt",
    "modifier notes.txt",
    "git restore notes.txt",
    "modifier notes.txt",
    "git stash",
    "git stash pop stash@{5}",
    "git stash pop dernier",
    "git stash ranger",
    "modifier notes.txt",
    "modifier notes.txt",
    "git commit -am 'autre version'",
    "git stash pop",
    "git restore notes.txt",
    "git add notes.txt",
    "git stash drop stash@{0}",
)


def build_git_case(pLevel, pName, pCommands):
    """Rejoue des commandes sur un niveau Git : message, fichiers, objectif, graphes."""

    vRepository = replay(pLevel.setup)
    vSteps = []

    for vCommand in pCommands:
        try:
            vStep = {"command": vCommand, "message": run_command(vRepository, vCommand)}

        except ValueError as vError:
            vStep = {"command": vCommand, "error": str(vError)}

        vStep["worktree"] = describe_worktree(vRepository)
        vStep["reached"] = is_goal_reached(pLevel, vRepository)
        vSteps.append(vStep)

    rCase = {
        "name": f"{pLevel.id} : {pName}",
        "level": pLevel.id,
        "steps": vSteps,
        "graph": render_graph(vRepository.local_view(), "Votre dépôt"),
        "server": (
            render_graph(vRepository.server_view(), "Serveur", pShowHead=False)
            if vRepository.remote
            else ""
        ),
        "goal": render_graph(
            replay(pLevel.setup + pLevel.solution).local_view(), "Objectif"
        ),
    }

    return rCase


def build_git_cases():
    """Retourne les cas Git : solution et commandes variées sur chaque niveau."""

    rCases = [
        build_git_case(vLevel, vName, vCommands)
        for vLevel in GIT_LEVELS
        for vName, vCommands in (
            ("solution", vLevel.solution),
            ("commandes variées", GIT_COMMANDS),
        )
    ]

    return rCases
