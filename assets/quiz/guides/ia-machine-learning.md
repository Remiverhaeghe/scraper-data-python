# IA et machine learning

## L'essentiel
- Intelligence artificielle : tout système qui produit une prédiction, une décision ou un contenu à partir de données. Le machine learning en est la branche qui apprend sur des exemples, le deep learning celle des réseaux de neurones à nombreuses couches.
- Un modèle ne programme pas des règles : il ajuste des paramètres pour reproduire ce que montrent les exemples. Il hérite donc des qualités et des défauts des données.
- Toute prédiction est une estimation, avec un taux d'erreur qu'il faut mesurer avant la mise en service et surveiller ensuite.
- La plus grande part du travail est la préparation des données, pas le choix de l'algorithme.
- Une IA conseille ; la personne ou l'entreprise qui applique la recommandation reste responsable.

## Les familles d'apprentissage
- Supervisé : des exemples avec la bonne réponse (étiquette). Classification si la réponse est une catégorie (bonne ou défectueuse), régression si c'est un nombre (heures avant panne).
- Non supervisé : sans étiquette, on cherche une structure. Regroupement (k-means), détection d'anomalies, réduction de dimension.
- Par renforcement : un agent essaie, reçoit une récompense et améliore sa stratégie (robotique, jeux).
- Auto-supervisé : les étiquettes viennent des données elles-mêmes, comme le mot suivant d'un texte. C'est le préentraînement des LLM.

## Données et évaluation
- Trois jeux : entraînement (apprendre), validation (régler), test (mesure finale, une seule fois). Par exemple 70 / 15 / 15 %.
- Séparer avant toute préparation : normaliser sur tout le jeu laisse fuir l'information du test. Un Pipeline scikit-learn refait la préparation dans chaque pli.
- Fuite de données : une variable connue seulement après l'événement (date de remplacement de la pièce) donne la réponse au modèle. Score superbe au test, effondrement en production.
- Validation croisée à k plis : k entraînements, chacun évalué sur une part différente ; on retient la moyenne.
- Surapprentissage : excellent sur l'entraînement, médiocre au test. Remèdes : plus de données, modèle plus simple, régularisation, arrêt précoce.
- Sous-apprentissage : médiocre partout. Remèdes : variables utiles, modèle plus riche.
- Classes déséquilibrées (1 % de pannes) : pondérer les classes (class_weight="balanced") ou rééchantillonner, sur l'entraînement uniquement.

## Les mesures
- Matrice de confusion : VP (défaut trouvé), FN (défaut manqué), FP (fausse alerte), VN (pièce bonne acceptée).
- Exactitude = (VP + VN) / total. Trompeuse sur une classe rare : déclarer chaque pièce bonne donne déjà 98 % avec 2 % de défauts.
- Précision = VP / (VP + FP) : parmi les alertes, combien sont justes.
- Rappel = VP / (VP + FN) : parmi les vrais défauts, combien sont trouvés.
- F1 = 2 × P × R / (P + R) : moyenne harmonique, punit le point faible.
- Régression : MAE (écart moyen, dans l'unité prédite), RMSE (punit les grosses erreurs).
- AUC : capacité à classer un positif avant un négatif, quel que soit le seuil ; 0,5 vaut le hasard.
- Le seuil se choisit avec le métier : l'abaisser fait monter le rappel et baisser la précision.

## Les algorithmes courants
- Régression linéaire ou logistique : base simple, lisible, à essayer d'abord.
- Arbre de décision : suite de questions, très lisible, surapprend vite seul.
- Forêt aléatoire : moyenne de nombreux arbres, robuste.
- Arbres boostés (XGBoost, LightGBM) : souvent les meilleurs sur des tableaux de mesures.
- k plus proches voisins : vote des exemples voisins ; variables à mettre à la même échelle.
- k-means : regroupement en k groupes choisis à l'avance.
- Isolation Forest, autoencodeur : détection d'anomalies apprise sur les cas normaux.

## Réseaux de neurones
- Des couches de neurones, des poids, une fonction d'activation (ReLU) qui apporte la non-linéarité.
- Entraînement : prédiction, perte, rétropropagation des gradients, mise à jour des poids par descente de gradient : w ← w − taux × gradient.
- Taux d'apprentissage trop fort : la perte oscille ou diverge. Trop faible : apprentissage lent.
- Époque : un passage complet sur le jeu ; lot (batch) : groupe d'exemples traités ensemble.
- CNN : images (contrôle visuel). LSTM : séries temporelles. Transformer : texte, LLM. Diffusion : génération d'images.
- Apprentissage par transfert : partir d'un modèle préentraîné et l'affiner sur quelques centaines d'exemples.
- PyTorch : zero_grad(), model(x), perte, backward(), step() à chaque lot ; model.eval() et torch.no_grad() pour prédire.

## Les grands modèles de langage
- Un LLM prédit le token suivant, un morceau de mot à la fois. Il ne vérifie rien de lui-même.
- Hallucination : réponse fausse présentée avec assurance (norme, fonction ou valeur inventée). Vérifier toute information importante.
- Fenêtre de contexte : consigne, historique, documents et réponse partagent une limite comptée en tokens.
- Connaissances arrêtées à une date ; calculs précis peu fiables sans outil.
- Température basse : réponses stables (extraction, code). Haute : réponses variées (idées).
- Une bonne demande donne un rôle, une tâche précise, un format et des limites ; quelques exemples résolus (few-shot) valent mieux qu'une longue description.
- Code proposé par un assistant : le comprendre, le tester, vérifier que les bibliothèques citées existent.

## RAG, embeddings et modèles locaux
- Embedding : vecteur qui représente le sens d'un texte ; deux textes proches ont des vecteurs proches (similarité cosinus).
- RAG : les documents sont découpés en passages, convertis en embeddings et rangés dans une base vectorielle ; à chaque question, les passages proches sont joints au prompt.
- RAG plutôt que fine-tuning pour des documents qui changent : on réindexe, on cite la source. Le fine-tuning ajuste plutôt le style et le comportement.
- Modèle local (Ollama, llama.cpp) : données qui restent sur le poste, sans abonnement. `ollama run mistral` télécharge puis lance le modèle ; API locale sur le port 11434.
- Mémoire des poids : paramètres × octets par poids. 7 milliards en 16 bits = 14 Go ; quantifié en 4 bits, environ 4 Go.
- Hugging Face : modèles ouverts ; vérifier la licence et la carte du modèle, préférer safetensors au format pickle, qui peut exécuter du code.

## IA en industrie
- Maintenance prédictive : intervenir selon l'état mesuré (vibrations, température, courant), pas à date fixe. Il faut un historique de mesures et des pannes datées dans la GMAO.
- Vision industrielle : CNN préentraîné affiné sur ses pièces, exécuté au pied de la ligne (edge) pour décider en quelques millisecondes.
- Détection d'anomalies : apprendre l'aspect normal quand les défauts sont rares ou inconnus.
- Fatigue d'alerte : trop de fausses alertes et les équipes ignorent aussi les vraies. Seuils réglés avec la maintenance.
- Dérive des données : nouvelle matière, capteur décalé, éclairage changé. Surveiller entrées, prédictions et résultats réels, puis réentraîner.
- Jumeau numérique : modèle d'un équipement alimenté par ses mesures, pour simuler sans toucher à la production.

## Droit, sécurité et éthique
- Règlement (UE) 2024/1689 sur l'IA (AI Act), appliqué par étapes depuis août 2024 : pratiques interdites (notation sociale, reconnaissance des émotions au travail), haut risque (recrutement, composant de sécurité d'une machine), transparence (chatbot, contenu généré), risque minimal.
- Haut risque : gestion des risques, qualité des données, documentation, journalisation, contrôle humain.
- Le RGPD s'applique en plus : données de salariés ou de clients = finalité, base légale, minimisation, information ; CSE consulté pour un outil de contrôle de l'activité.
- Biais : un modèle reproduit les décisions passées, même sans la variable sensible. Mesurer les résultats par groupe.
- Explicabilité : importance des variables, SHAP, LIME ; une alerte qu'on peut vérifier inspire confiance.
- Ne pas coller de plans, de code source ni de données personnelles dans un assistant public sans accord.
- Injection de prompt : une consigne cachée dans un document ou un courriel peut détourner le modèle. Séparer données et instructions, limiter les droits des agents, faire valider les actions.

## Pièges fréquents
- Juger un modèle sur l'exactitude quand la classe intéressante est rare.
- Évaluer sur les données d'entraînement, ou normaliser avant de séparer.
- Croire qu'une réponse de LLM bien rédigée est exacte.
- Confondre k-means (regroupement sans étiquette) et k-NN (classification par les voisins).
- Réentraîner chaque semaine un modèle par fine-tuning au lieu d'indexer les documents.
- Déployer sans surveiller : la dérive arrive sans bruit.

## En entretien
- Partez d'un cas concret : « prédire les arrêts d'un convoyeur à partir des vibrations et de la GMAO ».
- Citez la mesure choisie et pourquoi : rappel pour ne pas manquer de défaut, précision pour limiter les fausses alertes.
- Montrez que vous connaissez les limites : données, dérive, contrôle humain, AI Act et RGPD.
- Pour un usage des assistants IA au quotidien, décrivez vos garde-fous : relecture, tests, pas de données sensibles.

## Références
- [Apprentissage automatique (Wikipédia)](https://fr.wikipedia.org/wiki/Apprentissage_automatique)
- [Guide de l'utilisateur de scikit-learn](https://scikit-learn.org/stable/user_guide.html)
- [Tutoriels PyTorch](https://pytorch.org/tutorials/)
- [Ollama](https://ollama.com/)
- [Règlement (UE) 2024/1689 sur l'intelligence artificielle (EUR-Lex)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [Intelligence artificielle (CNIL)](https://www.cnil.fr/fr/intelligence-artificielle)
- [Top 10 des risques des applications LLM (OWASP)](https://genai.owasp.org/llm-top-10/)
