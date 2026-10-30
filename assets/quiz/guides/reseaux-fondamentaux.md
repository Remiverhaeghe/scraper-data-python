# Modèle OSI, TCP/IP et adressage

## L'essentiel
- Le modèle OSI découpe la communication en 7 couches : physique, liaison, réseau, transport, session, présentation, application.
- TCP/IP, utilisé en pratique, en compte 4 : accès réseau, Internet (IP), transport (TCP, UDP), application.
- Chaque couche ajoute son en-tête : encapsulation.

## Adressage
- Adresse MAC (couche 2) : identifiant de la carte réseau, utilisé sur le réseau local.
- Adresse IPv4 (couche 3) : 4 octets, avec un masque qui sépare réseau et hôte.
- Notation CIDR : 192.168.1.0/24, soit 254 adresses d'hôtes utilisables.
- Adresses privées : 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16.
- Passerelle par défaut : le routeur vers les autres réseaux. DNS : traduit les noms en adresses.

## Calculs utiles
- Nombre d'hôtes = 2^(32 - préfixe) - 2 (adresse réseau et diffusion exclues).
- /24 : 254 hôtes ; /25 : 126 ; /26 : 62 ; /30 : 2.
- Deux machines communiquent directement si elles sont dans le même réseau (même masque appliqué).

## Transport
- TCP : connexion établie (SYN, SYN-ACK, ACK), fiable, ordonné. Exemples : HTTP, SSH, Modbus TCP.
- UDP : sans connexion, rapide, sans garantie. Exemples : DNS, streaming, certains protocoles industriels.
- Ports connus : 22 SSH, 53 DNS, 80 HTTP, 443 HTTPS, 502 Modbus, 3306 MySQL.

## Équipements
- Commutateur (switch) : couche 2, aiguille selon les adresses MAC ; VLAN pour séparer.
- Routeur : couche 3, relie des réseaux différents.
- Pare-feu : filtre selon adresses, ports et protocoles.

## Diagnostic
- ping (joignable ?), traceroute ou tracert (chemin), ipconfig ou ip a (configuration), nslookup (DNS), arp -a (voisins).
- Démarche du bas vers le haut : câble et voyants, adresse et masque, passerelle, DNS, service.

## Pièges fréquents
- Deux équipements avec la même adresse IP (conflit).
- Un mauvais masque qui empêche de joindre une machine pourtant proche.
- Croire qu'un ping qui échoue signifie que la machine est éteinte (le pare-feu peut le bloquer).

## En entretien
- Calculez le nombre d'hôtes d'un /26 et expliquez la passerelle.
- Décrivez votre démarche face à un équipement qui ne répond plus.

## Références
- [Modèle OSI (Wikipédia)](https://fr.wikipedia.org/wiki/Mod%C3%A8le_OSI)
- [Suite des protocoles Internet (Wikipédia)](https://fr.wikipedia.org/wiki/Suite_des_protocoles_Internet)
- [Sous-réseau (Wikipédia)](https://fr.wikipedia.org/wiki/Sous-r%C3%A9seau)
