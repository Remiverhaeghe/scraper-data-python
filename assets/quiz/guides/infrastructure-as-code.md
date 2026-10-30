# Infrastructure as code (Terraform, Ansible)

## L'essentiel
- L'infrastructure se décrit dans des fichiers versionnés, relus et appliqués automatiquement.
- Avantages : reproductibilité, traçabilité, environnements identiques, retour arrière.
- Terraform crée et modifie des ressources (approche déclarative) ; Ansible configure des machines (tâches idempotentes).

## Terraform
- Fournisseurs (providers), ressources, variables, sorties, modules.
- Cycle : terraform init, plan (voir les changements), apply, destroy.
- L'état (state) mémorise ce qui existe : le stocker à distance, verrouillé et protégé, car il peut contenir des secrets.
- Langage HCL ; data sources pour lire l'existant.

## Ansible
- Inventaire des machines, playbooks en YAML, rôles réutilisables.
- Connexion par SSH, sans agent sur les machines.
- Idempotence : relancer un playbook ne change rien si l'état est déjà bon.
- Variables, gabarits Jinja2, handlers pour redémarrer un service après modification.
- Ansible Vault pour chiffrer les secrets.

## Bonnes pratiques
- Tout en Git, revue de code, plan relu avant application.
- Pas de modification manuelle hors code (dérive de configuration).
- Modules et rôles réutilisables, versions des fournisseurs fixées.
- Secrets hors du code : coffre-fort ou variables protégées.

## Pièges fréquents
- Appliquer sans lire le plan et supprimer une ressource par erreur.
- Perdre ou exposer le fichier d'état Terraform.
- Écrire des tâches Ansible non idempotentes (commandes shell brutes).

## En entretien
- Expliquez déclaratif et impératif, et l'idempotence.
- Décrivez ce que vous automatiseriez en premier dans une infrastructure.

## Références
- [Documentation Terraform](https://developer.hashicorp.com/terraform/docs)
- [Documentation Ansible](https://docs.ansible.com/)
- [Infrastructure as code (Wikipédia)](https://fr.wikipedia.org/wiki/Infrastructure_as_code)
