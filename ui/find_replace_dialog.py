"""查找/替换对话框。"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QPlainTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal


class FindReplaceDialog(QDialog):
    """非模态查找/替换对话框，操作目标编辑器。"""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("查找 / 替换")
        self.setMinimumWidth(380)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._editor: QPlainTextEdit = None

        layout = QVBoxLayout(self)

        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("查找:"))
        self._find_input = QLineEdit()
        self._find_input.setPlaceholderText("输入查找内容…")
        self._find_input.textChanged.connect(self._on_find_text_changed)
        find_layout.addWidget(self._find_input)
        layout.addLayout(find_layout)

        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("替换:"))
        self._replace_input = QLineEdit()
        self._replace_input.setPlaceholderText("替换为…")
        replace_layout.addWidget(self._replace_input)
        layout.addLayout(replace_layout)

        btn_layout = QHBoxLayout()
        self._prev_btn = QPushButton("上一个")
        self._prev_btn.clicked.connect(self._find_prev)
        btn_layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton("下一个")
        self._next_btn.clicked.connect(self._find_next)
        btn_layout.addWidget(self._next_btn)

        self._replace_btn = QPushButton("替换")
        self._replace_btn.clicked.connect(self._replace_current)
        btn_layout.addWidget(self._replace_btn)

        self._replace_all_btn = QPushButton("全部替换")
        self._replace_all_btn.clicked.connect(self._replace_all)
        btn_layout.addWidget(self._replace_all_btn)

        layout.addLayout(btn_layout)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._status)

        self._update_buttons()

    def set_editor(self, editor: QPlainTextEdit):
        self._editor = editor

    def show_for_editor(self, editor: QPlainTextEdit):
        self._editor = editor
        self._update_buttons()
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_find_text_changed(self):
        self._update_buttons()

    def _update_buttons(self):
        has_text = bool(self._find_input.text())
        self._prev_btn.setEnabled(has_text)
        self._next_btn.setEnabled(has_text)
        self._replace_btn.setEnabled(has_text)
        self._replace_all_btn.setEnabled(has_text)

    def _find_text(self, backward: bool = False):
        if not self._editor or not self._find_input.text():
            return False
        text = self._find_input.text()
        flags = QPlainTextEdit.findFlags()
        if backward:
            flags |= QPlainTextEdit.FindFlag.FindBackward

        found = self._editor.find(text, flags)
        if found:
            self._status.setText("")
        else:
            cursor = self._editor.textCursor()
            if backward:
                cursor.movePosition(cursor.MoveOperation.End)
            else:
                cursor.movePosition(cursor.MoveOperation.Start)
            self._editor.setTextCursor(cursor)
            found = self._editor.find(text, flags)
            if found:
                self._status.setText("(已回绕)")
            else:
                self._status.setText("未找到")
        return found

    def _find_next(self):
        self._find_text(backward=False)

    def _find_prev(self):
        self._find_text(backward=True)

    def _replace_current(self):
        if not self._editor:
            return
        cursor = self._editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self._find_input.text():
            cursor.insertText(self._replace_input.text())
        self._find_next()

    def _replace_all(self):
        if not self._editor or not self._find_input.text():
            return
        find_text = self._find_input.text()
        replace_text = self._replace_input.text()
        cursor = self._editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self._editor.setTextCursor(cursor)

        count = 0
        flags = QPlainTextEdit.findFlags()
        while self._editor.find(find_text, flags):
            cur = self._editor.textCursor()
            if cur.hasSelection():
                cur.insertText(replace_text)
                count += 1
        self._status.setText(f"已替换 {count} 处")

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
