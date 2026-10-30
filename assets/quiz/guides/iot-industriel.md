# IoT industriel et industrie 4.0

## L'essentiel
- L'IIoT relie capteurs, machines et systèmes pour exploiter les données de production : surveillance, maintenance prévisionnelle, énergie, qualité.
- On part d'un besoin métier (pannes d'un équipement, consommation, rebuts), pas des capteurs.
- La production ne doit jamais dépendre du cloud : l'edge collecte et réagit sur site, le cloud stocke et analyse sur la durée.

## La pyramide de l'automatisation (ISA-95)
- Niveau 0 : capteurs et actionneurs.
- Niveau 1 : automates et régulateurs.
- Niveau 2 : supervision (SCADA, IHM, historique).
- Niveau 3 : MES, ordres de fabrication, traçabilité, TRS.
- Niveau 4 : ERP, gestion de l'entreprise.

## MQTT
- Publication et abonnement : les clients publient sur des topics, le broker redistribue aux abonnés.
- Topics hiérarchiques : usine/ligne2/four/temperature. Joker + pour un niveau, # pour tous les niveaux suivants.
- QoS 0 : au plus une fois ; QoS 1 : au moins une fois (doublons possibles) ; QoS 2 : exactement une fois.
- Retain : le broker garde la dernière valeur pour les nouveaux abonnés.
- Last Will : message publié si un client disparaît brutalement.
- Ports : 1883 en clair, 8883 sur TLS.

## Autres protocoles
- OPC UA : client-serveur ou publication, modèle d'information typé, certificats et chiffrement intégrés, port 4840.
- Modbus : très répandu, simple, sans sécurité ; port 502 en TCP, RTU sur RS-485.
- 4-20 mA : zéro vivant à 4 mA pour détecter un fil coupé ; HART y superpose du numérique.
- IO-Link : communication numérique point à point avec le capteur sur un câble standard.
- Sans fil : LoRaWAN et NB-IoT pour la longue portée sur batterie, Wi-Fi pour le débit, BLE pour la courte portée, 5G privée pour la latence.

## Formules et ordres de grandeur
- 4-20 mA : valeur = (courant - 4) / 16 × étendue de mesure.
- Échantillonnage : au moins deux fois la fréquence la plus haute (Shannon), en pratique 2,5 à 5 fois.
- Volume : mesures par seconde × taille × 86 400 = octets par jour.
- Autonomie : capacité (mAh) / consommation moyenne (mA) = heures, avant les pertes réelles.

## Données
- Horodatage synchronisé (NTP, PTP) pour corréler les machines.
- Qualité associée à chaque valeur : une valeur figée par une coupure doit être signalée.
- Bande morte et rapport par exception réduisent le volume sans perdre l'information utile.
- Bases de séries temporelles (InfluxDB, TimescaleDB, historians) pour les mesures horodatées.

## Sécurité
- Changer les mots de passe par défaut, désactiver les services inutiles.
- Séparer le réseau des machines du réseau bureautique (zones et conduits).
- Connexions sortantes chiffrées vers le cloud, aucun port entrant ouvert.
- Les fonctions de sécurité machine restent câblées et certifiées : l'IoT supervise, il ne protège pas.

## Pièges fréquents
- Installer des capteurs sans objectif : les données dorment.
- Confondre une valeur constante et une perte de communication.
- Multiplier les fausses alertes : les équipes finissent par les ignorer.
- Oublier la maintenance : l'alerte doit déboucher sur un bon de travail.

## En entretien
- Racontez un exemple : mesure suivie, alerte, intervention planifiée, panne évitée.
- Montrez que vous faites le lien entre terrain et données : votre expérience de maintenance est un atout.
- Citez la pile que vous connaissez : passerelle, MQTT, base de séries temporelles, tableau de bord.

## Références
- [Internet industriel des objets (Wikipédia)](https://fr.wikipedia.org/wiki/Internet_industriel_des_objets)
- [MQTT (site officiel)](https://mqtt.org/)
- [OPC Unified Architecture (Wikipédia, en anglais)](https://en.wikipedia.org/wiki/OPC_Unified_Architecture)
- [ISA-95 (Wikipédia)](https://fr.wikipedia.org/wiki/ISA-95)
- [Edge computing (Wikipédia)](https://fr.wikipedia.org/wiki/Edge_computing)
- [Jumeau numérique (Wikipédia)](https://fr.wikipedia.org/wiki/Jumeau_num%C3%A9rique)
- [LoRaWAN (Wikipédia)](https://fr.wikipedia.org/wiki/LoRaWAN)
- [IO-Link (Wikipédia)](https://fr.wikipedia.org/wiki/IO-Link)
