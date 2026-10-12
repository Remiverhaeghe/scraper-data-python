# Génération des questions de révision avec ChatGPT

Consignes à donner à ChatGPT pour créer des lots de questions QCM, importés ensuite depuis
la page Révision (« Ajouter des questions », fichier .zip ou .json).

## Utilisation

1. Copier la demande ci-dessous dans ChatGPT.
2. Modifier les deux premières lignes : numéro de lot et thèmes à traiter (1 ou 2 thèmes).
3. Importer l'archive obtenue dans la page Révision.
4. Pour compléter un thème déjà traité, reprendre le même thème avec le numéro de lot suivant :
   les identifiants `<thème>-l<lot>-<numéro>` ne se chevauchent pas.

Si la réponse de ChatGPT est coupée, lui demander de continuer à partir de la dernière
question livrée, avec la même numérotation.

Les thèmes `python`, `java`, `spring`, `javascript`, `sql`, `git` et `docker` portent
l'identifiant des thèmes livrés dans `assets/quiz` : leurs questions s'y ajoutent.

## Faire évoluer le catalogue

- Un nouveau thème s'ajoute au catalogue avec un identifiant en minuscules, chiffres et
  tirets ; ne jamais renommer un identifiant déjà importé, ses réponses y sont rattachées.
- Un nouveau domaine ou sous-domaine doit d'abord exister dans `DOMAIN_ORDER` et
  `DOMAIN_ICONS` (`job/quiz_domains.py`) : sinon l'import l'ignore et classe le thème par
  mots-clés. Mettre à jour la règle 2 de la demande en même temps.

## Demande à copier

```text
Tu es formateur technique et recruteur. Crée un lot de questions QCM pour préparer des entretiens techniques, en français.

Numéro de lot : 1
Thèmes à traiter dans ce lot : automates-programmables

Ne traite que les thèmes demandés ci-dessus. Le catalogue ci-dessous sert à respecter les identifiants, libellés, domaines et sous-domaines, et à ne pas empiéter sur un autre thème.

CATALOGUE DES THÈMES (identifiant : libellé)
Informatique / Développement
- python : Python
- java : Java
- spring : Spring
- csharp-dotnet : C# et .NET
- javascript : JavaScript
- typescript : TypeScript
- web-html-css : HTML, CSS et accessibilité
- react-frontend : Frameworks frontend (React, Angular, Vue)
- api-rest : API REST et HTTP
- architecture-logicielle : Conception, SOLID et design patterns
- microservices : Microservices et messagerie (Kafka, RabbitMQ)
- algorithmique : Algorithmique et structures de données
- performance : Performance et optimisation
Informatique / Données
- sql : SQL
- sql-diagnostic : SQL et diagnostic de performance
- bases-de-donnees : Modélisation et bases NoSQL
- analyse-donnees : Analyse de données avec Python (Pandas)
- data-engineering : Ingénierie des données et ETL (Spark, Airflow)
- bi-reporting : BI et reporting (Power BI)
- ia-machine-learning : IA et machine learning
Informatique / Exploitation et DevOps
- linux-systeme : Linux et scripts shell
- windows-server : Windows Server et PowerShell
- virtualisation : Virtualisation (VMware, Hyper-V)
- docker : Docker
- ci-cd : Intégration et déploiement continus
- kubernetes : Kubernetes, Pods, images et sécurité
- cloud : Cloud et infrastructure (AWS, Azure)
- infrastructure-as-code : Infrastructure as code (Terraform, Ansible)
- observabilite : Supervision, logs et métriques
Informatique / Outils et méthodes
- git : Git
- tests-logiciels : Tests et qualité du code
- agile : Méthodes agiles et gestion de projet
- itil-support : Support informatique et ITIL
Réseau et sécurité / Réseau
- reseaux-fondamentaux : Modèle OSI, TCP/IP et adressage
- reseaux-diagnostic : Réseaux et diagnostic
- reseau-prod : Réseau en production
- wifi : Wi-Fi et réseaux sans fil
- pare-feu-vpn : Pare-feu et VPN
Réseau et sécurité / Sécurité et identité
- securite-applicative : Sécurité applicative (OWASP)
- identite-acces : Identité et accès (Active Directory, OAuth 2, OpenID Connect)
- cryptographie : Chiffrement, certificats et PKI
- securite-systemes : Durcissement des systèmes et réponse aux incidents
- rgpd : RGPD et protection des données
- cybersecurite-industrielle : Cybersécurité industrielle (IEC 62443)
Industrie / Maintenance
- maintenance-industrielle : Maintenance industrielle
- fiabilite : Fiabilité et méthodes (AMDEC, MTBF, GMAO)
- metrologie : Métrologie et instrumentation
- securite-industrielle : Sécurité industrielle et prévention
- levage-manutention : Levage et manutention
- qualite : Qualité et résolution de problèmes (8D, Ishikawa, ISO 9001)
- lean : Lean manufacturing et amélioration continue (5S, SMED, TRS)
Industrie / Électricité et énergie
- electricite : Électricité
- schemas-electriques : Lecture de schémas électriques
- electronique : Électronique
- habilitation-electrique : Habilitation électrique (NF C 18-510)
- distribution-electrique : Distribution électrique et protections (régimes de neutre)
- moteurs-variateurs : Moteurs électriques et variateurs
- energie : Énergie et efficacité énergétique
- energies-renouvelables : Énergies renouvelables (photovoltaïque, éolien)
Industrie / Mécanique et fluides
- mecanique : Mécanique
- lecture-plans : Dessin technique, cotation et tolérances
- usinage : Usinage et commande numérique
- soudage : Soudage et chaudronnerie
- hydraulique : Hydraulique industrielle
- pneumatique : Pneumatique
- genie-climatique : Froid et génie climatique (CVC)
- automobile : Mécanique automobile
Industrie / Automatisme
- automates-programmables : Automates programmables (Siemens TIA Portal, Schneider)
- grafcet : Grafcet et logique séquentielle
- capteurs-actionneurs : Capteurs et actionneurs
- regulation : Régulation et boucles PID
- supervision-scada : Supervision, SCADA et IHM
- reseaux-industriels : Réseaux industriels (Profinet, Modbus, OPC UA)
- securite-machines : Sécurité des machines (ISO 13849, directive Machines)
- vision-industrielle : Vision industrielle
- robotique : Robotique industrielle

Garde exactement ces identifiants, libellés, domaines et sous-domaines : les questions s'ajouteront à mes thèmes existants. Ne crée pas d'autre thème.

LIVRAISON
Une archive .zip avec :
- manifest.json
- questions/<id-du-theme>.json (un fichier par thème du lot)
- assets/schemas/<nom>.svg (facultatif)
- guides/<id-du-theme>.md (facultatif : méthode pratique en Markdown, titres, listes, liens https)
Si tu ne peux pas créer d'archive, donne le contenu de chaque fichier questions/<id>.json, l'un après l'autre.

manifest.json (un élément par thème du lot) :
{
  "themes": [
    {"id": "<id-du-theme>", "file": "questions/<id-du-theme>.json"}
  ]
}

questions/<id-du-theme>.json :
{
  "theme": "Libellé du thème",
  "domain": "Industrie",
  "subdomain": "Automatisme",
  "skills": ["automate Siemens", "TIA Portal", "Grafcet"],
  "questions": [
    {
      "id": "<id-du-theme>-l<numéro de lot>-001",
      "level": "intermédiaire",
      "type": "qcm",
      "question": "Énoncé de la question ?",
      "code": "facultatif : extrait de code, de configuration ou de programme automate",
      "choices": ["…", "…", "…", "…"],
      "answer": 2,
      "expectedAnswer": "texte exact de choices[answer]",
      "explanation": "…",
      "tags": ["…"],
      "visual": {"type": "svg", "path": "../assets/schemas/<nom>.svg", "alt": "Description du schéma"},
      "references": [{"title": "Titre exact de la page officielle", "url": "https://…"}]
    }
  ]
}

RÈGLES STRICTES
1. 100 questions par thème du lot : 25 débutant, 40 intermédiaire, 20 confirmé, 15 expert. Valeurs exactes : "débutant", "intermédiaire", "confirmé", "expert".
2. "domain" et "subdomain" : ceux du catalogue pour chaque thème, pris dans cette liste :
   Informatique : Développement, Données, Exploitation et DevOps, Outils et méthodes
   Réseau et sécurité : Réseau, Sécurité et identité
   Industrie : Maintenance, Électricité et énergie, Mécanique et fluides, Automatisme
3. Identifiants de question : "<id-du-theme>-l<numéro de lot>-001", "-002"… (ex. "grafcet-l1-001"), uniques, en minuscules, chiffres et tirets.
4. Exactement 4 choix, une seule bonne réponse, vérifiée. "answer" est l'indice du bon choix à partir de 0 ; répartis-le équitablement entre 0, 1, 2 et 3.
5. "expectedAnswer" recopie exactement choices[answer].
6. Les 4 choix ont une longueur comparable (écart de 20 % au plus) : la bonne réponse ne doit jamais se deviner parce qu'elle est la plus longue ou la plus précise. Les mauvaises réponses sont plausibles, des erreurs que ferait vraiment un candidat ; jamais de réponse absurde ou hors sujet.
7. Environ un tiers des questions est concret :
   - informatique et réseau : un extrait de code, de configuration ou de commande dans "code" (5 à 15 lignes au plus) : « que fait ce code ? », « quelle est la sortie ? », « où est l'erreur ? » ;
   - industrie : un petit calcul avec ses valeurs (loi d'Ohm, puissance, pression × surface, couple, rapport de transmission, réglage PID), la lecture d'un schéma, d'une plaque signalétique ou d'un relevé de mesure, ou un extrait de programme automate en texte structuré IEC 61131-3 dans "code".
   Les autres questions : notions, scénarios de terrain, diagnostic de panne ou d'incident, bonnes pratiques, normes.
8. "explanation" : 3 à 5 phrases qui font comprendre la notion. Dis pourquoi la bonne réponse est juste, puis pourquoi chacun des autres choix est faux. Pour un calcul, détaille le calcul.
9. Sécurité : pour l'électricité, l'hydraulique, la pneumatique, la mécanique, le soudage, le levage, l'automatisme et la robotique, les questions rappellent les bonnes pratiques (consignation, habilitation, EPI, arrêt d'urgence, purge de l'énergie). Elles ne présentent jamais un geste dangereux comme correct.
10. "references" : 1 ou 2 pages qui contiennent la réponse, sur un site officiel : documentation de l'éditeur ou du constructeur, organisme public (INRS, CNIL, ANSSI, Légifrance, AFNOR pour le résumé d'une norme), norme ou RFC, MDN pour le web, OWASP pour la sécurité applicative. Lien https direct vers la page exacte, jamais de raccourcisseur, d'adresse IP, d'identifiant dans l'adresse, de fichier à télécharger ni de site personnel. Ne cite qu'une page dont tu es sûr qu'elle existe ; sinon, omets "references".
11. Schémas : fournis un SVG quand il aide vraiment à comprendre (architecture, flux, circuit électrique, circuit hydraulique ou pneumatique, chaîne cinématique, grafcet, boucle de régulation, cellule robotisée), environ une question sur quatre. Uniquement du SVG, pas de PNG ni de JPEG. Le SVG ne contient ni script, ni attribut on…=, ni foreignObject, ni lien, ni image ou police externe ; texte en français, fond blanc, largeur 900 au plus. Le chemin de "visual" est relatif au fichier du thème.
12. Seulement le type "qcm". "code", "tags", "visual" et "references" sont facultatifs : omets-les plutôt que de les inventer.
13. Pas deux questions qui testent la même notion de la même façon ; varie les angles : définition, cas concret, piège courant, diagnostic de panne ou d'incident. Reste dans le périmètre du thème, sans empiéter sur un autre thème du catalogue.
14. Dans "skills", les mots tels qu'ils apparaissent dans les offres d'emploi (ex. « Python », « automate Siemens », « maintenance préventive », « habilitation électrique »).
15. Tout en français, sauf le code et les noms techniques.

Avant de livrer, vérifie toi-même chaque question : bonne réponse correcte, expectedAnswer identique au choix, longueurs comparables, calculs justes, identifiants uniques, JSON valide.
```
