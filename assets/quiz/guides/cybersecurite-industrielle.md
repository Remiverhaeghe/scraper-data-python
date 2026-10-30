# Cybersécurité industrielle

## L'essentiel
- En OT, une attaque a des conséquences physiques : arrêt, casse, danger pour les personnes, pollution.
- La disponibilité et l'intégrité des commandes passent avant la confidentialité.
- On ne protège pas ce qu'on ne connaît pas : l'inventaire des équipements, logiciels, comptes et flux vient en premier.
- La cybersécurité OT réunit production, maintenance, informatique et prestataires.

## IEC 62443 en bref
- Rôles : exploitant (asset owner), intégrateur, fournisseur de produits.
- Zones : groupes d'actifs aux mêmes exigences de sécurité. Conduits : passages contrôlés entre zones.
- Niveaux de sécurité : SL 1 (erreur ou violation occasionnelle) à SL 4 (attaquant organisé aux moyens étendus). SL-T visé, SL-A atteint, SL-C possible avec les composants.
- 7 exigences fondamentales : identification et authentification, contrôle d'usage, intégrité, confidentialité, flux restreints, réponse aux événements, disponibilité.
- 3-2 : analyse de risques et découpage en zones ; 3-3 : exigences du système ; 4-1 : développement sécurisé ; 4-2 : exigences des composants.

## Architecture
- Modèle de Purdue : niveaux 0-1 (terrain, automates), 2 (supervision), 3 (MES, historian), DMZ industrielle, puis IT.
- Pas de flux direct entre IT et OT : tout s'arrête dans la DMZ (serveur relais, historique répliqué, dépôt de mises à jour).
- Pare-feu : tout refuser par défaut, autoriser seulement les flux de la matrice des flux. Les VLAN séparent, le pare-feu filtre.
- Diode de données pour les systèmes les plus critiques : les données sortent, rien ne rentre.
- Défense en profondeur : organisation, accès physique, réseau, postes, automates.

## Les bons réflexes au quotidien
- Clés USB : toujours par la station blanche ; une clé trouvée va au service informatique.
- Comptes nominatifs, moindre privilège, mots de passe par défaut changés à l'installation.
- Accès distant : bastion, authentification à plusieurs facteurs, ouverture limitée à l'intervention, session enregistrée.
- Portables des prestataires contrôlés, prises réseau inutilisées désactivées, armoires fermées.
- Programmes d'automates versionnés et comparés à la référence ; sélecteur en RUN quand l'automate le permet.

## Vulnérabilités et correctifs
- Les CVE identifient les failles connues ; le score CVSS aide à prioriser.
- Un correctif se teste puis s'applique lors d'un arrêt, avec retour arrière prévu.
- En attendant : mesures compensatoires (filtrage, désactivation du service, surveillance).
- Les systèmes obsolètes s'isolent, se durcissent et se remplacent selon un plan budgété.

## Sauvegardes et incidents
- Règle 3-2-1 : trois copies, deux supports, une hors site ; idéalement une copie immuable.
- Sauvegarder aussi programmes, projets de supervision, paramètres de variateurs, configurations et licences.
- Tester la restauration régulièrement.
- Réponse à incident : préparer, détecter, contenir, éradiquer et restaurer, tirer les leçons. En OT, l'isolement se décide avec la production.
- PCA : continuer en mode dégradé ; PRA : reconstruire.

## Attaques à connaître
- Stuxnet (2010) : sabotage de centrifugeuses par modification de programmes d'automates, valeurs normales affichées aux opérateurs.
- Industroyer (2016) : coupure d'une partie du réseau électrique ukrainien.
- Triton (2017) : attaque d'automates de sécurité d'un site pétrochimique.
- NotPetya (2017) : destruction de données à grande échelle, usines arrêtées dans le monde.

## Cadre réglementaire en France
- ANSSI : classes de cybersécurité 1 à 3 selon la gravité des conséquences, guides de mesures détaillées.
- NIS2 : obligations de gestion des risques et de notification pour de nombreux secteurs industriels.
- EBIOS Risk Manager : méthode d'analyse de risques par scénarios.

## Pièges fréquents
- Croire qu'un réseau sans Internet est à l'abri : clés USB, portables et accès distants le relient au monde.
- Installer un antivirus ou un correctif sans test sur un poste de supervision.
- Confondre safety (défaillances) et security (malveillance) : une attaque peut neutraliser une fonction de sécurité.
- Laisser un accès distant ouvert en permanence pour gagner du temps.

## En entretien
- Montrez vos réflexes : station blanche, traçabilité des modifications, signalement d'une anomalie.
- Expliquez la différence IT et OT avec un exemple de votre expérience.
- Citez l'IEC 62443 (zones et conduits) et les guides de l'ANSSI.

## Références
- [La cybersécurité des systèmes industriels (ANSSI)](https://cyber.gouv.fr/publications/la-cybersecurite-des-systemes-industriels)
- [IEC 62443 (Wikipédia)](https://fr.wikipedia.org/wiki/IEC_62443)
- [Méthode EBIOS Risk Manager (ANSSI)](https://cyber.gouv.fr/la-methode-ebios-risk-manager)
- [Directive NIS 2 (Wikipédia)](https://fr.wikipedia.org/wiki/Directive_NIS_2)
- [Stuxnet (Wikipédia)](https://fr.wikipedia.org/wiki/Stuxnet)
- [Défense en profondeur (Wikipédia)](https://fr.wikipedia.org/wiki/D%C3%A9fense_en_profondeur)
