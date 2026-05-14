# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

OpencvIDE — 类 HDevelop 的 OpenCV 交互式视觉编程工具。编写 Python/OpenCV 代码，逐行执行并即时查看图像处理结果。

## 开发命令

```bash
py -3 main.py                          # 启动应用
py -3 -m pytest tests/ -v              # 运行所有测试
py -3 -m pytest tests/test_execution_engine.py::TestExecutionEngine::test_step_mode -v  # 单个测试
py -3 -c "from ui.main_window import MainWindow; print('import OK')"  # 快速验证导入
```

依赖：`PyQt6>=6.5.0` `opencv-contrib-python>=4.8.0` `numpy>=1.24.0`

## 架构

```
main.py                        入口，创建 QApplication + MainWindow
core/
  execution_engine.py          核心：sys.settrace() + QThread 逐行执行 Python 代码
  image_io.py                  imread_unicode() — 中文路径安全读取
ui/
  main_window.py               主窗口：QSplitter(editor|viewer) + QDockWidget(variable+doc)
  script_editor.py             QPlainTextEdit 子类，行号栏、执行高亮(绿色三角)、目标行(蓝色菱形)
  image_canvas.py              QGraphicsView 子类，缩放/平移图像查看器
  variable_panel.py            QDockWidget，分三区：图像缩略图 | 控制变量 | print输出
  function_doc.py              QDockWidget，显示当前行 OpenCV 函数的签名和说明
tests/
  conftest.py                  qapp fixture (session级 QApplication) + sample_image
  test_execution_engine.py     8 个引擎测试（步进、变量捕获、停止、重置等）
```

## 关键设计

- **执行引擎** (`execution_engine.py`): `sys.settrace()` 在线程内每行触发，扫描命名空间找 `np.ndarray` 变量，通过 `Qt.QueuedConnection` 信号发回主线程。`threading.Event` 控制暂停/继续。
- **停止机制**: `raise StopExecution()` 抛异常终止 `exec()`，不要用 `return None`（只停 trace 不停代码）。
- **跳转逻辑** (`_jump_to_line`): 源码脏或向后跳 → 重启引擎重新 compile；源码干净且向前跳 → 直接 `run_to_line` 快速路径。
- **Python 3.9 兼容**: 类型注解用 `Optional[X]` / `Dict[K,V]` / `Tuple[X,Y]`，不能用 `X | None` / `dict[K,V]` / `tuple[X,Y]`。
- **中文路径**: 用 `core/image_io.py` 的 `imread_unicode()` 而非 `cv2.imread()`。
- **UI 布局**: 左侧垂直 QSplitter（编辑器上 40% + 查看器下 60%）为 central widget；变量面板、函数说明面板为可拖动 QDockWidget。

## 注意事项

- 编辑引擎相关代码后运行 `py -3 -m pytest tests/ -v`
- 信号连接必须用 `Qt.QueuedConnection` 确保跨线程安全
- 修改 UI 后 `py -3 -c "from ui.main_window import MainWindow; w = MainWindow(); w.close()"` 冒烟测试
