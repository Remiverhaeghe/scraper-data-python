"""Réponses HTTP simulées pour les tests des clients d'API"""

import json


class FakeJsonResponse:
    """Base des réponses simulées : adapte une méthode json() au flux lu par request_json.

    Les classes de test définissent json() et, si besoin, raise_for_status().
    """

    is_redirect = False

    status_code = 200

    headers = {"Content-Type": "application/json"}

    def raise_for_status(self):
        """Ne lève rien : réponse en succès par défaut."""

    def iter_content(self, chunk_size):
        """Restitue les données de json() comme le ferait un flux HTTP."""
        try:
            vData = self.json()

        except ValueError:
            yield b"<html>Pas du JSON</html>"

        else:
            yield json.dumps(vData).encode("utf-8")

    def close(self):
        """Rien à libérer pour une réponse simulée."""
