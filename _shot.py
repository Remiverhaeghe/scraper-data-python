import os, sys
sys.path.insert(0, ".")
from PySide6.QtWidgets import QApplication
from gui.theme import apply_theme
from gui.main_window import MainWindow
from gui.progress_widgets import CelebrationOverlay, show_xp_gain
vApp = QApplication(sys.argv); vApp.setStyle("Fusion")
apply_theme(vApp, sys.argv[3], 100)
vWindow = MainWindow(sys.argv[2], "JobBoard Perso"); vWindow.resize(1600, 1000); vWindow.show()
vApp.processEvents(); vWindow.check_progress()
vWindow.navigate("progress"); vApp.processEvents()
vWindow.grab().save(sys.argv[1] + "/progress_" + sys.argv[3] + ".png")
show_xp_gain(vWindow, vWindow.progress_box, "+25 XP")
o = CelebrationOverlay(vWindow, "Niveau 3", "Technicien", "Prochain titre : Technicien confirmé")
import time
t = time.time()
while time.time() - t < 0.9: vApp.processEvents(); time.sleep(0.016)
vWindow.grab().save(sys.argv[1] + "/celebration_" + sys.argv[3] + ".png")
os._exit(0)
