# Linux et scripts shell

## L'essentiel
- Linux est partout : serveurs, conteneurs, passerelles industrielles, systèmes embarqués.
- Tout est fichier ; l'arborescence part de / (etc pour la configuration, var/log pour les journaux, home pour les utilisateurs).
- Le shell (bash) enchaîne des commandes simples avec des tubes et des redirections.

## Commandes essentielles
- Navigation : pwd, ls -l, cd, find, tree.
- Fichiers : cp, mv, rm, mkdir, cat, less, head, tail -f.
- Recherche dans les textes : grep, et traitement avec sed, awk, cut, sort, uniq, wc.
- Processus : ps aux, top ou htop, kill, systemctl status service.
- Disque et mémoire : df -h, du -sh, free -h.
- Réseau : ip a, ss -tulpn, ping, curl.

## Droits
- Propriétaire, groupe, autres ; lecture, écriture, exécution (r w x).
- chmod 640 fichier, chown utilisateur:groupe fichier.
- sudo pour une commande administrateur ; éviter de travailler en root.

## Services et journaux
- systemd : systemctl start, stop, enable, status ; journalctl -u service -f.
- cron ou timers systemd pour planifier une tâche.

## Scripts bash
- Commencer par #!/bin/bash et set -euo pipefail pour s'arrêter sur erreur.
- Variables entre guillemets ("$fichier") pour gérer les espaces.
- Code de retour $? ; 0 signifie succès.
- Boucles for et while, tests avec [ ] ou [[ ]].

## Pièges fréquents
- rm -rf avec une variable vide.
- Oublier les guillemets autour des variables.
- Donner les droits 777 pour « faire marcher ».
- Remplir le disque avec des journaux non tournés (logrotate).

## En entretien
- Expliquez comment trouver ce qui remplit le disque ou ce qui consomme le processeur.
- Montrez un petit script que vous avez écrit et sa gestion d'erreurs.

## Références
- [Manuel de Bash (GNU)](https://www.gnu.org/software/bash/manual/)
- [Linux (Wikipédia)](https://fr.wikipedia.org/wiki/Linux)
- [Documentation Ubuntu Server](https://documentation.ubuntu.com/server/)
