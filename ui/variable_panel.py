"""变量面板 — 可拖动 QDockWidget，显示图像缩略图和控制变量。"""
from typing import Dict
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
    QSplitter, QListWidget, QListWidgetItem, QHBoxLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont

from ui.image_canvas import cv2_to_qpixmap


THUMB_MAX_W = 120
THUMB_MAX_H = 90


def _make_thumbnail(cv_img: np.ndarray) -> QPixmap:
    h, w = cv_img.shape[:2]
    scale = min(THUMB_MAX_W / w, THUMB_MAX_H / h, 1.0)
    if scale < 1.0:
        thumb = cv2.resize(cv_img, (int(w * scale), int(h * scale)))
    else:
        thumb = cv_img
    return cv2_to_qpixmap(thumb)


class ImageVarEntry(QFrame):
    """图像变量条目：缩略图 + 名称 + 尺寸/类型信息。"""

    clicked = pyqtSignal(str, np.ndarray)
    double_clicked = pyqtSignal(str, np.ndarray)

    def __init__(self, name: str, cv_img: np.ndarray, parent=None):
        super().__init__(parent)
        self._name = name
        self._cv_img = cv_img

        self.setFrameStyle(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(THUMB_MAX_H + 12)

        hlay = QHBoxLayout(self)
        hlay.setContentsMargins(4, 4, 4, 4)
        hlay.setSpacing(6)

        self._thumb_label = QLabel()
        pix = _make_thumbnail(cv_img)
        self._thumb_label.setPixmap(pix)
        self._thumb_label.setFixedSize(pix.width(), pix.height())
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hlay.addWidget(self._thumb_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self._name_label = QLabel(name)
        font = QFont()
        font.setBold(True)
        self._name_label.setFont(font)

        h, w = cv_img.shape[:2]
        ch = cv_img.shape[2] if cv_img.ndim == 3 else 1
        dtype_str = str(cv_img.dtype)
        self._info_label = QLabel(f"({w}x{h})  {ch}-channel {dtype_str}")
        self._info_label.setStyleSheet("color: #666; font-size: 11px;")

        info_layout.addWidget(self._name_label)
        info_layout.addWidget(self._info_label)
        hlay.addLayout(info_layout)
        hlay.addStretch()

        self._set_style(False)

    def _set_style(self, selected: bool):
        if selected:
            self.setStyleSheet(
                "ImageVarEntry { border: 2px solid #1976D2; background: #E3F2FD; }"
            )
        else:
            self.setStyleSheet(
                "ImageVarEntry { border: 1px solid #ddd; background: #FAFAFA; }"
            )

    def mousePressEvent(self, event):
        self.clicked.emit(self._name, self._cv_img)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self._name, self._cv_img)
        super().mouseDoubleClickEvent(event)


class VariablePanel(QDockWidget):
    """可拖动的变量面板：图像缩略图（上）+ 控制变量（下）。"""

    image_selected = pyqtSignal(str, np.ndarray)
    image_double_clicked = pyqtSignal(str, np.ndarray)

    def __init__(self, parent=None):
        super().__init__("变量窗口", parent)
        self.setObjectName("variable_panel")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.setMinimumWidth(220)

        self._image_entries: Dict[str, ImageVarEntry] = {}

        # 内容容器
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # 上半：图像变量
        image_container = QWidget()
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("图像变量")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        image_layout.addWidget(title)

        self._image_scroll = QScrollArea()
        self._image_scroll.setWidgetResizable(True)
        self._image_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._image_list_widget = QWidget()
        self._image_list_layout = QVBoxLayout(self._image_list_widget)
        self._image_list_layout.setContentsMargins(0, 0, 0, 0)
        self._image_list_layout.setSpacing(4)
        self._image_list_layout.addStretch()

        self._image_scroll.setWidget(self._image_list_widget)
        image_layout.addWidget(self._image_scroll)
        splitter.addWidget(image_container)

        # 中部：控制变量
        ctrl_container = QWidget()
        ctrl_layout = QVBoxLayout(ctrl_container)
        ctrl_layout.setContentsMargins(4, 4, 4, 4)

        ctrl_title = QLabel("控制变量")
        ctrl_title.setFont(title_font)
        ctrl_layout.addWidget(ctrl_title)

        self._ctrl_list = QListWidget()
        self._ctrl_list.setAlternatingRowColors(True)
        ctrl_layout.addWidget(self._ctrl_list)

        splitter.addWidget(ctrl_container)

        # 下部：输出 (print 内容)
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(4, 4, 4, 4)

        output_title = QLabel("输出")
        output_title.setFont(title_font)
        output_layout.addWidget(output_title)

        from PyQt6.QtWidgets import QPlainTextEdit
        self._output_text = QPlainTextEdit()
        self._output_text.setReadOnly(True)
        self._output_text.setMaximumBlockCount(200)
        self._output_text.setFont(QFont("Consolas", 9))
        self._output_text.setStyleSheet("background: #F5F5F5;")
        self._output_text.setPlaceholderText("print() 输出将显示在这里…")
        output_layout.addWidget(self._output_text)

        splitter.addWidget(output_container)
        splitter.setStretchFactor(0, 45)
        splitter.setStretchFactor(1, 25)
        splitter.setStretchFactor(2, 30)

        layout.addWidget(splitter)
        self.setWidget(container)

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def refresh(self, variables: dict):
        image_vars = {}
        control_vars = {}

        for name, val in variables.items():
            if name.startswith('__') and name.endswith('__'):
                continue
            if name in ('cv2', 'np'):
                continue
            if isinstance(val, np.ndarray):
                image_vars[name] = val
            elif callable(val):
                continue
            elif hasattr(val, '__module__'):
                continue
            else:
                control_vars[name] = val

        self._update_image_vars(image_vars)
        self._update_control_vars(control_vars)

    def _update_image_vars(self, image_vars: dict):
        removed = set(self._image_entries.keys()) - set(image_vars.keys())
        for name in removed:
            entry = self._image_entries.pop(name)
            self._image_list_layout.removeWidget(entry)
            entry.deleteLater()

        for name, cv_img in image_vars.items():
            if name not in self._image_entries:
                entry = ImageVarEntry(name, cv_img)
                entry.clicked.connect(self._on_image_clicked)
                entry.double_clicked.connect(self._on_image_double_clicked)
                n = self._image_list_layout.count()
                self._image_list_layout.insertWidget(n - 1, entry)
                self._image_entries[name] = entry

    def _update_control_vars(self, control_vars: dict):
        self._ctrl_list.clear()
        if not control_vars:
            item = QListWidgetItem("（无 — 脚本中未定义标量变量）")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(Qt.GlobalColor.gray)
            self._ctrl_list.addItem(item)
            return
        for name, val in control_vars.items():
            val_str = str(val)
            if len(val_str) > 60:
                val_str = val_str[:57] + "..."
            item = QListWidgetItem(f"{name}  =  {val_str}")
            item.setToolTip(f"{name} = {val}")
            self._ctrl_list.addItem(item)

    def clear(self):
        for entry in self._image_entries.values():
            self._image_list_layout.removeWidget(entry)
            entry.deleteLater()
        self._image_entries.clear()
        self._ctrl_list.clear()
        self._output_text.clear()

    def append_output(self, text: str):
        """追加一行输出文本。"""
        self._output_text.appendPlainText(text.rstrip())

    def _on_image_clicked(self, name: str, cv_img: np.ndarray):
        self.image_selected.emit(name, cv_img)

    def _on_image_double_clicked(self, name: str, cv_img: np.ndarray):
        self.image_double_clicked.emit(name, cv_img)
