"""主窗口 —— QSplitter + QDockWidget，对齐 HDevelop 界面。"""
import os
from typing import Optional

import numpy as np
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar, QFileDialog, QMessageBox,
    QSplitter, QTabWidget, QMenu,
)

from core.execution_engine import ExecutionEngine
from ui.script_editor import ScriptEditor
from ui.image_canvas import ImageCanvas
from ui.variable_panel import VariablePanel
from ui.function_doc import FunctionDocPanel
from ui.find_replace_dialog import FindReplaceDialog
from ui.histogram_panel import HistogramPanel


class ExecState:
    IDLE = "idle"
    PAUSED = "paused"
    RUNNING = "running"
    ERROR = "error"


class MainWindow(QMainWindow):
    """OpencvIDE 主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpencvIDE — [未命名]")
        self.resize(1400, 900)

        # 引擎 — 必须在 tab widget 之前创建
        self._engine = ExecutionEngine()

        # 状态 — 必须在 _new_tab 之前初始化
        self._tab_files: dict = {}

        # 核心组件
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.tabCloseRequested.connect(self._close_tab)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        self._new_tab(load_default=True)  # 首标签页加载示例脚本

        # 图像查看器标签页
        self._viewer_tabs = QTabWidget()
        self._viewer_tabs.setTabsClosable(True)
        self._viewer_tabs.tabCloseRequested.connect(self._close_viewer_tab)
        self._main_viewer = ImageCanvas()
        self._viewer_tabs.addTab(self._main_viewer, "当前")
        self._viewer = self._main_viewer  # 默认查看器

        self._variable_panel = VariablePanel()
        self._function_doc = FunctionDocPanel()
        self._histogram_panel = HistogramPanel()
        self._find_dialog = FindReplaceDialog(self)

        # 状态
        self._exec_state = ExecState.IDLE
        self._current_file: Optional[str] = None
        self._current_exec_line: int = 0
        self._source_dirty: bool = False
        self._recent_files: list = []

        # 构建界面
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_statusbar()
        self._setup_layout()
        self._connect_signals()
        self._load_settings()

        self._engine.set_source(self._editor.toPlainText())
        self._update_button_states()

    # ------------------------------------------------------------------
    # 编辑器标签页管理
    # ------------------------------------------------------------------
    @property
    def _editor(self) -> ScriptEditor:
        return self._tab_widget.currentWidget()

    def _new_tab(self, load_default: bool = False) -> ScriptEditor:
        editor = ScriptEditor(load_default=load_default)
        idx = self._tab_widget.addTab(editor, "未命名")
        self._tab_widget.setCurrentIndex(idx)
        self._connect_editor_signals(editor)
        return editor

    def _close_tab(self, idx: int):
        if self._tab_widget.count() <= 1:
            return  # 至少保留一个标签页
        editor = self._tab_widget.widget(idx)
        if editor and editor.is_dirty():
            ret = QMessageBox.question(
                self, "未保存", "该标签页已修改，是否关闭？",
                QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if ret == QMessageBox.StandardButton.Cancel:
                return
        self._tab_widget.removeTab(idx)

    def _close_viewer_tab(self, idx: int):
        """关闭查看器标签页（保留第一个"当前"标签）。"""
        if idx == 0:
            return
        self._viewer_tabs.removeTab(idx)

    def _clear_viewers(self):
        """清空所有查看器标签页。"""
        self._main_viewer.clear_image()
        while self._viewer_tabs.count() > 1:
            self._viewer_tabs.removeTab(1)
        self._histogram_panel.clear()

    def _on_tab_changed(self, idx: int):
        editor = self._tab_widget.widget(idx)
        if editor and hasattr(self, '_engine'):
            self._engine.set_source(editor.toPlainText())
            self._source_dirty = True
            title = self._tab_widget.tabText(idx)
            self.setWindowTitle(f"OpencvIDE — {title}")
            self._engine.set_breakpoints(editor.breakpoints())
            # 更新当前文件路径
            self._current_file = self._tab_files.get(idx)

    # ------------------------------------------------------------------
    # 布局
    # ------------------------------------------------------------------
    def _setup_layout(self):
        """左侧 (tab编辑器 | 查看器) 为 central widget，
        右侧 VariablePanel、底部 FunctionDoc 为 DockWidget。"""
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.addWidget(self._tab_widget)
        left_splitter.addWidget(self._viewer_tabs)
        left_splitter.setStretchFactor(0, 40)
        left_splitter.setStretchFactor(1, 60)
        self.setCentralWidget(left_splitter)

        # 右侧：变量面板 (DockWidget)
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self._variable_panel
        )

        # 底部：函数说明 (DockWidget)
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea, self._function_doc
        )

        # 底部：直方图面板 (tabbified with function doc)
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea, self._histogram_panel
        )
        self.tabifyDockWidget(self._function_doc, self._histogram_panel)
        self._function_doc.raise_()  # 函数说明默认显示

    # ------------------------------------------------------------------
    # 菜单栏
    # ------------------------------------------------------------------
    def _setup_menubar(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("文件(&F)")
        file_menu.addAction("打开脚本(&O)…\tCtrl+O", self._open_script)
        file_menu.addAction("保存(&S)\tCtrl+S", self._save_script)
        file_menu.addAction("另存为(&A)…", self._save_script_as)
        file_menu.addSeparator()
        self._recent_menu = file_menu.addMenu("最近文件")
        self._update_recent_menu()
        file_menu.addSeparator()
        file_menu.addAction("退出(&Q)", self.close)

        edit_menu = mb.addMenu("编辑(&E)")
        edit_menu.addAction("撤销(&U)\tCtrl+Z", self._undo)
        edit_menu.addAction("重做(&R)\tCtrl+Y", self._redo)
        edit_menu.addSeparator()
        edit_menu.addAction("查找/替换(&F)\tCtrl+F", self._show_find_replace)
        edit_menu.addSeparator()
        edit_menu.addAction("新建标签页(&N)\tCtrl+T", self._new_tab_action)

        run_menu = mb.addMenu("运行(&R)")
        self._act_run = QAction("运行(&R)\tF5", self)
        self._act_run.triggered.connect(self._on_run)
        run_menu.addAction(self._act_run)

        self._act_step = QAction("单步(&S)\tF6", self)
        self._act_step.triggered.connect(self._on_step)
        run_menu.addAction(self._act_step)

        self._act_stop = QAction("停止(&T)\tEsc", self)
        self._act_stop.triggered.connect(self._on_stop)
        run_menu.addAction(self._act_stop)

        run_menu.addSeparator()
        self._act_reset = QAction("重置(&R)", self)
        self._act_reset.triggered.connect(self._on_reset)
        run_menu.addAction(self._act_reset)

        view_menu = mb.addMenu("视图(&V)")
        view_menu.addAction("清空查看器", self._clear_viewers)
        view_menu.addSeparator()
        view_menu.addAction(self._variable_panel.toggleViewAction())
        view_menu.addAction(self._function_doc.toggleViewAction())
        view_menu.addAction(self._histogram_panel.toggleViewAction())

    # ------------------------------------------------------------------
    # 工具栏
    # ------------------------------------------------------------------
    def _setup_toolbar(self):
        tb = QToolBar("工具栏")
        tb.setObjectName("main_toolbar")
        tb.setMovable(False)
        self.addToolBar(tb)

        tb.addAction("打开", self._open_script)
        tb.addAction("保存", self._save_script)
        tb.addSeparator()

        self._act_run_tb = tb.addAction("▶ 运行 (F5)", self._on_run)
        self._act_step_tb = tb.addAction("⏭ 单步 (F6)", self._on_step)
        self._act_stop_tb = tb.addAction("■ 停止 (Esc)", self._on_stop)
        tb.addSeparator()
        tb.addAction("↺ 重置", self._on_reset)
        tb.addSeparator()
        self._act_roi_rect = tb.addAction("□ 矩形ROI", lambda: self._set_roi_mode("rect"))
        self._act_roi_circle = tb.addAction("○ 圆形ROI", lambda: self._set_roi_mode("circle"))
        self._act_roi_line = tb.addAction("╱ 直线ROI", lambda: self._set_roi_mode("line"))
        self._act_roi_off = tb.addAction("✕ 退出ROI", lambda: self._set_roi_mode(""))

    # ------------------------------------------------------------------
    # 状态栏
    # ------------------------------------------------------------------
    def _setup_statusbar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("就绪")

    # ------------------------------------------------------------------
    # QSettings
    # ------------------------------------------------------------------
    def _load_settings(self):
        s = QSettings("OpencvIDE", "OpencvIDE")
        geo = s.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        state = s.value("windowState")
        if state is not None:
            self.restoreState(state)
        self._recent_files = s.value("recentFiles", [])
        if not isinstance(self._recent_files, list):
            self._recent_files = []

    def _save_settings(self):
        s = QSettings("OpencvIDE", "OpencvIDE")
        s.setValue("geometry", self.saveGeometry())
        s.setValue("windowState", self.saveState())
        s.setValue("recentFiles", self._recent_files)

    def closeEvent(self, event):
        if self._editor.is_dirty():
            ret = QMessageBox.question(
                self, "未保存", "脚本已修改，是否保存？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if ret == QMessageBox.StandardButton.Save:
                if not self._save_script():
                    event.ignore()
                    return
            elif ret == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        self._save_settings()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # 最近文件
    # ------------------------------------------------------------------
    def _update_recent_menu(self):
        self._recent_menu.clear()
        for path in self._recent_files:
            if os.path.isfile(path):
                action = QAction(os.path.basename(path), self)
                action.setToolTip(path)
                action.triggered.connect(
                    lambda checked, p=path: self._open_file(p)
                )
                self._recent_menu.addAction(action)
        if self._recent_files:
            self._recent_menu.addSeparator()
            self._recent_menu.addAction("清空最近文件", self._clear_recent)

    def _add_recent(self, path: str):
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:5]
        self._update_recent_menu()

    def _clear_recent(self):
        self._recent_files.clear()
        self._update_recent_menu()

    # ------------------------------------------------------------------
    # 编辑操作
    # ------------------------------------------------------------------
    def _undo(self):
        self._editor.undo_edit()

    def _redo(self):
        self._editor.redo_edit()

    def _show_find_replace(self):
        self._find_dialog.show_for_editor(self._editor)

    def _new_tab_action(self):
        editor = self._new_tab()
        self._connect_editor_signals(editor)

    # ------------------------------------------------------------------
    # 文件操作
    # ------------------------------------------------------------------
    def _open_script(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开脚本", "",
            "Python (*.py);;All Files (*)"
        )
        if path:
            self._open_file(path)

    def _open_file(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件: {e}")
            return
        editor = self._editor
        editor.setPlainText(content)
        editor.mark_clean()
        self._current_file = path
        idx = self._tab_widget.currentIndex()
        self._tab_files[idx] = path
        basename = os.path.basename(path)
        self._tab_widget.setTabText(idx, basename)
        self.setWindowTitle(f"OpencvIDE — {basename}")
        self._engine.set_source(content)
        self._add_recent(path)
        self._status.showMessage(f"已打开: {path}")

    def _save_script(self) -> bool:
        if self._current_file:
            return self._do_save(self._current_file)
        else:
            return self._save_script_as()

    def _save_script_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self, "保存脚本", "script.py",
            "Python (*.py);;All Files (*)"
        )
        if not path:
            return False
        self._current_file = path
        return self._do_save(path)

    def _do_save(self, path: str) -> bool:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._editor.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法保存: {e}")
            return False
        self._editor.mark_clean()
        basename = os.path.basename(path)
        idx = self._tab_widget.currentIndex()
        self._tab_files[idx] = path
        self._tab_widget.setTabText(idx, basename)
        self.setWindowTitle(f"OpencvIDE — {basename}")
        self._add_recent(path)
        self._status.showMessage(f"已保存: {path}")
        return True

    # ------------------------------------------------------------------
    # 运行控制
    # ------------------------------------------------------------------
    def _on_step(self):
        target = self._editor._target_line
        if self._exec_state == ExecState.IDLE:
            if target > 0:
                self._start_engine()
                self._exec_state = ExecState.RUNNING
                self._update_button_states()
                self._engine.run_to_line(target)
                self._clear_target_line()
            else:
                self._start_engine()
        elif self._exec_state == ExecState.PAUSED:
            if target > 0:
                self._jump_to_line(target)
            else:
                self._exec_state = ExecState.RUNNING
                self._update_button_states()
                self._engine.step()
        elif self._exec_state == ExecState.ERROR:
            self._reset_and_start()

    def _on_run(self):
        target = self._editor._target_line
        if self._exec_state == ExecState.IDLE:
            self._start_engine()
            self._exec_state = ExecState.RUNNING
            self._update_button_states()
            if target > 0:
                self._engine.run_to_line(target)
                self._clear_target_line()
            else:
                self._engine.run_continuously()
        elif self._exec_state == ExecState.PAUSED:
            if target > 0:
                self._jump_to_line(target)
            else:
                self._exec_state = ExecState.RUNNING
                self._update_button_states()
                self._engine.run_continuously()
        elif self._exec_state == ExecState.ERROR:
            self._reset_and_start()

    def _jump_to_line(self, target: int):
        """暂停中跳转到目标行。源码脏或向后跳时重启引擎。"""
        need_restart = self._source_dirty or target < self._current_exec_line
        if need_restart:
            self._restart_engine_to_line(target)
        else:
            self._exec_state = ExecState.RUNNING
            self._update_button_states()
            self._engine.run_to_line(target)
        self._clear_target_line()

    def _restart_engine_to_line(self, target: int):
        """重启引擎（重新编译最新源码），运行到目标行暂停。"""
        self._engine.stop()
        self._engine.wait(2000)
        self._engine.reset()
        self._engine.set_source(self._editor.toPlainText())
        self._variable_panel.clear()
        self._function_doc.clear()
        self._clear_viewers()
        self._current_exec_line = 0
        self._editor.clear_highlight()
        self._exec_state = ExecState.RUNNING
        self._source_dirty = False
        self._update_button_states()
        self._engine.start()
        self._engine.run_to_line(target)

    def _clear_target_line(self):
        self._editor._target_line = -1
        self._editor._line_number_area.update()

    def _on_stop(self):
        if self._exec_state in (ExecState.RUNNING, ExecState.PAUSED):
            self._engine.stop()
            self._exec_state = ExecState.IDLE
            self._update_button_states()
            self._editor.clear_highlight()
            self._status.showMessage("已停止")

    def _on_reset(self):
        if self._engine.isRunning():
            self._engine.stop()
            self._engine.wait(1000)
        self._engine.reset()
        self._engine.set_source(self._editor.toPlainText())
        self._exec_state = ExecState.IDLE
        self._source_dirty = False
        self._current_exec_line = 0
        self._editor.clear_highlight()
        self._editor._target_line = -1
        self._editor._line_number_area.update()
        self._variable_panel.clear()
        self._function_doc.clear()
        self._clear_viewers()
        self._engine.set_breakpoints(set())
        self._update_button_states()
        self._status.showMessage("已重置 — 从头开始")

    def _start_engine(self):
        self._engine.reset()
        self._engine.set_source(self._editor.toPlainText())
        self._source_dirty = False
        self._exec_state = ExecState.RUNNING
        self._update_button_states()
        self._variable_panel.clear()
        self._function_doc.clear()
        self._clear_viewers()
        self._current_exec_line = 0
        self._last_displayed_var = None
        self._editor.clear_highlight()
        self._status.showMessage("执行中…")
        self._engine.start()

    def _reset_and_start(self):
        if self._engine.isRunning():
            self._engine.stop()
            self._engine.wait(1000)
        self._start_engine()

    # ------------------------------------------------------------------
    # 按钮状态
    # ------------------------------------------------------------------
    def _update_button_states(self):
        s = self._exec_state
        idle_or_error = s in (ExecState.IDLE, ExecState.ERROR)
        is_paused = s == ExecState.PAUSED
        is_running = s == ExecState.RUNNING

        self._act_run.setEnabled(idle_or_error or is_paused)
        self._act_step.setEnabled(idle_or_error or is_paused)
        self._act_stop.setEnabled(is_running or is_paused)

        self._act_run_tb.setEnabled(idle_or_error or is_paused)
        self._act_step_tb.setEnabled(idle_or_error or is_paused)
        self._act_stop_tb.setEnabled(is_running or is_paused)

        if is_paused:
            self._act_run.setText("继续(&C)\tF5")
            self._act_run_tb.setText("▶ 继续 (F5)")
        else:
            self._act_run.setText("运行(&R)\tF5")
            self._act_run_tb.setText("▶ 运行 (F5)")

    # ------------------------------------------------------------------
    # 信号连接（用 QueuedConnection 确保线程安全）
    # ------------------------------------------------------------------
    def _connect_signals(self):
        # 引擎 → UI
        self._engine.line_reached.connect(
            self._on_line_reached, Qt.ConnectionType.QueuedConnection)
        self._engine.new_image_detected.connect(
            self._on_new_image, Qt.ConnectionType.QueuedConnection)
        self._engine.variables_changed.connect(
            self._on_variables_changed, Qt.ConnectionType.QueuedConnection)
        self._engine.stdout_received.connect(
            self._on_stdout, Qt.ConnectionType.QueuedConnection)
        self._engine.execution_paused.connect(
            self._on_paused, Qt.ConnectionType.QueuedConnection)
        self._engine.execution_finished.connect(
            self._on_finished, Qt.ConnectionType.QueuedConnection)
        self._engine.execution_error.connect(
            self._on_error, Qt.ConnectionType.QueuedConnection)

        # 变量面板 → 查看器
        self._variable_panel.image_selected.connect(self._on_variable_selected)
        self._variable_panel.image_double_clicked.connect(
            self._on_variable_double_clicked)

        # 图像查看器像素悬停 → 状态栏
        self._viewer.pixel_hovered.connect(self._on_pixel_hovered)

        # ROI 创建 → 变量注入
        self._viewer.roi_created.connect(self._on_roi_created)

        # 缩放/平移联动
        self._viewer.zoom_updated.connect(self._on_viewer_zoom_changed)
        self._viewer.pan_updated.connect(self._on_viewer_pan_changed)

        # 第一个标签页的信号
        self._connect_editor_signals(self._editor)

    def _connect_editor_signals(self, editor: ScriptEditor):
        """连接编辑器标签页的信号。"""
        editor.script_modified.connect(self._on_script_modified)
        editor.line_clicked.connect(self._on_line_clicked)
        editor.cursorPositionChanged.connect(self._on_cursor_moved)
        editor.breakpoints_changed.connect(self._on_breakpoints_changed)

    def _on_breakpoints_changed(self):
        self._engine.set_breakpoints(self._editor.breakpoints())

    def _on_line_reached(self, line_no: int):
        self._current_exec_line = line_no
        self._editor.highlight_line(line_no)
        self._status.showMessage(f"执行中 — 第 {line_no} 行")
        # 显示当前行函数说明
        block = self._editor.document().findBlockByLineNumber(line_no - 1)
        if block.isValid():
            self._function_doc.show_line_doc(block.text())

    def _on_new_image(self, name: str, cv_img: np.ndarray):
        # 更新主查看器并切回 "当前" 标签页
        self._main_viewer.set_cv_image(cv_img)
        self._histogram_panel.set_image(cv_img)
        self._viewer_tabs.setCurrentIndex(0)
        self._last_displayed_var = name
        # 后台添加历史对比标签页
        viewer = ImageCanvas()
        viewer.set_cv_image(cv_img)
        self._viewer_tabs.addTab(viewer, name)
        viewer.pixel_hovered.connect(self._on_pixel_hovered)
        viewer.roi_created.connect(self._on_roi_created)
        viewer.zoom_updated.connect(self._on_viewer_zoom_changed)
        viewer.pan_updated.connect(self._on_viewer_pan_changed)
        # 限制标签页数量
        while self._viewer_tabs.count() > 10:
            self._viewer_tabs.removeTab(1)
        self._status.showMessage(f"图像: {name}  ({cv_img.shape[1]}x{cv_img.shape[0]})")

    def _on_pixel_hovered(self, x: int, y: int, info: str):
        self._status.showMessage(info, 3000)

    # ------------------------------------------------------------------
    # 缩放/平移联动
    # ------------------------------------------------------------------
    def _on_viewer_zoom_changed(self, scale: float, center):
        """一个查看器缩放时同步所有其他查看器。"""
        sender = self.sender()
        for i in range(self._viewer_tabs.count()):
            viewer = self._viewer_tabs.widget(i)
            if viewer is not sender and viewer:
                viewer._apply_zoom_with_absolute(scale, center, emit=False)

    def _on_viewer_pan_changed(self, center):
        """一个查看器平移时同步所有其他查看器。"""
        sender = self.sender()
        for i in range(self._viewer_tabs.count()):
            viewer = self._viewer_tabs.widget(i)
            if viewer is not sender and viewer:
                viewer.sync_pan(center)

    # ------------------------------------------------------------------
    # ROI 工具
    # ------------------------------------------------------------------
    def _set_roi_mode(self, mode: str):
        """切换 ROI 绘制模式。"""
        self._viewer.set_roi_mode(mode)
        modes = {"rect": "矩形ROI模式 — 在图像上拖拽绘制", "circle": "圆形ROI模式 — 在图像上拖拽绘制",
                 "line": "直线ROI模式 — 在图像上拖拽绘制"}
        self._status.showMessage(modes.get(mode, "ROI模式已退出"))

    def _on_roi_created(self, roi_type: str, params: tuple):
        """ROI 绘制完成，注入变量到引擎命名空间。"""
        if not self._engine.isRunning():
            return
        if roi_type == "rect" and len(params) == 4:
            x, y, w, h = params
            self._engine._namespace["roi_x"] = x
            self._engine._namespace["roi_y"] = y
            self._engine._namespace["roi_w"] = w
            self._engine._namespace["roi_h"] = h
            self._status.showMessage(f"矩形ROI: ({x},{y},{w},{h}) → roi_x/roi_y/roi_w/roi_h")
        elif roi_type == "circle" and len(params) == 3:
            cx, cy, r = params
            self._engine._namespace["roi_cx"] = cx
            self._engine._namespace["roi_cy"] = cy
            self._engine._namespace["roi_r"] = r
            self._status.showMessage(f"圆形ROI: 中心({cx},{cy}) r={r} → roi_cx/roi_cy/roi_r")
        elif roi_type == "line" and len(params) == 4:
            x1, y1, x2, y2 = params
            self._engine._namespace["roi_x1"] = x1
            self._engine._namespace["roi_y1"] = y1
            self._engine._namespace["roi_x2"] = x2
            self._engine._namespace["roi_y2"] = y2
            self._status.showMessage(f"直线ROI: ({x1},{y1})→({x2},{y2}) → roi_x1/roi_y1/roi_x2/roi_y2")
        self._variable_panel.refresh(self._engine.get_all_variables())

    def _on_script_modified(self, source: str):
        """编辑器内容变化时更新引擎源码并标记脏。"""
        self._engine.set_source(source)
        self._source_dirty = True

    def _on_line_clicked(self, line_no: int):
        """行号被点击，设置目标行光标。"""
        self._status.showMessage(f"目标行: {line_no} — 按 F5/F6 运行到此处")

    def _on_cursor_moved(self):
        """光标移动时自动在编辑行显示蓝色菱形标记。"""
        if self._exec_state not in (ExecState.IDLE, ExecState.PAUSED):
            return
        cursor = self._editor.textCursor()
        line_no = cursor.blockNumber() + 1
        self._editor.set_target_line(line_no)

    def _on_variables_changed(self, variables: dict):
        self._variable_panel.refresh(variables)

    def _on_stdout(self, text: str):
        self._variable_panel.append_output(text)

    def _on_paused(self):
        self._exec_state = ExecState.PAUSED
        self._update_button_states()

    def _on_finished(self):
        self._exec_state = ExecState.IDLE
        self._update_button_states()
        self._editor.clear_highlight()
        self._status.showMessage("完成")

    def _on_error(self, err_msg: str, line_no: int):
        self._exec_state = ExecState.ERROR
        self._update_button_states()
        self._editor.highlight_error_line(line_no)
        short = err_msg.strip().split('\n')[-1]
        self._status.showMessage(f"错误: {short}")
        QMessageBox.critical(self, "执行错误", err_msg)

    def _on_variable_selected(self, name: str, cv_img: np.ndarray):
        self._viewer.set_cv_image(cv_img)
        self._last_displayed_var = name
        self._status.showMessage(
            f"显示: {name}  ({cv_img.shape[1]}×{cv_img.shape[0]})"
        )

    def _on_variable_double_clicked(self, name: str, cv_img: np.ndarray):
        self._viewer.clear_image()
        self._viewer.set_cv_image(cv_img)
        self._last_displayed_var = name
        self._status.showMessage(
            f"显示: {name}  ({cv_img.shape[1]}×{cv_img.shape[0]})"
        )

    # ------------------------------------------------------------------
    # 快捷键
    # ------------------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_F6:
            self._on_step()
        elif key == Qt.Key.Key_F5:
            self._on_run()
        elif key == Qt.Key.Key_Escape:
            self._on_stop()
        else:
            super().keyPressEvent(event)
