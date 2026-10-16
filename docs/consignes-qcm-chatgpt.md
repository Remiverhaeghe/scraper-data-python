# Génération des questions de révision avec ChatGPT

Les questions supplémentaires sont créées avec son propre compte ChatGPT, puis importées
dans la page Révision. Les demandes sont produites par l'application à partir de ces fichiers :

| Fichier | Contenu |
|---|---|
| `assets/quiz_generation/catalog.json` | Catalogue des thèmes, rangés par domaine puis sous-domaine, avec les mots des offres (`skills`) |
| `assets/quiz_generation/prompt.txt` | Texte de la demande et ses règles, avec des variables `$…` |
| `assets/quiz_generation/correction.txt` | Demande de correction d'un lot signalé, variable `$themes` |

## Utilisation

1. Page Révision, la carte « À compléter en priorité » propose les thèmes les plus demandés
   dans vos offres et encore loin de 100 questions ; « Préparer la demande » remplit tout.
   Sinon, carte « Ajouter des questions » : choisir un thème (catalogue, thème
   existant ou nouveau), le niveau (« Tous les niveaux » : 25 % débutant, 40 %
   intermédiaire, 20 % confirmé, 15 % expert) et le nombre de questions (100 par défaut).
2. « Générer avec ChatGPT » copie la demande et ouvre ChatGPT ; la coller.
3. Importer l'archive .zip obtenue, ou coller le JSON. Les archives contrôlées déposées
   dans `data/packs/` sous le nom `<thème>-l<lot>-valide.zip` s'importent toutes avec
   « Importer les lots validés » ; une archive déjà importée ne change rien.
4. Lire le bilan : en orange, le lot ne respecte pas la demande (bonne réponse trop souvent
   la plus longue ou à la même position, explications trop courtes). « Voir le détail »
   donne les mesures de chaque thème.
5. Lot en orange : « Faire corriger par ChatGPT » copie une demande qui cite les alertes
   et les questions concernées. Le lot corrigé se réimporte normalement : chaque question
   importée revenant avec le même identifiant est remplacée. Ses réponses restent
   rattachées, un schéma absent de la correction est gardé et un signalement est levé.
   Une question livrée avec l'application ou d'un autre thème n'est jamais remplacée.

Les archives à garder ou à retravailler se rangent dans `data/packs/`, ignoré par Git. Une
archive contrôlée prend le suffixe `-valide` (`grafcet-l1-valide.zip`), une archive de
ChatGPT remplacée par sa version corrigée le suffixe `-chatgpt-ecarte`.

Chaque demande porte le numéro du lot suivant du thème, calculé d'après les questions déjà
importées : les identifiants `<thème>-l<lot>-<numéro>` ne se chevauchent jamais.

Les thèmes `python`, `java`, `spring`, `javascript`, `sql`, `git` et `docker` portent
l'identifiant des thèmes livrés dans `assets/quiz` : leurs questions s'y ajoutent.

## Ordre de travail conseillé

Le numéro de lot appartient à chaque thème : le lot 1 de `grafcet` et le lot 1 de
`hydraulique` sont deux demandes distinctes. Les séries ci-dessous regroupent seulement les
thèmes à traiter ensuite, un thème par demande.

| Série | Thèmes |
|---|---|
| 1. Automatisme | `automates-programmables`, `grafcet`, `capteurs-actionneurs`, `regulation`, `supervision-scada`, `reseaux-industriels`, `securite-machines`, `vision-industrielle`, `robotique`, `iot-industriel` |
| 2. Électricité et énergie | `electricite`, `schemas-electriques`, `habilitation-electrique`, `distribution-electrique`, `moteurs-variateurs`, `electronique`, `energie`, `energies-renouvelables`, `installations-electriques-batiment` |
| 3. Maintenance et qualité | `maintenance-industrielle`, `fiabilite`, `metrologie`, `securite-industrielle`, `levage-manutention`, `qualite`, `lean`, `maintenance-conditionnelle` |
| 4. Mécanique et fluides | `mecanique`, `lecture-plans`, `hydraulique`, `pneumatique`, `usinage`, `soudage`, `genie-climatique`, `automobile`, `transmissions-mecaniques` |
| 5. Diagnostic et exploitation | `linux-systeme`, `windows-server`, `reseaux-fondamentaux`, `reseaux-diagnostic`, `reseau-prod`, `wifi`, `pare-feu-vpn`, `observabilite`, `sql-diagnostic`, `telephonie-ip`, `serveurs-web`, `sauvegarde-pra` |
| 6. DevOps et cloud | `docker`, `ci-cd`, `kubernetes`, `cloud`, `infrastructure-as-code`, `virtualisation` |
| 7. Développement | `python`, `java`, `spring`, `javascript`, `typescript`, `csharp-dotnet`, `web-html-css`, `react-frontend`, `api-rest`, `architecture-logicielle`, `microservices`, `algorithmique`, `performance`, `kotlin`, `php`, `golang`, `android`, `c-cpp-embarque` |
| 8. Données | `sql`, `bases-de-donnees`, `analyse-donnees`, `data-engineering`, `bi-reporting`, `ia-machine-learning`, `hibernate-jpa` |
| 9. Sécurité | `securite-applicative`, `identite-acces`, `cryptographie`, `securite-systemes`, `rgpd`, `cybersecurite-industrielle` |
| 10. Outils et méthodes | `git`, `tests-logiciels`, `agile`, `itil-support` |

## Cadrer ChatGPT

ChatGPT garde en mémoire des consignes d'une conversation à l'autre et peut les préférer à
la demande (par exemple un autre nombre de questions par thème). À envoyer une fois :

```text
Oublie les consignes de nombre et de répartition de questions que tu as mémorisées pour ce projet. Pour chaque lot, seule la demande que je colle fait foi : thème, numéro de lot, nombre de questions et répartition par niveau. Ne livre jamais plus de questions que demandé. Si ta réponse est coupée, j'écrirai « continue » et tu reprendras à la question suivante, avec la même numérotation.
```

Un lot de 100 questions détaillées remplit déjà une réponse : au-delà, ChatGPT coupe ou
répète des notions. Pour atteindre 250 questions sur un thème, demander plusieurs lots.

## Contrôler une archive ou écrire un lot

Une archive se contrôle sans toucher à la base : elle est importée dans une copie, puis
mesurée. Le code de retour vaut 1 si le lot n'est pas conforme.

```text
python -m tools.quiz_lot check data/packs/<archive>.zip
```

Un lot peut aussi s'écrire directement dans `tools/quiz_lots/<thème>/` : des fichiers
`partN.txt` au format compact décrit en tête de `tools/quiz_lot.py`, et un `lot.json`
(numéro de lot, graine de tirage des positions, compétences, schémas). La commande suivante
écrit `data/packs/<thème>-l<lot>-valide.zip` et affiche son contrôle :

```text
python -m tools.quiz_lot build <thème>
```

Un lot écrit peut mêler aux QCM des questions interactives (calcul, remise en ordre,
association, code à compléter, zone à désigner sur un schéma, schéma à construire), dont les
champs sont décrits au même endroit. Les composants d'un schéma à construire viennent de
`job/schema_library.py` : chacun n'apparaît qu'une fois par question. Les zones se mesurent dans les coordonnées du SVG ; une question « zone »
montre toujours son schéma avec l'énoncé. Dans
`lot.json`, un schéma se rattache à des questions par leur numéro ; il s'affiche avec la
correction, sauf avec `"on_question": true`, pour un symbole ou un schéma qu'il faut lire
pour répondre (planche de symboles numérotés, par exemple). Les schémas dessinés à la main
se rangent dans `tools/quiz_lots/<thème>/schemas/`, sans commentaire qui trahirait la
réponse.

Une question peut citer une ou deux références, ligne `R: Titre | https://…`. Avant de les
garder, on vérifie que les pages existent (accès réseau, à la demande seulement) ; le code de
retour vaut 1 si une page est retirée :

```text
python -m tools.quiz_lot links <thème ou archive.zip>
```

Les tests reconstruisent et contrôlent chaque lot de `tools/quiz_lots` : un lot modifié qui
ne respecte plus les règles fait échouer la CI.

Le contrôle mesure chaque lot en entier, même livré en plusieurs fichiers ou archives : les
questions déjà importées du même lot comptent avec les nouvelles.

## Faire évoluer le catalogue et la demande

- Ajouter un thème dans `catalog.json` sous son domaine et son sous-domaine, avec un
  identifiant en minuscules, chiffres et tirets (3 caractères au moins). Ne jamais renommer
  un identifiant déjà importé : ses questions et réponses y sont rattachées.
- Un nouveau domaine ou sous-domaine doit d'abord exister dans `DOMAIN_ORDER` et
  `DOMAIN_ICONS` (`job/quiz_domains.py`), sinon l'import l'ignore et classe le thème par
  mots-clés.
- Les règles se modifient dans `prompt.txt`. Variables disponibles : `$theme`, `$key`,
  `$lot`, `$count`, `$levels`, `$perimeter`, `$manifest`, `$example`, `$level_values`,
  `$domain_rule`. Un `$` littéral s'écrit `$$`.
- Les seuils du contrôle des lots sont dans `job/quiz_generation.py`
  (`MAX_LONGEST_SHARE`, `MAX_POSITION_SHARE`, `MIN_EXPLANATION_LENGTH`…).

`tests/job/test_quiz_generation.py` vérifie le catalogue (identifiants uniques, classement
connu) et que la demande ne laisse aucune variable non remplie.
