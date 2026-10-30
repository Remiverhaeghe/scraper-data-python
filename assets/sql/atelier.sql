-- Base d'exemple du bac à sable SQL : une usine, ses machines et leur maintenance.
-- Chargée dans une base SQLite en mémoire, neuve à chaque requête.

CREATE TABLE atelier (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL
);

CREATE TABLE machine (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    nom TEXT NOT NULL,
    atelier_id INTEGER NOT NULL REFERENCES atelier (id),
    mise_en_service TEXT NOT NULL,
    puissance_kw REAL NOT NULL
);

CREATE TABLE technicien (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    specialite TEXT NOT NULL,
    atelier_id INTEGER REFERENCES atelier (id)
);

CREATE TABLE intervention (
    id INTEGER PRIMARY KEY,
    machine_id INTEGER NOT NULL REFERENCES machine (id),
    technicien_id INTEGER REFERENCES technicien (id),
    type TEXT NOT NULL,
    debut TEXT NOT NULL,
    fin TEXT,
    cout REAL
);

CREATE TABLE piece (
    id INTEGER PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    libelle TEXT NOT NULL,
    stock INTEGER NOT NULL,
    stock_mini INTEGER NOT NULL,
    prix REAL NOT NULL
);

CREATE TABLE piece_utilisee (
    intervention_id INTEGER NOT NULL REFERENCES intervention (id),
    piece_id INTEGER NOT NULL REFERENCES piece (id),
    quantite INTEGER NOT NULL
);

INSERT INTO atelier (id, nom) VALUES
    (1, 'Usinage'),
    (2, 'Assemblage'),
    (3, 'Emballage'),
    (4, 'Peinture');

INSERT INTO machine (id, code, nom, atelier_id, mise_en_service, puissance_kw) VALUES
    (1, 'TOUR-01', 'Tour CN', 1, '2012-03-15', 22.0),
    (2, 'FRAI-01', 'Centre d''usinage 5 axes', 1, '2019-09-02', 37.0),
    (3, 'FRAI-02', 'Fraiseuse conventionnelle', 1, '2008-05-20', 7.5),
    (4, 'PRES-01', 'Presse hydraulique 100 t', 2, '2014-11-04', 30.0),
    (5, 'ROBO-01', 'Robot de vissage', 2, '2021-02-10', 4.0),
    (6, 'CONV-01', 'Convoyeur principal', 2, '2010-06-01', 5.5),
    (7, 'EMB-01', 'Encartonneuse', 3, '2017-04-12', 11.0),
    (8, 'EMB-02', 'Banderoleuse', 3, '2016-08-30', 3.0),
    (9, 'COMP-01', 'Compresseur d''air', 2, '2009-01-19', 45.0);

INSERT INTO technicien (id, nom, prenom, specialite, atelier_id) VALUES
    (1, 'Martin', 'Julie', 'électricité', 1),
    (2, 'Bernard', 'Karim', 'mécanique', 1),
    (3, 'Petit', 'Sophie', 'automatisme', 2),
    (4, 'Durand', 'Thomas', 'mécanique', 2),
    (5, 'Moreau', 'Léa', 'hydraulique', 3),
    (6, 'Garcia', 'Nicolas', 'électricité', NULL);

INSERT INTO intervention (id, machine_id, technicien_id, type, debut, fin, cout) VALUES
    (1, 1, 2, 'preventive', '2026-01-12 08:00:00', '2026-01-12 10:00:00', 180.00),
    (2, 4, 5, 'corrective', '2026-01-20 14:30:00', '2026-01-21 09:00:00', 1250.00),
    (3, 6, 3, 'corrective', '2026-02-03 07:15:00', '2026-02-03 08:45:00', 95.50),
    (4, 2, 1, 'corrective', '2026-02-17 10:00:00', '2026-02-17 16:30:00', 640.00),
    (5, 7, 4, 'preventive', '2026-03-02 08:00:00', '2026-03-02 09:30:00', 120.00),
    (6, 4, 5, 'preventive', '2026-03-09 13:00:00', '2026-03-09 17:00:00', 310.00),
    (7, 9, 2, 'corrective', '2026-03-25 06:00:00', '2026-03-25 11:00:00', 870.00),
    (8, 1, 1, 'corrective', '2026-04-08 09:00:00', '2026-04-08 12:00:00', 420.00),
    (9, 5, 3, 'corrective', '2026-04-15 15:00:00', '2026-04-15 15:45:00', 60.00),
    (10, 3, 2, 'preventive', '2026-04-22 08:00:00', '2026-04-22 10:00:00', 75.00),
    (11, 4, 4, 'corrective', '2026-05-06 10:30:00', '2026-05-07 18:00:00', 2340.00),
    (12, 8, NULL, 'corrective', '2026-05-19 11:00:00', '2026-05-19 12:00:00', 45.00),
    (13, 6, 3, 'preventive', '2026-05-27 07:00:00', '2026-05-27 08:00:00', 80.00),
    (14, 2, 1, 'preventive', '2026-06-03 08:00:00', '2026-06-03 12:00:00', 260.00),
    (15, 7, 5, 'corrective', '2026-06-10 14:00:00', '2026-06-10 16:00:00', 150.00),
    (16, 9, 4, 'preventive', '2026-06-16 08:00:00', '2026-06-16 09:00:00', 90.00),
    (17, 1, 2, 'corrective', '2026-06-24 10:00:00', NULL, NULL),
    (18, 5, NULL, 'corrective', '2026-06-29 16:00:00', NULL, NULL),
    (19, 4, 5, 'corrective', '2026-06-27 09:00:00', NULL, NULL);

INSERT INTO piece (id, reference, libelle, stock, stock_mini, prix) VALUES
    (1, 'ROU-6204', 'Roulement à billes 6204', 12, 5, 8.40),
    (2, 'ROU-6305', 'Roulement à billes 6305', 3, 4, 14.80),
    (3, 'COU-A42', 'Courroie trapézoïdale A42', 6, 2, 11.20),
    (4, 'JOI-HYD25', 'Joint hydraulique 25 mm', 0, 6, 6.75),
    (5, 'FIL-HYD10', 'Filtre hydraulique 10 µm', 2, 2, 32.00),
    (6, 'CAP-IND12', 'Capteur inductif M12', 4, 2, 27.50),
    (7, 'RLY-24V', 'Relais 24 V', 15, 10, 9.90),
    (8, 'FUS-10A', 'Fusible 10 A', 40, 20, 0.85),
    (9, 'ROU-6001', 'Roulement à billes 6001', 0, 0, 5.20),
    (10, 'VAR-075', 'Variateur 0,75 kW', 1, 1, 289.00),
    (11, 'COU-B50', 'Courroie trapézoïdale B50', 0, 0, 13.40);

INSERT INTO piece_utilisee (intervention_id, piece_id, quantite) VALUES
    (1, 1, 2),
    (2, 4, 6),
    (2, 5, 1),
    (3, 3, 1),
    (4, 6, 1),
    (4, 7, 2),
    (7, 8, 3),
    (8, 1, 2),
    (8, 3, 1),
    (10, 3, 2),
    (11, 4, 8),
    (11, 5, 1),
    (13, 3, 1),
    (14, 6, 2),
    (15, 7, 1),
    (16, 8, 2);
