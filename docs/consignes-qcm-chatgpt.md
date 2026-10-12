# Génération des questions de révision avec ChatGPT

Les questions supplémentaires sont créées avec son propre compte ChatGPT, puis importées
dans la page Révision. La demande est produite par l'application à partir de deux fichiers :

| Fichier | Contenu |
|---|---|
| `assets/quiz_generation/catalog.json` | Catalogue des thèmes, rangés par domaine puis sous-domaine |
| `assets/quiz_generation/prompt.txt` | Texte de la demande et ses règles, avec des variables `$…` |

## Utilisation

1. Page Révision, carte « Ajouter des questions » : choisir un thème (catalogue, thème
   existant ou nouveau), le niveau (« Tous les niveaux » : 25 % débutant, 40 %
   intermédiaire, 20 % confirmé, 15 % expert) et le nombre de questions (100 par défaut).
2. « Générer avec ChatGPT » copie la demande et ouvre ChatGPT ; la coller.
3. Importer l'archive .zip obtenue, ou coller le JSON.
4. Lire le bilan : en orange, le lot ne respecte pas la demande (bonne réponse trop souvent
   la plus longue ou à la même position, explications trop courtes). « Voir le détail »
   donne les mesures de chaque thème. Un lot douteux se supprime en signalant ses questions
   ou se redemande à ChatGPT.

Chaque demande porte le numéro du lot suivant du thème, calculé d'après les questions déjà
importées : les identifiants `<thème>-l<lot>-<numéro>` ne se chevauchent jamais.

Les thèmes `python`, `java`, `spring`, `javascript`, `sql`, `git` et `docker` portent
l'identifiant des thèmes livrés dans `assets/quiz` : leurs questions s'y ajoutent.

## Cadrer ChatGPT

ChatGPT garde en mémoire des consignes d'une conversation à l'autre et peut les préférer à
la demande (par exemple un autre nombre de questions par thème). À envoyer une fois :

```text
Oublie les consignes de nombre et de répartition de questions que tu as mémorisées pour ce projet. Pour chaque lot, seule la demande que je colle fait foi : thème, numéro de lot, nombre de questions et répartition par niveau. Ne livre jamais plus de questions que demandé. Si ta réponse est coupée, j'écrirai « continue » et tu reprendras à la question suivante, avec la même numérotation.
```

Un lot de 100 questions détaillées remplit déjà une réponse : au-delà, ChatGPT coupe ou
répète des notions. Pour atteindre 250 questions sur un thème, demander plusieurs lots.

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
