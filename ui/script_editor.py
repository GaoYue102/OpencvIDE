"""脚本编辑器 —— 带行号栏、执行行高亮、只读切换。"""
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QTextFormat, QFont, QPolygonF
from PyQt6.QtCore import QPointF


# 预置示例脚本
DEFAULT_SCRIPT = r"""# OpenCV IDE — 交互式视觉编程
# F6 单步执行，F5 运行全部，Esc 停止
import cv2
import numpy as np

# === 参数区（控制变量窗口会显示这些变量） ===
blur_ksize = (5, 5)       # 高斯模糊核大小
canny_low = 100            # Canny 低阈值
canny_high = 200           # Canny 高阈值

# === 图像处理流程 ===
img = cv2.imread(r"photo.jpg")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

blur = cv2.GaussianBlur(gray, blur_ksize, 0)

edges = cv2.Canny(blur, canny_low, canny_high)
print(f"edges: {edges.shape}, dtype={edges.dtype}")
"""


class LineNumberArea(QWidget):
    """行号栏，绘制在编辑器左侧。可点击定位。"""

    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return self._editor._line_number_area_size()

    def paintEvent(self, event):
        self._editor._line_number_area_paint(event)

    def mousePressEvent(self, event):
        line_no = self._editor._line_at_y(event.pos().y())
        if line_no > 0:
            self._editor._on_line_number_clicked(line_no)
        super().mousePressEvent(event)


class ScriptEditor(QPlainTextEdit):
    """带行号栏、执行高亮的代码编辑器。"""

    script_modified = pyqtSignal(str)
    line_clicked = pyqtSignal(int)  # 点击行号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)
        self._current_line: int = -1
        self._error_line: int = -1
        self._target_line: int = -1
        self._script_dirty = False

        # 字体
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(' '))

        # 信号
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.textChanged.connect(self._on_text_changed)

        # 初始宽度
        self._update_line_number_area_width(0)

        # 加载默认脚本
        self.setPlainText(DEFAULT_SCRIPT)
        self._script_dirty = False

    # ------------------------------------------------------------------
    # 行号栏
    # ------------------------------------------------------------------
    def _line_number_area_width(self):
        digits = max(1, len(str(max(1, self.blockCount()))))
        space = 6 + self.fontMetrics().horizontalAdvance('9') * digits
        return space + 16  # 16px 留给执行箭头

    def _line_number_area_size(self):
        from PyQt6.QtCore import QSize
        return QSize(self._line_number_area_width(), 0)

    def _update_line_number_area_width(self, _new_block_count):
        self.setViewportMargins(self._line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(),
                  self._line_number_area_width(), cr.height())
        )

    def _line_number_area_paint(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#f0f0f0"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        arrow_area_w = 14  # 箭头区域宽度
        font_metrics = self.fontMetrics()
        digit_w = font_metrics.horizontalAdvance('9')

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                line_no = block_number + 1

                # 执行箭头（绿色三角）
                if line_no == self._current_line:
                    painter.save()
                    painter.setBrush(QColor("#4CAF50"))
                    painter.setPen(Qt.PenStyle.NoPen)
                    cx = 7
                    cy = top + (bottom - top) // 2
                    pts = [(cx, cy - 5), (cx + 5, cy), (cx, cy + 5)]
                    poly = QPolygonF([QPointF(*p) for p in pts])
                    painter.drawPolygon(poly)
                    painter.restore()

                # 目标行（蓝色菱形）
                if line_no == self._target_line and line_no != self._current_line:
                    painter.save()
                    painter.setBrush(QColor("#42A5F5"))
                    painter.setPen(Qt.PenStyle.NoPen)
                    cx = 7
                    cy = top + (bottom - top) // 2
                    pts = [(cx, cy - 4), (cx + 4, cy), (cx, cy + 4), (cx - 4, cy)]
                    poly = QPolygonF([QPointF(*p) for p in pts])
                    painter.drawPolygon(poly)
                    painter.restore()

                # 行号
                painter.setPen(QColor("#999999"))
                num_x = arrow_area_w + 4 + (3 - len(number)) * digit_w
                painter.drawText(
                    int(num_x), top,
                    self._line_number_area.width() - int(arrow_area_w),
                    font_metrics.height(),
                    Qt.AlignmentFlag.AlignRight, number
                )

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    # ------------------------------------------------------------------
    # 执行高亮
    # ------------------------------------------------------------------
    def highlight_line(self, line_number: int):
        """高亮当前执行行（绿色背景）。"""
        self._clear_highlights()
        self._current_line = line_number
        self._apply_highlight(line_number, QColor("#E8F5E9"))
        self.goto_line(line_number)
        self._line_number_area.update()

    def highlight_error_line(self, line_number: int):
        """红色高亮错误行。"""
        self._clear_highlights()
        self._error_line = line_number
        self._current_line = -1
        self._apply_highlight(line_number, QColor("#FFEBEE"))
        self.goto_line(line_number)
        self._line_number_area.update()

    def clear_highlight(self):
        """清除所有高亮。"""
        self._clear_highlights()
        self._current_line = -1
        self._error_line = -1
        self._line_number_area.update()

    def set_target_line(self, line_no: int):
        """设置目标行（蓝色光标标记）。"""
        self._target_line = line_no
        self._line_number_area.update()

    def _line_at_y(self, y: int) -> int:
        """根据 y 坐标计算行号。"""
        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        while block.isValid():
            bottom = top + round(self.blockBoundingRect(block).height())
            if top <= y <= bottom:
                return block.blockNumber() + 1
            block = block.next()
            top = bottom
        return 0

    def _on_line_number_clicked(self, line_no: int):
        """行号被点击。"""
        self._target_line = line_no
        self._line_number_area.update()
        self.line_clicked.emit(line_no)

    def _clear_highlights(self):
        self.setExtraSelections([])

    def _apply_highlight(self, line_number: int, color: QColor):
        """对指定行应用背景色高亮。"""
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(color)
        sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.movePosition(
            self.textCursor().MoveOperation.Start
        )
        block = self.document().findBlockByLineNumber(line_number - 1)
        if block.isValid():
            sel.cursor.setPosition(block.position())
        self.setExtraSelections([sel])

    def goto_line(self, line_number: int):
        """滚动并选中指定行。"""
        block = self.document().findBlockByLineNumber(line_number - 1)
        if not block.isValid():
            return
        cursor = self.textCursor()
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _on_text_changed(self):
        self._script_dirty = True
        self.script_modified.emit(self.toPlainText())

    def is_dirty(self) -> bool:
        return self._script_dirty

    def mark_clean(self):
        self._script_dirty = False
