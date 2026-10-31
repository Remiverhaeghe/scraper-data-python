"""Tests de la carte schématique des employeurs"""

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from gui.employers_map import EmployersMap, place_employers, project

HOME = {"label": "Lille", "latitude": 50.63, "longitude": 3.06}
EMPLOYERS = [
    {
        "siren": "1",
        "name": "ROQUETTE FRERES",
        "sector": "Agroalimentaire",
        "city": "Lestrem",
        "distance_km": 28,
        "latitude": 50.63,
        "longitude": 2.66,
        "spontaneous": {"status_label": "Envoyée", "follow_up_due": True},
    },
    {
        "siren": "2",
        "name": "SANS POSITION",
        "latitude": None,
        "longitude": None,
    },
]


def test_points_are_placed_around_home_and_fit_the_widget():
    """Vérifie la projection en km, l'échelle et l'employeur sans position omis."""

    vEast, vNorth = project(HOME, 50.73, 3.06)
    vScale, vPoints = place_employers(HOME, EMPLOYERS, 400, 400)

    assert round(vEast) == 0 and round(vNorth) == 11
    assert len(vPoints) == 1
    assert vPoints[0][1] == 400 / 2 - 400 / 2 + 24
    assert vPoints[0][2] == 200
    assert round(vScale * 28.2) == 176


def mouse_event(pType, pX, pY):
    """Construit un événement de souris à une position de la carte."""

    rEvent = QMouseEvent(
        pType,
        QPointF(pX, pY),
        QPointF(pX, pY),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    return rEvent


def test_map_is_drawn_and_a_click_chooses_an_employer(qt_application):
    """Vérifie le dessin, le survol, le clic sur un point et le message sans domicile."""

    vMap = EmployersMap()
    vMap.resize(400, 400)
    vClicked = []
    vMap.employer_clicked.connect(vClicked.append)

    vMap.set_employers(None, EMPLOYERS)
    vMap.grab()

    assert vMap.points == []

    vMap.set_employers(HOME, EMPLOYERS)
    vMap.grab()
    _, vX, vY = vMap.points[0]

    vMap.mouseMoveEvent(mouse_event(QEvent.Type.MouseMove, vX, vY))
    vMap.mouseMoveEvent(mouse_event(QEvent.Type.MouseMove, 5, 5))
    vMap.mousePressEvent(mouse_event(QEvent.Type.MouseButtonPress, 5, 5))
    vMap.mousePressEvent(mouse_event(QEvent.Type.MouseButtonPress, vX + 3, vY))

    assert vClicked == ["1"]
    assert vMap.find_point(QPoint(200, 200)) is None
