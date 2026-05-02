# -*- coding: utf-8 -*-
import ctypes

from PySide6 import QtWidgets, QtCore, QtGui

WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020


class OSD(QtWidgets.QWidget):
    """On-screen display widget showing current mode and hints."""
    def __init__(self):
        super().__init__(None, QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowFlag(QtCore.Qt.WindowDoesNotAcceptFocus, True)
        self.text_main = ""
        self.text_sub = ""
        self.exit_progress = None
        self.font_main = QtGui.QFont("Segoe UI", 12, QtGui.QFont.Bold)
        self.font_sub = QtGui.QFont("Segoe UI", 10)
        self.font_progress = QtGui.QFont("Segoe UI", 7, QtGui.QFont.Bold)
        self._install_click_through()
        self._resize_top()
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    def _install_click_through(self):
        """Allow mouse clicks to pass through the widget."""
        hwnd = int(self.winId())
        GWL_EXSTYLE = -20
        GetWindowLong = ctypes.windll.user32.GetWindowLongW
        SetWindowLong = ctypes.windll.user32.SetWindowLongW
        ex = GetWindowLong(hwnd, GWL_EXSTYLE)
        SetWindowLong(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED | WS_EX_TRANSPARENT)

    def _resize_top(self):
        """Stretch the overlay across the top of the primary screen."""
        scr = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.setGeometry(scr.left(), scr.top(), round(scr.width() / 3), 52)

    def set_text(self, main, sub=""):
        """Update displayed main and secondary text."""
        self.text_main = main or ""
        self.text_sub = sub or ""
        self.update()

    def set_exit_progress(self, progress):
        """Show or hide the mode-exit hold progress ring."""
        if progress is None:
            self.exit_progress = None
        else:
            self.exit_progress = max(0.0, min(1.0, float(progress)))
        self.update()

    def paintEvent(self, e):
        """Render overlay background and text."""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self.rect()
        p.fillRect(r, QtGui.QColor(0, 0, 0, 120))
        pen = QtGui.QPen(QtGui.QColor(80, 200, 255, 180))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawRect(r.adjusted(1, 1, -2, -2))
        text_right_padding = 72 if self.exit_progress is not None else 12
        p.setPen(QtGui.QColor(230, 255, 255))
        p.setFont(self.font_main)
        p.drawText(
            r.adjusted(12, 8, -text_right_padding, -8),
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            self.text_main,
        )
        p.setFont(self.font_sub)
        p.setPen(QtGui.QColor(180, 235, 235))
        p.drawText(
            r.adjusted(12, 26, -text_right_padding, -8),
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            self.text_sub,
        )
        if self.exit_progress is not None:
            self._draw_exit_progress(p, r)

    def _draw_exit_progress(self, painter, bounds):
        progress = max(0.0, min(1.0, float(self.exit_progress or 0.0)))
        diameter = 34
        margin = 9
        rect = QtCore.QRectF(
            bounds.right() - diameter - margin,
            bounds.center().y() - diameter / 2,
            diameter,
            diameter,
        )
        track_pen = QtGui.QPen(QtGui.QColor(80, 110, 120, 190))
        track_pen.setWidth(4)
        track_pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        progress_pen = QtGui.QPen(QtGui.QColor(90, 230, 255, 235))
        progress_pen.setWidth(4)
        progress_pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(progress_pen)
        painter.drawArc(rect, 90 * 16, -int(360 * 16 * progress))

        painter.setPen(QtGui.QColor(230, 255, 255))
        painter.setFont(self.font_progress)
        painter.drawText(rect, QtCore.Qt.AlignCenter, f"{round(progress * 100):d}%")

    def showEvent(self, e):
        """Ensure overlay is resized when shown."""
        super().showEvent(e)
        self._resize_top()
