import os, sys
sys.path.insert(0, ".")
from PySide6.QtWidgets import QApplication, QScrollArea
import config
from gui.theme import apply_theme
from gui.main_window import MainWindow
vApp = QApplication(sys.argv); vApp.setStyle("Fusion")
apply_theme(vApp, "light", 100)
vWindow = MainWindow(config.DATABASE_FILE, "t"); vWindow.resize(1600, 1000); vWindow.show()
vWindow.navigate("settings"); vApp.processEvents()
def report(pLabel):
    for vArea in vWindow.pages.currentWidget().findChildren(QScrollArea):
        vBar = vArea.horizontalScrollBar()
        print(pLabel, "barre visible :", vBar.isVisible(), "max :", vBar.maximum(), "contenu :", vArea.widget().width(), "zone :", vArea.viewport().width())
report("avant")
vWindow.rebuild("settings", lambda: apply_theme(vApp, "dark", 115)); vApp.processEvents()
report("après")
vApp.processEvents(); report("après 2")
os._exit(0)
