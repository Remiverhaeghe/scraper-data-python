# Kubernetes

## L'essentiel
- Kubernetes orchestre des conteneurs sur un ensemble de machines : déploiement, mise à l'échelle, redémarrage.
- On décrit l'état voulu en YAML ; le cluster le fait respecter en permanence.
- Plan de contrôle (API, ordonnanceur, etcd) et nœuds de travail (kubelet, environnement d'exécution).

## Objets principaux
- Pod : un ou plusieurs conteneurs qui partagent réseau et stockage ; éphémère.
- Deployment : maintient le nombre de pods voulu et gère les mises à jour progressives.
- Service : adresse stable et répartition de charge vers des pods (ClusterIP, NodePort, LoadBalancer).
- Ingress : routage HTTP depuis l'extérieur.
- ConfigMap et Secret : configuration et données sensibles.
- PersistentVolume et PersistentVolumeClaim : stockage durable.
- Namespace : séparer les environnements ou les équipes.

## Commandes courantes
- kubectl get pods, kubectl describe pod nom, kubectl logs nom, kubectl exec -it nom -- sh.
- kubectl apply -f fichier.yaml, kubectl rollout status, kubectl rollout undo.

## Santé et ressources
- Sondes liveness (redémarrer si bloqué) et readiness (envoyer du trafic seulement si prêt).
- Requêtes et limites de CPU et de mémoire ; dépassement de mémoire : OOMKilled.
- Mise à l'échelle automatique (HorizontalPodAutoscaler).

## Sécurité
- Droits RBAC minimaux, comptes de service dédiés.
- Pods non root, images analysées, politiques réseau entre namespaces.
- Les Secret ne sont qu'encodés en base64 : chiffrer etcd et limiter leur lecture.

## Pièges fréquents
- CrashLoopBackOff : lire les journaux du conteneur précédent (kubectl logs --previous).
- Oublier la sonde readiness et envoyer du trafic à un pod qui démarre.
- Pas de limites de ressources : un pod affame les autres.

## En entretien
- Expliquez Pod, Deployment et Service.
- Décrivez le diagnostic d'un pod qui redémarre en boucle.

## Références
- [Documentation Kubernetes (en français)](https://kubernetes.io/fr/docs/home/)
- [Concepts Kubernetes](https://kubernetes.io/docs/concepts/)
