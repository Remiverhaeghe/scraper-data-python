"""Glossaire des compétences repérées dans les offres : une définition courte par
compétence, pour comprendre une exigence ou l'expliquer en entretien
"""

from job.enrichment import SKILL_PATTERNS

SKILL_GLOSSARY = {
    "Python": "Langage polyvalent et lisible, utilisé pour le web, les scripts, "
    "la donnée et l'automatisation.",
    "Java": "Langage objet compilé pour la machine virtuelle Java, très présent "
    "dans les applications d'entreprise.",
    "JavaScript": "Langage du navigateur, qui rend les pages web interactives ; "
    "s'utilise aussi côté serveur avec Node.js.",
    "TypeScript": "JavaScript avec des types vérifiés à la compilation, pour "
    "fiabiliser les gros projets front et back.",
    "SQL": "Langage d'interrogation des bases relationnelles : sélectionner, "
    "joindre, agréger et modifier des données.",
    "PostgreSQL": "Base de données relationnelle libre, réputée pour sa robustesse "
    "et sa conformité au standard SQL.",
    "MySQL": "Base de données relationnelle libre très répandue, notamment pour "
    "les sites web.",
    "SQL Server": "Base de données relationnelle de Microsoft, courante dans les "
    "systèmes d'information Windows.",
    "MongoDB": "Base de données orientée documents (JSON), sans schéma fixe.",
    "React": "Bibliothèque JavaScript de Meta pour construire des interfaces à "
    "base de composants.",
    "Angular": "Cadriciel front-end de Google, en TypeScript, complet et structuré.",
    "Vue.js": "Cadriciel JavaScript progressif pour interfaces web, réputé simple "
    "à prendre en main.",
    "Node.js": "Environnement d'exécution JavaScript côté serveur, adapté aux API "
    "et aux traitements asynchrones.",
    "Django": "Cadriciel web Python « tout compris » : ORM, administration, "
    "formulaires et sécurité.",
    "Flask": "Micro-cadriciel web Python, minimal et extensible.",
    "FastAPI": "Cadriciel Python pour API REST rapides, typées et documentées "
    "automatiquement.",
    "Spring": "Écosystème Java de référence pour les applications d'entreprise : "
    "injection de dépendances, web, données (Spring Boot).",
    "Hibernate": "ORM Java : fait correspondre des objets Java aux tables d'une "
    "base relationnelle (JPA).",
    "JSF / PrimeFaces": "JavaServer Faces, cadriciel d'interfaces web Java à base "
    "de composants, enrichi par la bibliothèque PrimeFaces.",
    "Maven": "Outil de construction Java : dépendances, compilation, tests et "
    "packaging décrits dans un pom.xml.",
    "Tomcat": "Serveur d'applications Java qui exécute servlets et pages JSP.",
    "JUnit": "Cadriciel de tests unitaires de référence en Java.",
    "PHP": "Langage serveur historique du web, utilisé par de nombreux sites et "
    "CMS.",
    "Symfony": "Cadriciel PHP structuré, à base de composants réutilisables.",
    "C#": "Langage objet de Microsoft pour la plateforme .NET : applications, web "
    "et jeux (Unity).",
    ".NET": "Plateforme de développement de Microsoft (C#, ASP.NET), "
    "multiplateforme depuis .NET Core.",
    "C++": "Langage compilé performant, proche du matériel : logiciels "
    "embarqués, jeux, calcul.",
    "Go": "Langage compilé de Google, simple et concurrent, prisé pour les "
    "services cloud.",
    "Rust": "Langage compilé sûr pour la mémoire sans ramasse-miettes, pour le "
    "logiciel système.",
    "Kotlin": "Langage moderne pour la machine virtuelle Java, langage officiel "
    "d'Android.",
    "Swift": "Langage d'Apple pour les applications iOS et macOS.",
    "Scala": "Langage fonctionnel et objet sur la machine virtuelle Java, utilisé "
    "avec Spark.",
    "Docker": "Conteneurs : une application et ses dépendances empaquetées pour "
    "tourner partout de la même façon.",
    "Kubernetes": "Orchestrateur de conteneurs : déploiement, mise à l'échelle et "
    "redémarrage automatiques.",
    "AWS": "Amazon Web Services, premier fournisseur de cloud : serveurs, "
    "stockage, bases et services managés.",
    "Azure": "Cloud de Microsoft, souvent choisi par les entreprises déjà "
    "équipées en outils Microsoft.",
    "GCP": "Google Cloud Platform, le cloud de Google, fort en données et en IA.",
    "Terraform": "Infrastructure décrite en code : serveurs et réseaux créés et "
    "versionnés à partir de fichiers.",
    "Ansible": "Automatisation de la configuration des serveurs par des scripts "
    "déclaratifs (playbooks), sans agent.",
    "Linux": "Système d'exploitation libre qui fait tourner l'essentiel des "
    "serveurs : ligne de commande, droits, services.",
    "Git": "Gestion de versions décentralisée : historique, branches, fusions et "
    "travail en équipe.",
    "Jira": "Outil de suivi des tickets et des sprints, très utilisé en méthode "
    "agile.",
    "CI/CD": "Intégration et déploiement continus : chaque modification est "
    "testée puis livrée automatiquement.",
    "Kafka": "Plateforme de flux de messages distribuée, pour faire circuler des "
    "événements entre applications.",
    "Spark": "Moteur de calcul distribué pour traiter de gros volumes de données.",
    "Airflow": "Orchestrateur de traitements de données planifiés, décrits en "
    "Python (DAG).",
    "Pandas": "Bibliothèque Python de manipulation de données en tableaux.",
    "TensorFlow": "Bibliothèque d'apprentissage automatique de Google, notamment "
    "pour les réseaux de neurones.",
    "PyTorch": "Bibliothèque d'apprentissage profond de Meta, appréciée en "
    "recherche comme en production.",
    "Power BI": "Outil de Microsoft pour construire des tableaux de bord et des "
    "rapports à partir de données.",
    "Tableau": "Logiciel de visualisation de données et de tableaux de bord "
    "interactifs.",
    "Excel": "Tableur de Microsoft : formules, tableaux croisés dynamiques, "
    "graphiques.",
    "SAP": "Progiciel de gestion intégré (ERP) qui couvre finance, achats, "
    "production et logistique.",
    "Salesforce": "Logiciel de gestion de la relation client (CRM) en ligne.",
    "HTML": "Langage de structure des pages web : titres, paragraphes, liens, "
    "formulaires.",
    "CSS": "Langage de mise en forme des pages web : couleurs, disposition, "
    "adaptation aux écrans.",
    "GraphQL": "Langage de requête d'API où le client demande exactement les "
    "données dont il a besoin.",
    "REST": "Style d'API web fondé sur HTTP : ressources, verbes (GET, POST...) "
    "et codes de réponse.",
    "XML": "Format texte balisé pour échanger des données structurées.",
    "SFTP": "Transfert de fichiers sécurisé par SSH.",
    "Agile": "Façon de mener un projet par courtes itérations, avec des retours "
    "fréquents (Scrum, Kanban).",
    "Automates programmables": "Automates industriels (API) qui pilotent une "
    "machine à partir de capteurs et d'actionneurs.",
    "Siemens TIA Portal": "Logiciel de Siemens pour programmer automates S7, "
    "écrans et variateurs dans un même projet.",
    "Schneider": "Matériel et logiciels d'automatisme de Schneider Electric "
    "(automates Modicon, EcoStruxure).",
    "Rockwell": "Automatismes Rockwell Automation / Allen-Bradley, programmés "
    "avec Studio 5000.",
    "Grafcet": "Représentation graphique normalisée du fonctionnement séquentiel "
    "d'un automatisme : étapes et transitions.",
    "Supervision / IHM": "Écrans de conduite et de supervision qui affichent "
    "l'état d'une installation et permettent d'agir dessus.",
    "Réseaux industriels": "Bus et réseaux de terrain qui relient automates, "
    "capteurs et variateurs (Profinet, Modbus, Ethernet/IP).",
    "Électrotechnique": "Production, distribution et utilisation de l'énergie "
    "électrique : moteurs, armoires, protections.",
    "Électronique": "Conception et dépannage de circuits et de cartes "
    "électroniques.",
    "Habilitation électrique": "Titre délivré par l'employeur qui autorise à "
    "travailler sur ou près d'installations électriques (B1V, BR, BC, H0...).",
    "Schémas électriques": "Lecture et réalisation des plans de câblage et de "
    "puissance d'une installation.",
    "Variateurs de vitesse": "Équipements qui pilotent la vitesse et le couple "
    "d'un moteur électrique.",
    "Pneumatique": "Commande de mouvements par air comprimé : vérins, "
    "distributeurs, circuits.",
    "Hydraulique": "Transmission de puissance par fluide sous pression : "
    "pompes, vérins, centrales.",
    "Mécanique": "Montage, réglage et dépannage des ensembles mécaniques : "
    "transmissions, roulements, guidages.",
    "Instrumentation et régulation": "Mesure des grandeurs physiques (pression, "
    "débit, température) et boucles de régulation qui les maintiennent.",
    "Robotique": "Programmation et maintenance de robots industriels (Fanuc, "
    "ABB, Kuka...).",
    "Maintenance préventive et curative": "Entretien planifié pour éviter les "
    "pannes, et dépannage quand elles surviennent.",
    "GMAO": "Logiciel de gestion de la maintenance : interventions, stocks de "
    "pièces, historique des équipements.",
    "Lean": "Démarche d'amélioration continue qui chasse les gaspillages (5S, "
    "flux, standards).",
    "TPM": "Maintenance productive totale : les opérateurs participent à "
    "l'entretien pour fiabiliser les machines.",
    "AMDEC": "Analyse des modes de défaillance, de leurs effets et de leur "
    "criticité, pour prioriser les actions.",
    "Lecture de plans": "Comprendre les dessins techniques : vues, cotes, "
    "tolérances et nomenclatures.",
    "CAO": "Conception assistée par ordinateur : pièces et ensembles dessinés "
    "en 2D ou 3D (SolidWorks, CATIA...).",
    "Soudure": "Assemblage de pièces métalliques par fusion (procédés TIG, MIG, "
    "MAG, à l'arc).",
    "CVC et froid": "Chauffage, ventilation, climatisation et installations "
    "frigorifiques.",
}

# Recherche sans tenir compte de la casse : « python » trouve « Python ».
GLOSSARY_INDEX = {vSkill.lower(): vSkill for vSkill in SKILL_GLOSSARY}


def describe_skill(pSkill):
    """Retourne la définition d'une compétence, ou None si elle est inconnue."""

    vName = GLOSSARY_INDEX.get(str(pSkill or "").strip().lower())

    rDefinition = SKILL_GLOSSARY[vName] if vName else None

    return rDefinition


def build_glossary(pSkills=None):
    """Retourne (compétence, définition) des compétences données, ou de toutes,
    par ordre alphabétique.
    """

    vSkills = SKILL_GLOSSARY if pSkills is None else pSkills

    rGlossary = sorted(
        {
            (GLOSSARY_INDEX[str(vSkill).strip().lower()], vDefinition)
            for vSkill in vSkills
            if (vDefinition := describe_skill(vSkill))
        },
        key=lambda pItem: pItem[0].lower(),
    )

    return rGlossary


def list_undefined_skills():
    """Retourne les compétences repérées dans les offres sans définition."""

    rSkills = [vSkill for vSkill in SKILL_PATTERNS if vSkill not in SKILL_GLOSSARY]

    return rSkills
