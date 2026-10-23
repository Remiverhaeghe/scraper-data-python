"""Configuration commune des tests des outils de développement"""

import logging

import pytest


@pytest.fixture(autouse=True)
def restore_logging():
    """Rétablit les journaux coupés par python -m tools.quiz_lot.

    Sans cela, les tests suivants qui vérifient un message de journal
    échouent selon l'ordre d'exécution.
    """

    yield

    logging.disable(logging.NOTSET)
