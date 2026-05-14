"""直方图面板 —— 显示当前图像的灰度/各通道直方图。"""
import numpy as np
from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPaintEvent


_HIST_BG = QColor("#FFFFFF")
_HIST_GRID = QColor("#E0E0E0")
_CHANNEL_COLORS = [
    QColor(66, 133, 244, 180),   # Blue
    QColor(52, 168, 83, 180),    # Green
    QColor(234, 67, 53, 180),    # Red
    QColor("#666666"),            # Gray (single channel)
]
_CHANNEL_NAMES = ["Blue", "Green", "Red", "Gray"]


class _HistogramWidget(QWidget):
    """纯 QPainter 直方图绘制，无外部依赖。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bins = 256
        self._hist_data = {}  # channel_index -> histogram array
        self.setMinimumHeight(160)
        self.setStyleSheet("background: #FAFAFA;")

    def set_histogram(self, hist_data: dict):
        self._hist_data = hist_data
        self.update()

    def clear(self):
        self._hist_data.clear()
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 12

        painter.fillRect(QRectF(0, 0, w, h), _HIST_BG)

        plot_x = margin + 24
        plot_y = margin
        plot_w = w - plot_x - margin
        plot_h = h - margin * 2 - 16

        if plot_w <= 0 or plot_h <= 0:
            painter.end()
            return

        # 网格线
        pen = QPen(_HIST_GRID, 1)
        painter.setPen(pen)
        for i in range(5):
            y = plot_y + plot_h * i / 4
            painter.drawLine(int(plot_x), int(y), int(plot_x + plot_w), int(y))

        # 坐标轴
        painter.setPen(QPen(QColor("#999999"), 1))
        painter.drawLine(int(plot_x), int(plot_y), int(plot_x), int(plot_y + plot_h))
        painter.drawLine(int(plot_x), int(plot_y + plot_h), int(plot_x + plot_w), int(plot_y + plot_h))

        if not self._hist_data:
            painter.setPen(QColor("#999999"))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(
                int(plot_x + plot_w / 2 - 60), int(plot_y + plot_h / 2),
                "无直方图数据"
            )
            painter.end()
            return

        bar_w = max(1, plot_w / self._bins)

        global_max = 1
        for arr in self._hist_data.values():
            if len(arr) > 0:
                global_max = max(global_max, float(np.max(arr)))

        # 通道柱状图
        for ch_idx, arr in sorted(self._hist_data.items()):
            if len(arr) == 0:
                continue
            color = _CHANNEL_COLORS[min(ch_idx, len(_CHANNEL_COLORS) - 1)]
            painter.setPen(Qt.PenStyle.NoPen)

            for i in range(min(len(arr), self._bins)):
                bar_h = (arr[i] / global_max) * plot_h
                if bar_h < 0.5:
                    continue
                x = plot_x + i * bar_w
                y = plot_y + plot_h - bar_h
                painter.fillRect(QRectF(x, y, bar_w + 0.5, bar_h), color)

        # 图例
        legend_x = plot_x
        legend_y = plot_y + plot_h + 10
        painter.setFont(QFont("Consolas", 8))
        for ch_idx in sorted(self._hist_data.keys()):
            color = _CHANNEL_COLORS[min(ch_idx, len(_CHANNEL_COLORS) - 1)]
            name = _CHANNEL_NAMES[min(ch_idx, len(_CHANNEL_NAMES) - 1)]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRect(int(legend_x), int(legend_y), 10, 10)
            painter.setPen(QColor("#333333"))
            painter.drawText(int(legend_x + 14), int(legend_y + 9), name)
            legend_x += 60

        painter.end()


class HistogramPanel(QDockWidget):
    """可拖动的直方图面板。"""

    def __init__(self, parent=None):
        super().__init__("直方图", parent)
        self.setObjectName("histogram_panel")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.setMinimumWidth(280)
        self.setMinimumHeight(200)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        self._hist_widget = _HistogramWidget()
        layout.addWidget(self._hist_widget)

        self.setWidget(container)

    def set_image(self, cv_img: np.ndarray):
        """从 numpy 图像计算并显示直方图。"""
        if cv_img is None or cv_img.size == 0:
            self._hist_widget.clear()
            return

        hist_data = {}
        if cv_img.ndim == 2:
            hist_data[3] = _calc_hist(cv_img)
        elif cv_img.ndim == 3:
            for ch in range(cv_img.shape[2]):
                hist_data[ch] = _calc_hist(cv_img[:, :, ch])

        self._hist_widget.set_histogram(hist_data)

    def clear(self):
        self._hist_widget.clear()


def _calc_hist(channel: np.ndarray) -> np.ndarray:
    """计算单通道直方图（0-255 bins）。"""
    hist, _ = np.histogram(channel.ravel(), bins=256, range=(0, 256))
    return hist.astype(np.float64)
