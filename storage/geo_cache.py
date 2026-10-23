"""Coordonnées des lieux d'offres : cache du géocodage et position de chaque offre"""

from storage.database import connect_database


def get_cached_locations(pDatabaseFile):
    """Retourne les lieux déjà cherchés : clé vers (latitude, longitude) ou None."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT location_key, latitude, longitude FROM geo_cache"
        ).fetchall()

    finally:
        vConnection.close()

    rLocations = {
        vKey: None if vLatitude is None else (vLatitude, vLongitude)
        for vKey, vLatitude, vLongitude in vRows
    }

    return rLocations


def get_cached_departments(pDatabaseFile):
    """Retourne le département de chaque lieu cherché : clé vers numéro, ou None."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rDepartments = dict(
            vConnection.execute("SELECT location_key, department FROM geo_cache")
        )

    finally:
        vConnection.close()

    return rDepartments


def save_location(pDatabaseFile, pKey, pCoordinates, pLabel, pNow, pDepartment=None):
    """Garde le résultat d'une recherche de lieu ; pCoordinates None s'il est inconnu."""

    vLatitude, vLongitude = pCoordinates or (None, None)
    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            INSERT INTO geo_cache (
                location_key, latitude, longitude, label, looked_up_at, department
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(location_key) DO UPDATE SET
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                label = excluded.label,
                looked_up_at = excluded.looked_up_at,
                department = excluded.department
            """,
            (
                pKey,
                vLatitude,
                vLongitude,
                pLabel,
                pNow.isoformat(timespec="seconds"),
                pDepartment,
            ),
        )
        vConnection.commit()

    finally:
        vConnection.close()


def get_offers_to_locate(pDatabaseFile, pCountry):
    """Retourne la source, l'identifiant et le lieu des offres du pays à placer.

    Une offre placée avant que le département soit gardé l'est de nouveau.
    """

    vConnection = connect_database(pDatabaseFile)

    try:
        rOffers = vConnection.execute(
            """
            SELECT source, source_id, location
            FROM job_offer
            WHERE country = ?
            AND (latitude IS NULL OR french_department IS NULL)
            AND COALESCE(location, '') != ''
            """,
            (pCountry,),
        ).fetchall()

    finally:
        vConnection.close()

    return rOffers


def save_offer_positions(pDatabaseFile, pPositions):
    """Enregistre la position des offres : (latitude, longitude, département, source, id)."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            "UPDATE job_offer SET latitude = ?, longitude = ?, french_department = ?"
            " WHERE source = ? AND source_id = ?",
            pPositions,
        )
        vConnection.commit()

    finally:
        vConnection.close()


def count_offer_positions(pDatabaseFile, pCountry):
    """Retourne le nombre d'offres du pays avec un lieu, et celles déjà placées."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vTotal, vPlaced = vConnection.execute(
            """
            SELECT COUNT(*), COUNT(latitude)
            FROM job_offer
            WHERE country = ? AND COALESCE(location, '') != ''
            """,
            (pCountry,),
        ).fetchone()

    finally:
        vConnection.close()

    rCounts = (vTotal, vPlaced)

    return rCounts
