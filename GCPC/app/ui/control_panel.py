# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Iterable

from PySide6 import QtCore, QtWidgets

from app.utils.camera import camera_index_options


class ControlPanel(QtWidgets.QWidget):
    """Always-on-top launcher panel for camera, hand control and settings."""

    settings_requested = QtCore.Signal()
    camera_index_changed = QtCore.Signal(int)
    camera_resolution_changed = QtCore.Signal(int, int)

    def __init__(
        self,
        default_camera_enabled: bool = False,
        default_hand_enabled: bool = False,
        default_camera_index: int = 0,
        default_resolution: tuple[int, int] = (640, 360),
        available_camera_indices: Iterable[int] = (),
        camera_device_names: Iterable[str] = (),
        last_working_camera_index: int | None = None,
    ):
        super().__init__(None, QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("GCPC Controls")
        self.hand_control_enabled = bool(default_hand_enabled)
        self.camera_enabled = bool(default_camera_enabled)
        self.available_camera_indices = tuple(int(index) for index in available_camera_indices)
        self.camera_device_names = tuple(str(name) for name in camera_device_names)
        self.last_working_camera_index = last_working_camera_index

        layout = QtWidgets.QVBoxLayout(self)
        self.hand_btn = QtWidgets.QPushButton(self._hand_label())
        self.hand_btn.setCheckable(True)
        self.hand_btn.setChecked(self.hand_control_enabled)
        self.hand_btn.clicked.connect(self._toggle_hand_control)

        self.camera_btn = QtWidgets.QPushButton(self._camera_label())
        self.camera_btn.setCheckable(True)
        self.camera_btn.setChecked(self.camera_enabled)
        self.camera_btn.clicked.connect(self._toggle_camera)

        self.camera_source_combo = QtWidgets.QComboBox(self)
        self.camera_source_combo.setToolTip("Camera source")
        self._populate_camera_source_combo(default_camera_index)
        self.camera_source_combo.currentIndexChanged.connect(
            self._emit_camera_index_changed
        )

        self.camera_resolution_combo = QtWidgets.QComboBox(self)
        selected_index = 0
        default_width = int(default_resolution[0])
        default_height = int(default_resolution[1])
        default_found = False
        for index, (text, width, height) in enumerate(self._resolution_options()):
            self.camera_resolution_combo.addItem(text, (width, height))
            if (int(width), int(height)) == (default_width, default_height):
                selected_index = index
                default_found = True
        if not default_found:
            selected_index = self.camera_resolution_combo.count()
            self.camera_resolution_combo.addItem(
                f"{default_width}x{default_height}",
                (default_width, default_height),
            )
        self.camera_resolution_combo.setCurrentIndex(selected_index)
        self.camera_resolution_combo.currentIndexChanged.connect(
            self._emit_camera_resolution_changed
        )

        self.settings_btn = QtWidgets.QPushButton("Gesture settings")
        self.settings_btn.clicked.connect(self.settings_requested.emit)

        camera_row = QtWidgets.QHBoxLayout()
        camera_row.addWidget(self.camera_btn, 1)
        camera_row.addWidget(self.camera_source_combo, 1)
        camera_row.addWidget(self.camera_resolution_combo, 1)

        layout.addWidget(self.hand_btn)
        layout.addLayout(camera_row)
        layout.addWidget(self.settings_btn)

    @staticmethod
    def _resolution_options():
        return [
            ("640x360", 640, 360),
            ("640x480", 640, 480),
            ("960x540", 960, 540),
            ("1280x720", 1280, 720),
            ("1920x1080", 1920, 1080),
        ]

    def _hand_label(self) -> str:
        return "Hand control: ON" if self.hand_control_enabled else "Hand control: OFF"

    def _camera_label(self) -> str:
        return "Camera: ON" if self.camera_enabled else "Camera: OFF"

    def _camera_source_label(self, index: int) -> str:
        if index == -1:
            return "Auto (-1)"
        name = (
            self.camera_device_names[index]
            if 0 <= index < len(self.camera_device_names)
            else ""
        )
        suffixes = []
        if index in self.available_camera_indices:
            suffixes.append("available")
        elif index == self.last_working_camera_index:
            suffixes.append("last working")
        else:
            suffixes.append("configured")
        suffix = f" ({', '.join(suffixes)})" if suffixes else ""
        if name:
            return f"{index}: {name}{suffix}"
        return f"OpenCV index {index}{suffix}"

    def _populate_camera_source_combo(self, selected_index: int) -> None:
        selected_index = int(selected_index)
        options = camera_index_options(
            selected_index,
            self.available_camera_indices,
            self.last_working_camera_index,
        )
        self.camera_source_combo.clear()
        selected_combo_index = 0
        for combo_index, camera_index in enumerate(options):
            self.camera_source_combo.addItem(
                self._camera_source_label(camera_index),
                camera_index,
            )
            if camera_index == selected_index:
                selected_combo_index = combo_index
        self.camera_source_combo.setCurrentIndex(selected_combo_index)

    def set_camera_index(
        self,
        index: int,
        available_camera_indices: Iterable[int] | None = None,
        camera_device_names: Iterable[str] | None = None,
        last_working_camera_index: int | None = None,
    ) -> None:
        if available_camera_indices is not None:
            self.available_camera_indices = tuple(
                int(camera_index) for camera_index in available_camera_indices
            )
        if camera_device_names is not None:
            self.camera_device_names = tuple(str(name) for name in camera_device_names)
        if last_working_camera_index is not None:
            self.last_working_camera_index = last_working_camera_index
        blocked = self.camera_source_combo.blockSignals(True)
        try:
            self._populate_camera_source_combo(int(index))
        finally:
            self.camera_source_combo.blockSignals(blocked)

    def _toggle_hand_control(self) -> None:
        self.hand_control_enabled = self.hand_btn.isChecked()
        self.hand_btn.setText(self._hand_label())

    def _toggle_camera(self) -> None:
        self.camera_enabled = self.camera_btn.isChecked()
        self.camera_btn.setText(self._camera_label())

    def current_interaction(self) -> str:
        return "gestures"

    def is_armed(self) -> bool:
        return True

    def is_hand_control_enabled(self) -> bool:
        return self.hand_control_enabled

    def is_camera_enabled(self) -> bool:
        return self.camera_enabled

    def selected_camera_index(self) -> int:
        data = self.camera_source_combo.currentData()
        try:
            return int(data)
        except (TypeError, ValueError):
            return 0

    def selected_camera_resolution(self) -> tuple[int, int]:
        data = self.camera_resolution_combo.currentData()
        if isinstance(data, tuple) and len(data) == 2:
            return int(data[0]), int(data[1])
        return 640, 360

    def _emit_camera_index_changed(self, _index: int) -> None:
        self.camera_index_changed.emit(self.selected_camera_index())

    def _emit_camera_resolution_changed(self, _index: int) -> None:
        width, height = self.selected_camera_resolution()
        self.camera_resolution_changed.emit(width, height)
