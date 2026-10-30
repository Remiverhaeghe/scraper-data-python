# Git

## L'essentiel
- Git suit l'historique d'un projet par instantanés (commits), en local, et se synchronise avec des dépôts distants.
- Trois zones : répertoire de travail, index (staging), historique.
- Une branche est un pointeur mobile vers un commit ; HEAD indique où l'on se trouve.

## Commandes courantes
- git status, git add, git commit -m "message", git log --oneline --graph.
- git switch -c nouvelle-branche, git switch main.
- git pull (récupérer et intégrer), git push (envoyer), git fetch (récupérer sans intégrer).
- git diff (non indexé), git diff --staged (indexé).

## Fusionner
- git merge : crée un commit de fusion si les historiques ont divergé, ou avance rapidement sinon.
- git rebase : rejoue ses commits au-dessus d'une autre branche, pour un historique linéaire.
- Conflit : éditer les zones marquées, git add, puis terminer la fusion ou le rebase.
- Ne pas réécrire (rebase, amend, push --force) des commits déjà partagés.

## Revenir en arrière
- git restore fichier : annuler une modification non indexée.
- git revert commit : crée un commit inverse, sûr sur une branche partagée.
- git reset : déplace la branche (soft, mixed, hard) ; --hard efface les modifications.
- git stash : mettre de côté un travail en cours.
- git reflog : retrouver un commit « perdu ».

## Bonnes pratiques
- Commits petits et cohérents, messages clairs.
- Branches de fonctionnalité et revues de code (pull requests, merge requests).
- .gitignore pour exclure fichiers générés, secrets et environnements.

## Pièges fréquents
- Committer un mot de passe : il reste dans l'historique même supprimé ensuite.
- Faire un reset --hard sans avoir sauvegardé son travail.
- Forcer un push sur une branche partagée.

## En entretien
- Expliquez merge et rebase, et quand utiliser chacun.
- Racontez la résolution d'un conflit.

## Références
- [Livre Pro Git (en français)](https://git-scm.com/book/fr/v2)
- [Documentation Git](https://git-scm.com/docs)
