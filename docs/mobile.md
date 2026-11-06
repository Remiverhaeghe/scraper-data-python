# Accès depuis un téléphone

Tableau de bord web sur le téléphone et API de l'application mobile.

Le tableau de bord web s'adapte au téléphone et peut s'installer sur l'écran d'accueil
(menu du navigateur, « Ajouter à l'écran d'accueil »). Pour y accéder hors de chez soi
sans exposer ce PC sur Internet, un réseau privé chiffré relie le téléphone au PC :

1. Installer Tailscale (offre gratuite personnelle) sur le serveur (PC ou NAS) et sur le
   téléphone, avec le même compte.
2. Dans la console d'administration de Tailscale (DNS), activer MagicDNS et « HTTPS
   Certificates ».
3. Sur le serveur, `python -m tools.tailscale_certificate` demande un certificat reconnu
   pour son nom Tailscale (`serveur.xxx.ts.net`) et affiche les lignes du `.env` :
   `WEB_HOST` (adresse Tailscale 100.x.y.z, fermée au Wi-Fi et à Internet),
   `WEB_PUBLIC_HOST` (le nom, transmis par le QR code), `WEB_TLS_CERTFILE`,
   `WEB_TLS_KEYFILE` et `WEB_SECURE_COOKIE`. Le certificat vaut 90 jours : le
   planificateur le renouvelle un mois avant sa fin, et le tableau de bord le recharge
   sans redémarrer ; la page Santé affiche sa date de fin.
4. Relancer `python -m web`, rescanner le QR code depuis l'application, et ouvrir
   `https://serveur.xxx.ts.net:8000` dans le navigateur du téléphone : le tableau de bord
   s'installe alors comme une application.

Sur le Wi-Fi de la maison, sans Tailscale :

1. `WEB_HOST` dans `.env` reçoit l'adresse Wi-Fi du PC (`ipconfig`, carte Wi-Fi), par
   exemple `192.168.1.80`. Le serveur n'écoute plus alors que sur cette adresse :
   depuis le PC aussi, le tableau de bord s'ouvre à `http://192.168.1.80:8000`.
2. Le Wi-Fi est en réseau « Privé » dans Windows, et le pare-feu autorise le port 8000
   sur les réseaux privés seulement : sur un Wi-Fi public, le PC reste fermé.
3. L'adresse du PC peut changer au redémarrage de la box : la réserver pour le PC dans
   les réglages de la box (bail DHCP fixe) évite de la ressaisir.
4. Facultatif, HTTPS : `python -m tools.local_certificate` crée un certificat pour
   l'adresse `WEB_HOST` et affiche les lignes `WEB_TLS_CERTFILE` et `WEB_TLS_KEYFILE`
   à ajouter au `.env`. Après avoir relancé `python -m web`, rescanner le QR code :
   il transmet l'empreinte du certificat, seule acceptée par l'application. Le
   navigateur, lui, signale un certificat inconnu, à accepter une fois ; le tableau
   de bord ne s'installe comme une application qu'avec un certificat reconnu
   (Tailscale en fournit un gratuitement) ou depuis ce PC.

Aucun port n'est ouvert sur la box : seuls les appareils de votre compte Tailscale
atteignent le PC. L'authentification du tableau de bord reste obligatoire. Pour lancer une
recherche depuis le téléphone, le planificateur (`python -m scheduler`) doit tourner sur le PC.
`python -m tools.windows_startup` les lance tous deux à l'ouverture de session, dans des
fenêtres réduites, après 30 secondes laissées au Wi-Fi pour se connecter.

## API de l'application mobile de révision

L'application Flutter du dossier `mobile/` révise hors ligne puis envoie ses réponses :
installation, compilation et premier lancement dans [mobile/README.md](../mobile/README.md). Le
jeton se crée dans Paramètres, « Application mobile » ; son bouton « QR code » (PC) ou
« Afficher le QR code » (web) donne l'adresse et le jeton à scanner depuis l'application.
Chaque requête porte l'en-tête `Authorization: Bearer <jeton>` ; aucune session n'est utilisée.

| Méthode | Adresse | Rôle |
|---|---|---|
| GET | `/api/v1/ping` | Sans jeton : nom de l'application et version de l'API, pour que le téléphone trouve le serveur sur le Wi-Fi |
| GET | `/api/v1/quiz` | Thèmes, questions (réponse et explication comprises), schémas et guides ; `ETag` : 304 si rien n'a changé |
| GET | `/api/v1/progress` | Boîte et date de révision de chaque question, chiffres d'ensemble |
| POST | `/api/v1/exams` | Examens blancs du téléphone, ajoutés sans doublon à l'historique du PC : `{"exams": [{"title", "finished_at", "correct", "count", "seconds"}]}` |
| POST | `/api/v1/flags` | Questions signalées depuis le téléphone, retirées des tirages : `{"question_ids": [...]}` |
| POST | `/api/v1/answers` | Réponses faites hors ligne : `{"answers": [{"id", "question_id", "choice" ou "response", "answered_at"}]}` |
| GET | `/api/v1/offers` | Nouvelles offres de la semaine puis offres retenues (intéressé, postulé, entretien), fiche lisible hors ligne : description, compétences couvertes et manquantes, salaire, distance, position et `near` (dans le rayon des alertes) |
| POST | `/api/v1/applications` | Statuts donnés aux offres sur le téléphone : `{"changes": [{"source", "source_id", "status"}]}` ; notes et date d'entretien gardées |
| GET, POST | `/api/v1/interview` | Questions de la simulation d'entretien ; séries faites sur le téléphone : `{"series": [...]}` |
| GET, POST | `/api/v1/labs` | Simulations jouables hors ligne (scénarios de pannes, niveaux d'automate, de Git, de SQL, d'Excel, de Maven et de Docker, base d'exemple SQL et règles de dialecte, règles des formules Excel, dépôt Maven et images Docker simulés, réussites du PC) ; parties faites sur le téléphone : `{"results": [{"id", "lab", "scenario" et "actions", ou "level" et "program", "history", "steps", "formula" ou "query" et "dialect", "finished_at"}]}`, rejouées par le PC avant d'être comptées |
| GET, POST | `/api/v1/skills` | Grille d'auto-évaluation ; niveaux saisis sur le téléphone : `{"levels": {"Java": 6}}` |
| GET | `/api/v1/replies` | Réponses de recruteurs repérées dans Gmail par le planificateur : offre, statut annoncé, date d'entretien ; jamais le contenu du message |

Les QCM sont dans `questions`. Les calculs, remises en ordre, associations et revues de code
sont dans `interactive_questions`, avec leur `type` : une application qui ne les connaît pas
encore les ignore. Leurs éléments sont dans l'ordre correct, à mélanger à l'affichage. Une
réponse porte alors `response` : texte du calcul (« 2,3 mA »), ou liste d'indices d'origine pour
l'ordre, l'association et les constats cochés d'une revue de code.

Le téléphone corrige lui-même avec le contenu téléchargé ; à l'envoi, le serveur recalcule
chaque correction, ignore une réponse déjà reçue (même `id`) et refuse une date hors limites.
Les réponses sont rangées par heure de réponse : un envoi tardif ne fausse pas la répétition
espacée. Au plus 500 réponses par envoi.
