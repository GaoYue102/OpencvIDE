"""逐行 Python 执行引擎 —— sys.settrace() + QThread。

在后台线程中执行用户脚本，逐行暂停，捕获命名空间中的 numpy 图像变量。
"""
import sys
import threading
import io
from contextlib import redirect_stdout
from typing import Dict, Any
import traceback

import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal


class StopExecution(Exception):
    """用户手动停止执行的信号异常。"""
    pass


class ExecutionEngine(QThread):
    """逐行 Python 执行器，用 sys.settrace() 实现行级步进。"""

    # ---- 信号 ----
    line_reached = pyqtSignal(int)                        # 当前行号
    new_image_detected = pyqtSignal(str, np.ndarray)      # 新图像变量 (名称, 图像)
    variables_changed = pyqtSignal(dict)                   # 完整命名空间快照
    stdout_received = pyqtSignal(str)                      # print() 输出
    execution_paused = pyqtSignal()                        # 暂停等待用户操作
    execution_finished = pyqtSignal()                      # 脚本正常完成
    execution_error = pyqtSignal(str, int)                 # (错误消息, 行号)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source: str = ""
        self._namespace: Dict[str, Any] = {}
        self._prev_var_keys: set = set()
        self._step_event = threading.Event()
        self._stop_flag = False
        self._step_mode = True
        self._target_line: int = 0
        self._script_filename = "<opencv_ide_script>"

    # ------------------------------------------------------------------
    # 公共控制方法（主线程调用）
    # ------------------------------------------------------------------
    def set_source(self, source: str):
        """加载脚本源码。"""
        self._source = source

    def step(self):
        """单步执行一行。"""
        self._step_mode = True
        self._step_event.set()

    def run_continuously(self):
        """连续执行到结束或目标行。"""
        self._step_mode = False
        self._step_event.set()

    def run_to_line(self, target_line: int):
        """连续执行到指定行后暂停。"""
        self._target_line = target_line
        self._step_mode = False
        self._step_event.set()

    def stop(self):
        """停止执行。"""
        self._stop_flag = True
        self._step_event.set()

    def reset(self):
        """复位引擎状态。"""
        self._namespace.clear()
        self._prev_var_keys.clear()
        self._stop_flag = False
        self._step_event.clear()
        self._target_line = 0

    def is_paused(self) -> bool:
        return not self._step_event.is_set()

    def get_variable(self, name: str):
        """获取命名空间中的变量值。"""
        return self._namespace.get(name)

    def get_all_variables(self) -> dict:
        """获取完整命名空间快照（过滤内部变量）。"""
        result = {}
        for k, v in self._namespace.items():
            if k.startswith('__') and k.endswith('__'):
                continue
            if k in ('cv2', 'np'):
                continue
            if callable(v) and not isinstance(v, (np.ndarray,)):
                continue
            result[k] = v
        return result

    # ------------------------------------------------------------------
    # QThread 入口
    # ------------------------------------------------------------------
    def run(self):
        """在后台线程中执行用户脚本。"""
        self._stop_flag = False
        # 不在此处 clear event —— reset() 已经处理，
        # 且 run_continuously() 可能在 thread start 之后立即 set

        # 初始化命名空间
        self._namespace = {
            '__builtins__': __builtins__,
            'cv2': cv2,
            'np': np,
        }
        self._prev_var_keys = set(self._namespace.keys())

        stdout_buf = io.StringIO()

        try:
            code = compile(self._source, self._script_filename, 'exec')
            # 设置 trace
            sys.settrace(self._trace_func)
            try:
                with redirect_stdout(stdout_buf):
                    exec(code, self._namespace)
            finally:
                sys.settrace(None)
                stdout_output = stdout_buf.getvalue()
                if stdout_output:
                    self.stdout_received.emit(stdout_output)
        except StopExecution:
            pass
        except SyntaxError as e:
            line_no = e.lineno or 1
            self.execution_error.emit(f"语法错误: {e.msg}", line_no)
        except Exception:
            line_no = self._extract_script_lineno(sys.exc_info()[2])
            self.execution_error.emit(traceback.format_exc(), line_no)

        self.execution_finished.emit()

    # ------------------------------------------------------------------
    # trace 回调（在后台线程中执行）
    # ------------------------------------------------------------------
    def _trace_func(self, frame, event, arg):
        if event != 'line':
            return self._trace_func
        if frame.f_code.co_filename != self._script_filename:
            return self._trace_func

        line_no = frame.f_lineno

        # 扫描命名空间变化
        self._scan_namespace()

        # 发射行号
        self.line_reached.emit(line_no)

        # 暂停逻辑
        should_pause = self._step_mode
        if self._target_line > 0 and line_no >= self._target_line:
            should_pause = True
            self._target_line = 0  # 到达目标行后清除
            self._step_mode = True

        if should_pause:
            self._step_event.clear()
            self.execution_paused.emit()
            self._step_event.wait()

        if self._stop_flag:
            raise StopExecution()

        return self._trace_func

    # ------------------------------------------------------------------
    # 命名空间扫描
    # ------------------------------------------------------------------
    def _scan_namespace(self):
        """扫描命名空间，检测新增/变化的变量。"""
        current_keys = set(self._namespace.keys())
        new_keys = current_keys - self._prev_var_keys

        for key in new_keys:
            val = self._namespace[key]
            if isinstance(val, np.ndarray):
                self.new_image_detected.emit(key, val)

        # 发出完整变量快照
        self.variables_changed.emit(self.get_all_variables())

        self._prev_var_keys = current_keys.copy()

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    def _extract_script_lineno(self, tb) -> int:
        """从 traceback 中提取脚本行号。"""
        while tb is not None:
            if tb.tb_frame.f_code.co_filename == self._script_filename:
                return tb.tb_lineno
            tb = tb.tb_next
        return 1
