import time
import os, sys

# Change the current dir to the temporary one created by PyInstaller
try:
    os.chdir(sys._MEIPASS)
    print(sys._MEIPASS)
except:
    pass

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import *
from PyQt5 import uic
from EyeReader import EyeReader
from BlinkTimer import BlinkTimer
from BreakTimer import BreakTimer
from EyeFrameAnalyzer import EyeFrameAnalyzer
from datetime import timedelta
import icons
import sfx
import sys
import numpy as np
import random
import traceback


class ProxyWidget(QWidget):
    def __init__(self, name):
        super(ProxyWidget, self).__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.oldPos = self.pos()
        uic.loadUi(name + ".ui", self)

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.pos() + delta)
        self.oldPos = event.globalPos()


class BlinkWellWidget(QWidget):
    def __init__(self, app, name):
        super(BlinkWellWidget, self).__init__()
        self.app = app
        self.name = name
        self.old_visibility = False
        self.settings = QSettings("BlinkWell", "BlinkWellApp")

        uic.loadUi(name + ".ui", self)
        self.set_effect()

        if not self.settings.contains(self.name + "_geometry"):
            self.set_default_geometry()
            self.settings.setValue(self.name + "_geometry", self.saveGeometry())

        geometry = self.settings.value(self.name + "_geometry")
        self.restoreGeometry(geometry)

        self.proxy = ProxyWidget(name)

    def set_default_geometry(self):
        self.move(QApplication.desktop().screen().rect().center() - self.rect().center())

    def restore_default_geometry(self):
        self.set_default_geometry()
        self.proxy.setGeometry(self.geometry())
        self.settings.setValue(self.name + "_geometry", self.saveGeometry())

    def enable_drag(self):
        self.old_visibility = self.isVisible()
        self.hide()
        self.proxy.show()
        self.proxy.setGeometry(self.geometry())

    def disable_drag(self):
        self.settings.setValue(self.name + "_geometry", self.proxy.saveGeometry())
        self.setGeometry(self.proxy.geometry())
        self.setVisible(self.old_visibility)
        self.proxy.hide()

    def set_effect(self):
        effect = QGraphicsDropShadowEffect(color=QColor("#222"))
        effect.setBlurRadius(15)
        effect.setOffset(QPoint(0, 0))
        self.setGraphicsEffect(effect)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, icon, main_window):
        super(TrayIcon, self).__init__()

        self.main_window = main_window

        menu = QMenu()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(lambda: sys.exit())

        self.setContextMenu(menu)
        self.setIcon(icon)
        self.activated.connect(self.on_clicked)
        self.show()

    def on_clicked(self, reason):
        if reason == self.ActivationReason.Trigger:
            self.main_window.showMinimized()
            self.main_window.show()
            self.main_window.setWindowState(Qt.WindowActive)


class SettingsPage(QWidget):
    def __init__(self, app):
        super(SettingsPage, self).__init__()
        uic.loadUi("settings_page.ui", self)
        self.app = app
        self.settings = QSettings("BlinkWell", "BlinkWellApp")

        self.setup_slider("ear_threshold")
        self.setup_slider("target_blink_rate")
        self.setup_slider("blink_reminder_rigidness")
        self.setup_slider("session_duration")
        self.setup_slider("snooze_duration")
        self.setup_slider("break_duration")

        self.setup_toggle("blink_reminder_toggle", self.app.blink_reminder_toggle_signal)
        self.setup_toggle("break_reminder_toggle", self.app.break_reminder_toggle_signal)
        self.setup_toggle("stats_overlay_toggle", self.app.stats_overlay_toggle_signal)

        self.move_ui_button = self.findChild(QPushButton, "move_ui_button")
        self.move_ui_button.toggled.connect(self.on_move_ui_toggle)
        self.reset_geometry_button = self.findChild(QPushButton, "reset_geometry_button")
        self.reset_geometry_button.clicked.connect(self.app.restore_default_geometry)
        self.reset_settings_button = self.findChild(QPushButton, "reset_settings_button")
        self.reset_settings_button.clicked.connect(self.app.restore_default_settings)

    def on_move_ui_toggle(self):
        if self.move_ui_button.isChecked():
            self.app.move_ui_start()
        else:
            self.app.move_ui_stop()

    def setup_toggle(self, name, signal):
        toggle: QToolButton = self.findChild(QToolButton, name)
        toggle.toggled.connect(lambda: self.on_toggle(name, signal, toggle))

        toggle.setChecked(self.settings.value(name, type=bool))
        self.on_toggle(name, signal, toggle)

    def on_toggle(self, name, signal, toggle):
        enabled = toggle.isChecked()
        self.settings.setValue(name, enabled)
        signal.emit(enabled)

    def setup_slider(self, name):
        label: QLabel = self.findChild(QLabel, name + "_label")
        slider: QSlider = self.findChild(QSlider, name + "_slider")
        slider.valueChanged.connect(lambda: self.on_slider_value_changed(name, slider, label))
        slider.setValue(int(self.settings.value(name)))
        label.setText(str(int(self.settings.value(name))))
        self.app.restore_settings_signal.connect(lambda: self.update_slider(name, slider))

    def update_slider(self, name, slider):
        slider.setValue(int(self.settings.value(name)))

    def on_slider_value_changed(self, name, slider, label):
        self.settings.setValue(name, slider.value())
        label.setText(str(slider.value()))


class DebugPage(QWidget):
    def __init__(self, app):
        super(DebugPage, self).__init__()
        uic.loadUi("debug_page.ui", self)
        self.app = app
        self.camera_feed_label = self.findChild(QLabel, "camera_feed_label")
        self.app.update_camera_feed_signal.connect(self.update_camera_feed)

    def update_camera_feed(self, image):
        qt_img = self.convert_cv_qt(image)
        self.camera_feed_label.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        h, w, ch = cv_img.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(cv_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(600, 600, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)


class HomePage(QWidget):
    def __init__(self, app):
        super(HomePage, self).__init__()
        uic.loadUi("home_page.ui", self)
        self.app = app


class MainWindow(BlinkWellWidget):
    def __init__(self, app):
        super(MainWindow, self).__init__(app, "main_window")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.stackedWidget = self.findChild(QStackedWidget, "stackedWidget")
        self.home_page = HomePage(app)
        self.debug_page = DebugPage(app)
        self.settings_page = SettingsPage(app)

        self.stackedWidget.addWidget(self.home_page)
        self.stackedWidget.addWidget(self.debug_page)
        self.stackedWidget.addWidget(self.settings_page)

        self.home_button = self.findChild(QPushButton, "home_button")
        self.debug_button = self.findChild(QPushButton, "debug_button")
        self.settings_button = self.findChild(QPushButton, "settings_button")

        self.home_button.pressed.connect(lambda: self.stackedWidget.setCurrentIndex(0))
        self.debug_button.pressed.connect(lambda: self.stackedWidget.setCurrentIndex(1))
        self.settings_button.pressed.connect(lambda: self.stackedWidget.setCurrentIndex(2))

        self.findChild(QPushButton, "minimize_button").clicked.connect(self.hide)



class BlinkReminderWindow(BlinkWellWidget):
    def __init__(self, app):
        super(BlinkReminderWindow, self).__init__(app, "blink_reminder_window")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.toggle_enabled = True

        self.blink_button = self.findChild(QPushButton, "blink_button")
        app.start_blink_reminder_signal.connect(self.start)
        app.stop_blink_reminder_signal.connect(self.stop)
        app.blink_reminder_toggle_signal.connect(self.on_toggle)

    def on_toggle(self, enabled):
        self.toggle_enabled = enabled

    def start(self):
        if self.toggle_enabled:
            self.show()
            QTimer.singleShot(150, lambda: self.blink_button.setChecked(False))
            QTimer.singleShot(300, lambda: self.blink_button.setChecked(True))
            QTimer.singleShot(500, lambda: self.blink_button.setChecked(False))
            QTimer.singleShot(700, lambda: self.blink_button.setChecked(True))
            QTimer.singleShot(1200, lambda: self.blink_button.setChecked(False))
            QTimer.singleShot(1350, lambda: self.blink_button.setChecked(True))
            QTimer.singleShot(2200, lambda: self.blink_button.setChecked(False))
            QTimer.singleShot(2350, lambda: self.blink_button.setChecked(True))

    def stop(self):
        self.hide()


class BreakReminderWindow(BlinkWellWidget):
    def __init__(self, app):
        super(BreakReminderWindow, self).__init__(app, "break_reminder_window")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.screen_time_label: QLabel = self.findChild(QLabel, 'screen_time_label')
        self.start_button: QPushButton = self.findChild(QPushButton, 'start_button')
        self.snooze_button: QPushButton = self.findChild(QPushButton, 'snooze_button')
        self.skip_button: QPushButton = self.findChild(QPushButton, 'skip_button')

        self.start_button.clicked.connect(self.on_start_button)
        self.snooze_button.clicked.connect(self.on_snooze_button)
        self.skip_button.clicked.connect(self.on_skip_button)

        self.app.start_break_signal.connect(self.on_break_start)
        self.app.update_session_time_signal.connect(self.update_screen_time)
        self.app.start_break_reminder_signal.connect(self.start)

        self.setup_notification_sounds()

    def start(self):
        self.show()
        self.start_button.show()
        self.play_random_notification_sound()

    def update_screen_time(self, screen_time):
        self.screen_time_label.setText(str(timedelta(seconds=screen_time)))

    def on_start_button(self):
        self.app.start_break_signal.emit()

    def on_snooze_button(self):
        self.app.snooze_break_signal.emit()
        self.app.finish_break_reminder_signal.emit()
        self.hide()

    def on_skip_button(self):
        self.app.skip_break_signal.emit()
        self.app.finish_break_reminder_signal.emit()
        self.hide()

    def on_break_start(self):
        self.app.finish_break_reminder_signal.emit()
        self.hide()

    def set_default_geometry(self):
        position = QPoint(int(QApplication.desktop().availableGeometry().center().x() - self.width() / 2), 0)
        self.move(position)

    def setup_notification_sounds(self):
        self.notification_sounds = []

        paths = [
            ":sfx/long_1.wav",
            ":sfx/long_2.wav",
            ":sfx/long_3.wav",
            ":sfx/long_4.wav",
            ":sfx/long_5.wav",
            ":sfx/long_6.wav"
        ]

        for path in paths:
            sfx = QSoundEffect()
            sfx.setSource(QUrl.fromLocalFile(path))
            self.notification_sounds.append(sfx)

    def play_random_notification_sound(self):
        random_index = random.randint(0, len(self.notification_sounds) - 1)
        self.notification_sounds[random_index].play()


class BreakWindow(BlinkWellWidget):
    def __init__(self, app):
        super(BreakWindow, self).__init__(app, "break_window")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        effect = QGraphicsDropShadowEffect(offset=QPoint(0, 0), blurRadius=12, color=QColor("#222"))
        self.setGraphicsEffect(effect)

        self.unlocked = False
        self.progress_bar_steps = 100000

        self.progress_bar: QProgressBar = self.findChild(QProgressBar, 'progressBar')
        self.quit_button: QPushButton = self.findChild(QPushButton, 'quit_button')
        self.quit_button.clicked.connect(self.stop)

        self.app.start_break_signal.connect(self.start)
        self.app.unlock_break_signal.connect(self.unlock)
        self.app.update_break_duration_signal.connect(self.update_elapsed_time)

        self.app.update_finished_session_duration.connect(self.update_session_duration)
        self.app.update_finished_session_blink_rate.connect(self.update_session_blink_rate)

        self.blinks_per_minute_label: QLabel = self.findChild(QLabel, "blinks_per_minute")
        self.minutes_on_screen_label: QLabel = self.findChild(QLabel, "minutes_on_screen")
        self.minutes_on_break_label: QLabel = self.findChild(QLabel, "minutes_on_break")

        self.setup_notification_sounds()

    def unlock(self):
        self.quit_button.setEnabled(True)
        self.unlocked = True
        self.progress_bar.setValue(int(self.progress_bar_steps))
        self.play_random_notification_sound()

    def update_session_blink_rate(self, blink_rate):
        self.blinks_per_minute_label.setText(str(int(blink_rate)))
        self.blinks_per_minute_label.update()

    def update_session_duration(self, duration):
        self.minutes_on_screen_label.setText(str(int(duration/60)))
        self.minutes_on_screen_label.update()

    def update_elapsed_time(self, duration, percentage):
        self.minutes_on_break_label.setText(str(int(duration/60)))
        self.minutes_on_break_label.update()

        if self.unlocked:
            return

        self.progress_bar.setValue(int(percentage * self.progress_bar_steps))
        self.progress_bar.update()

    def start(self):
        self.unlocked = False
        self.quit_button.setEnabled(False)
        self.minutes_on_break_label.setText("0")
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, self.progress_bar_steps)
        self.quit_button.update()

        QTimer.singleShot(50, self.show)

    def stop(self):
        self.hide()
        self.app.finish_break_signal.emit()

    def setup_notification_sounds(self):
        self.notification_sounds = []

        paths = [
            ":sfx/short_1.wav",
            ":sfx/short_2.wav"
        ]

        for path in paths:
            sfx = QSoundEffect()
            sfx.setSource(QUrl.fromLocalFile(path))
            self.notification_sounds.append(sfx)

    def play_random_notification_sound(self):
        random_index = random.randint(0, len(self.notification_sounds) - 1)
        self.notification_sounds[random_index].play()


class StatsOverlayWindow(BlinkWellWidget):
    def __init__(self, app):
        super(StatsOverlayWindow, self).__init__(app, "stats_overlay_window")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.blink_rate_label: QLabel = self.findChild(QLabel, 'blink_rate_label')
        self.screen_time_label: QLabel = self.findChild(QLabel, 'screen_time_label')

        app.update_blink_rate_signal.connect(self.update_blink_rate)
        app.update_session_time_signal.connect(self.update_screen_time)
        app.stats_overlay_toggle_signal.connect(self.on_toggle)


    def on_toggle(self, enabled):
        self.setVisible(enabled)

    def update_blink_rate(self, rate_short, rate_long):
        self.blink_rate_label.setText(str(rate_short))

    def update_screen_time(self, screen_time):
        self.screen_time_label.setText(str(timedelta(seconds=screen_time)))

    def set_default_geometry(self):
        position = QApplication.desktop().availableGeometry().topLeft() + QPoint(0, 103)
        self.move(position)


class WorkerThread(QThread):
    def __init__(self, app):
        super(WorkerThread, self).__init__()
        self.settings = QSettings("BlinkWell", "BlinkWellApp")
        self.blink_timer = BlinkTimer(app, self)
        self.break_timer = BreakTimer(app, self)
        self.eye_reader = EyeReader(app, self)
        self.frame_analyzer = EyeFrameAnalyzer(app, self)
        self.start()

    def get_setting(self, name):
        return float(self.settings.value(name))


    def run(self):
        while True:
            frame_data = self.eye_reader.process_frame()
            if not frame_data.success:
                continue
            self.frame_analyzer.tick(frame_data)
            self.blink_timer.tick(frame_data)
            self.break_timer.tick(frame_data)

    def update_blink_rate(self, rate_short, rate_long):
        self.update_blink_rate_signal.emit(rate_short, rate_long)


class BlinkWellApp(QApplication):
    start_blink_reminder_signal = pyqtSignal()
    stop_blink_reminder_signal = pyqtSignal()

    update_blink_rate_signal = pyqtSignal(int, int)
    update_session_time_signal = pyqtSignal(int)
    update_break_duration_signal = pyqtSignal(float, float)

    update_finished_session_blink_rate = pyqtSignal(int)
    update_finished_session_duration = pyqtSignal(int)

    start_break_reminder_signal = pyqtSignal()
    finish_break_reminder_signal = pyqtSignal()

    start_break_signal = pyqtSignal()
    snooze_break_signal = pyqtSignal()
    skip_break_signal = pyqtSignal()
    finish_break_signal = pyqtSignal()
    unlock_break_signal = pyqtSignal()

    blink_reminder_toggle_signal = pyqtSignal(bool)
    break_reminder_toggle_signal = pyqtSignal(bool)
    stats_overlay_toggle_signal = pyqtSignal(bool)

    restore_settings_signal = pyqtSignal()

    update_camera_feed_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super(BlinkWellApp, self).__init__([])
        self.setQuitOnLastWindowClosed(False)

        self.settings = QSettings("BlinkWell", "BlinkWellApp")
        self.populate_default_settings()

        self.blink_reminder_window = BlinkReminderWindow(self)
        self.break_reminder_window = BreakReminderWindow(self)
        self.break_window = BreakWindow(self)
        self.stats_overlay_window = StatsOverlayWindow(self)
        self.worker_thread = WorkerThread(self)
        self.main_window = MainWindow(self)

        self.tray_icon = TrayIcon(QIcon(":icons/logo_icon2.png"), self.main_window)

    def restore_default_settings(self):
        self.set_settings_default(True)
        self.restore_settings_signal.emit()

    def populate_default_settings(self):
        self.set_settings_default(False)

    def set_settings_default(self, override):
        self.try_set_default_setting("ear_threshold", 23, override)
        self.try_set_default_setting("target_blink_rate", 20, override)
        self.try_set_default_setting("blink_reminder_rigidness", 50, override)
        self.try_set_default_setting("session_duration", 20, override)
        self.try_set_default_setting("snooze_duration", 2, override)
        self.try_set_default_setting("break_duration", 20, override)
        self.try_set_default_setting("blink_reminder_toggle", True, override)
        self.try_set_default_setting("break_reminder_toggle", True, override)
        self.try_set_default_setting("stats_overlay_toggle", True, override)

    def try_set_default_setting(self, name, value, override):
        if override or not self.settings.contains(name):
            self.settings.setValue(name, value)

    def restore_default_geometry(self):
        self.blink_reminder_window.restore_default_geometry()
        self.break_reminder_window.restore_default_geometry()
        self.break_window.restore_default_geometry()
        self.stats_overlay_window.restore_default_geometry()

    def move_ui_start(self):
        self.break_window.enable_drag()
        self.break_reminder_window.enable_drag()
        self.blink_reminder_window.enable_drag()
        self.stats_overlay_window.enable_drag()

    def move_ui_stop(self):
        self.blink_reminder_window.disable_drag()
        self.break_reminder_window.disable_drag()
        self.break_window.disable_drag()
        self.stats_overlay_window.disable_drag()

def main():
    app = BlinkWellApp()
    app.exec()





if __name__ == '__main__':
    main()
