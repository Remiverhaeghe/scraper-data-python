# Entretien PHP et web

## L'essentiel
- Les questions portent sur PHP, HTML et CSS, JavaScript et jQuery, HTTP et la sécurité web.
- On attend la compréhension du cycle d'une requête : navigateur, serveur, base, réponse.

## PHP
- Typage : comparaison stricte === plutôt que == ; déclarations de types et strict_types.
- Tableaux associatifs, fonctions array_map, array_filter.
- Programmation objet : classes, interfaces, traits, espaces de noms, autoload Composer.
- PDO avec requêtes préparées contre l'injection SQL.
- Frameworks : Symfony, Laravel ; gestion des dépendances avec Composer.
- Sessions et cookies, password_hash et password_verify.

## HTML et CSS
- HTML sémantique : header, nav, main, article, button plutôt que des div partout.
- Modèle de boîte : content, padding, border, margin ; box-sizing: border-box.
- Mise en page : flexbox (une dimension), grid (deux dimensions), media queries pour le responsive.
- Spécificité des sélecteurs et cascade.

## JavaScript et jQuery
- Manipuler le DOM, écouter des événements, requêtes asynchrones (fetch, $.ajax).
- jQuery reste présent dans du code existant ; le JavaScript natif suffit souvent aujourd'hui.

## HTTP et sécurité
- Méthodes, codes de réponse, en-têtes, cookies.
- XSS (échapper l'affichage avec htmlspecialchars), CSRF (jeton de formulaire), injection SQL (requêtes préparées).

## Pièges fréquents
- Comparer avec == en PHP ("abc" == 0 selon les versions).
- Concaténer des entrées utilisateur dans une requête SQL.
- Afficher des données sans les échapper.

## Références
- [Documentation PHP (en français)](https://www.php.net/manual/fr/)
- [HTML (MDN)](https://developer.mozilla.org/fr/docs/Web/HTML)
- [CSS (MDN)](https://developer.mozilla.org/fr/docs/Web/CSS)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
