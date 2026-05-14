"""缩放/平移图像查看器，复用于双图对比和变量显示。"""
from typing import Optional

import numpy as np
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItemGroup,
    QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsLineItem,
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal, QLineF
from PyQt6.QtGui import QPixmap, QWheelEvent, QMouseEvent, QPainter, QImage, QPen, QColor


def cv2_to_qpixmap(cv_img: np.ndarray) -> QPixmap:
    """numpy 图像数组 → QPixmap，支持灰度和 BGR。"""
    if cv_img.ndim == 2:
        h, w = cv_img.shape
        qimg = QImage(cv_img.data, w, h, w, QImage.Format.Format_Grayscale8)
    else:
        h, w, ch = cv_img.shape
        qimg = QImage(cv_img.data, w, h, ch * w, QImage.Format.Format_BGR888)
    return QPixmap.fromImage(qimg)


class ImageCanvas(QGraphicsView):
    """可缩放/平移的图像查看器。"""

    zoom_updated = pyqtSignal(float, QPointF)
    pan_updated = pyqtSignal(QPointF)
    pixel_hovered = pyqtSignal(int, int, str)  # x, y, 颜色信息
    roi_created = pyqtSignal(str, tuple)  # (roi_type, params)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._source_pixmap: Optional[QPixmap] = None
        self._roi_mode: str = ""  # "" / "rect" / "circle" / "line"
        self._roi_start: Optional[QPointF] = None
        self._roi_item: Optional[QGraphicsItemGroup] = None

        self._zoom_factor = 1.15
        self._min_scale = 0.01
        self._max_scale = 20.0
        self._current_scale = 1.0

        self._panning = False
        self._pan_start = QPointF()

        self.setMouseTracking(True)

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    @property
    def scene(self) -> QGraphicsScene:
        return self._scene

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def set_image(self, pixmap: QPixmap):
        # 记住当前缩放/平移状态
        prev_had_image = self._pixmap_item is not None
        prev_scale = self._current_scale if prev_had_image else 0
        prev_center = self.scene_center() if prev_had_image else QPointF()

        self._source_pixmap = pixmap
        self._scene.clear()
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._scene.addItem(self._pixmap_item)
        self._scene.setSceneRect(QRectF(pixmap.rect()))

        if prev_had_image and prev_scale > 0.01:
            # 恢复之前的缩放和位置
            self._current_scale = 1.0
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            # 然后重新缩放到之前的 scale
            scale_factor = prev_scale / self._current_scale
            if scale_factor != 1.0:
                self._current_scale = prev_scale
                self.resetTransform()
                self.scale(prev_scale, prev_scale)
            # 尝试恢复到之前的中心
            self.centerOn(prev_center)
        else:
            self._current_scale = 1.0
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        QTimer.singleShot(0, self._emit_zoom_sync)

    def set_cv_image(self, cv_img: np.ndarray):
        """直接显示 numpy 图像数组（OpenCV 格式）。记住缩放状态。"""
        self.set_image(cv2_to_qpixmap(cv_img))

    # ------------------------------------------------------------------
    # ROI 绘制模式
    # ------------------------------------------------------------------
    def set_roi_mode(self, mode: str):
        """设置 ROI 绘制模式: '' / 'rect' / 'circle' / 'line'。"""
        self._roi_mode = mode
        if mode:
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def roi_mode(self) -> str:
        return self._roi_mode

    def clear_image(self):
        self._scene.clear()
        self._pixmap_item = None
        self._source_pixmap = None
        self._current_scale = 1.0

    def scene_center(self) -> QPointF:
        """可见区域中心（场景坐标）。"""
        return self.mapToScene(self.viewport().rect().center())

    def sync_pan(self, center_scene: QPointF):
        """外部同步平移。"""
        self.centerOn(center_scene)

    def center_on_bbox(self, x: int, y: int, w: int, h: int):
        """居中显示指定边界框。"""
        pad = max(w, h) * 0.3
        rect = QRectF(x - pad, y - pad, w + 2 * pad, h + 2 * pad)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._current_scale = self.transform().m11()
        QTimer.singleShot(0, self._emit_zoom_sync)

    def _apply_zoom_with_absolute(self, target_scale: float, center_scene: QPointF, *, emit: bool):
        """匹配绝对缩放比例（双视图同步时用）。"""
        if self._current_scale == 0:
            return
        factor = target_scale / self._current_scale
        self._apply_zoom(factor, center_scene, emit=emit)

    # ------------------------------------------------------------------
    # events
    # ------------------------------------------------------------------
    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = self._zoom_factor if delta > 0 else 1.0 / self._zoom_factor
        center_scene = self.mapToScene(event.position().toPoint())
        self._apply_zoom(factor, center_scene, emit=True)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._roi_mode:
                self._roi_start = self.mapToScene(event.pos().toPoint())
                self._roi_draw_start()
                return
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._roi_mode and self._roi_start:
            self._roi_draw_move(event)
            return
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            self.pan_updated.emit(self.scene_center())
        else:
            self._check_pixel_hover(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._roi_mode and self._roi_start:
                self._roi_draw_end()
                return
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def _check_pixel_hover(self, event: QMouseEvent):
        """检测鼠标下方的像素值并发出信号。"""
        if self._source_pixmap is None or self._pixmap_item is None:
            return
        scene_pos = self.mapToScene(event.pos().toPoint())
        x = int(scene_pos.x())
        y = int(scene_pos.y())
        pix_rect = self._source_pixmap.rect()
        if x < 0 or y < 0 or x >= pix_rect.width() or y >= pix_rect.height():
            return
        img = self._source_pixmap.toImage()
        color = img.pixelColor(x, y)
        r, g, b = color.red(), color.green(), color.blue()
        info = f"({x}, {y})  R:{r} G:{g} B:{b}"
        self.pixel_hovered.emit(x, y, info)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._emit_zoom_sync()

    # ------------------------------------------------------------------
    # ROI 绘制实现
    # ------------------------------------------------------------------
    def _roi_draw_start(self):
        pen = QPen(QColor("#FF0000"), 2, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        self._roi_item = None

        if self._roi_mode == "rect":
            item = QGraphicsRectItem()
            item.setPen(pen)
            item.setRect(QRectF(self._roi_start, self._roi_start))
            self._scene.addItem(item)
            self._roi_item = item
        elif self._roi_mode == "circle":
            item = QGraphicsEllipseItem()
            item.setPen(pen)
            item.setRect(QRectF(self._roi_start, self._roi_start))
            self._scene.addItem(item)
            self._roi_item = item
        elif self._roi_mode == "line":
            item = QGraphicsLineItem()
            item.setPen(pen)
            item.setLine(QLineF(self._roi_start, self._roi_start))
            self._scene.addItem(item)
            self._roi_item = item

    def _roi_draw_move(self, event: QMouseEvent):
        if not self._roi_item or not self._roi_start:
            return
        end = self.mapToScene(event.pos().toPoint())
        if self._roi_mode == "rect":
            rect = QRectF(self._roi_start, end).normalized()
            self._roi_item.setRect(rect)
        elif self._roi_mode == "circle":
            rect = QRectF(self._roi_start, end).normalized()
            self._roi_item.setRect(rect)
        elif self._roi_mode == "line":
            self._roi_item.setLine(QLineF(self._roi_start, end))

    def _roi_draw_end(self):
        end = self._roi_item.mapToScene(
            self._roi_item.boundingRect().center()
        ) if hasattr(self._roi_item, 'boundingRect') else QPointF()
        # 计算最终参数
        if self._roi_mode == "rect":
            rect = self._roi_item.rect()
            params = (int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()))
        elif self._roi_mode == "circle":
            rect = self._roi_item.rect()
            cx = int(rect.center().x())
            cy = int(rect.center().y())
            r = int(min(rect.width(), rect.height()) / 2)
            params = (cx, cy, r)
        elif self._roi_mode == "line":
            line = self._roi_item.line()
            params = (int(line.x1()), int(line.y1()), int(line.x2()), int(line.y2()))
        else:
            params = ()

        # 保留绘制结果在图上（改为实线，半透明填充）
        pen = QPen(QColor("#00FF00"), 2)
        pen.setCosmetic(True)
        self._roi_item.setPen(pen)

        self.roi_created.emit(self._roi_mode, params)
        self._roi_start = None
        self._roi_item = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _apply_zoom(self, factor: float, center_scene: QPointF, emit: bool):
        new_scale = self._current_scale * factor
        if new_scale < self._min_scale or new_scale > self._max_scale:
            return
        self._current_scale = new_scale
        self.scale(factor, factor)
        new_center_view = self.mapFromScene(center_scene)
        delta = self.viewport().rect().center() - new_center_view
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() - delta.x()
        )
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        if emit:
            self.zoom_updated.emit(self._current_scale, self.scene_center())

    def _emit_zoom_sync(self):
        """发出当前缩放状态以便同步。"""
        self.zoom_updated.emit(self._current_scale, self.scene_center())
