# Supervision, SCADA et IHM

## L'essentiel
- La supervision montre l'état des installations, remonte les alarmes, permet de commander et historise les données.
- IHM : pupitre au pied de la machine. SCADA : supervision de plusieurs machines, d'un site ou d'un réseau étendu.
- Logiciels courants : WinCC (Siemens), AVEVA (Wonderware), Ignition, PcVue, Panorama.

## Composants d'un SCADA
- Serveurs d'acquisition reliés aux automates (OPC UA, Modbus, drivers constructeur).
- Synoptiques : vues animées des installations.
- Gestion des alarmes : apparition, acquittement, disparition, priorités.
- Historique et courbes de tendance ; rapports de production.
- Postes clients, parfois accès web.

## Alarmes bien conçues
- Une alarme doit demander une action de l'opérateur ; sinon c'est une information.
- Priorités claires, textes compréhensibles, cause probable et action attendue.
- Éviter les avalanches d'alarmes et les alarmes toujours actives (norme ISA-18.2, EEMUA 191).

## Bonnes pratiques d'affichage
- Synoptiques sobres : gris pour le normal, couleur pour l'anormal (ISA-101).
- Mêmes symboles et mêmes couleurs sur toutes les vues.
- Valeurs avec unités, qualité affichée quand la communication est perdue.

## Exploitation et sécurité
- Comptes nominatifs et droits par rôle (opérateur, régleur, administrateur).
- Sauvegardes des projets, gestion des versions.
- Poste dédié, durci, sans navigation Internet ni messagerie.
- Horloges synchronisées pour des historiques cohérents.

## Pièges fréquents
- Prendre une valeur figée pour une mesure réelle (perte de communication).
- Laisser des centaines d'alarmes acquittées sans les traiter.
- Modifier une vue en production sans sauvegarde.

## En entretien
- Décrivez un synoptique que vous avez utilisé ou modifié.
- Expliquez comment vous traitez une alarme et remontez à la cause.

## Références
- [SCADA (Wikipédia)](https://fr.wikipedia.org/wiki/Syst%C3%A8me_de_contr%C3%B4le_et_d%27acquisition_de_donn%C3%A9es)
- [Interface homme-machine (Wikipédia)](https://fr.wikipedia.org/wiki/Interface_homme-machine)
- [OPC Unified Architecture (Wikipédia, en anglais)](https://en.wikipedia.org/wiki/OPC_Unified_Architecture)
