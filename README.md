# OpencvIDE

类 HDevelop 的 OpenCV 交互式视觉编程工具。编写 Python/OpenCV 代码，逐行执行并即时查看每一步图像处理结果，便于选择合适的函数和参数。

## 界面布局

```
┌──────────────────────────────────────────────────────┐
│  菜单栏 / 工具栏 (运行/单步/停止/重置)                  │
├────────────────────────────────┬─────────────────────┤
│                                │  变量窗口 (可拖动)     │
│  脚本编辑器 (带行号、执行高亮)    │  ├ 图像缩略图         │
│                                │  ├ 控制变量           │
│                                │  └ print 输出         │
├────────────────────────────────┤                     │
│  图像查看器 (缩放/平移)          │                     │
├────────────────────────────────┴─────────────────────┤
│  函数说明面板 (当前行 OpenCV 函数文档)                   │
└──────────────────────────────────────────────────────┘
```

## 功能

- **逐行执行** — F6 单步、F5 运行，基于 `sys.settrace()` 实现行级步进
- **即时图像显示** — 每步执行后自动显示新生成的 `np.ndarray` 图像变量
- **变量面板** — 图像缩略图列表、控制变量值、`print()` 输出
- **函数文档** — 自动识别当前行 OpenCV 函数并显示签名和说明
- **跳转执行** — 点击行号设置目标行，F5/F6 直接运行到该行
- **编辑自动定位** — 光标移动自动标记目标行，改参数后无需从头运行
- **可拖动布局** — 变量面板和函数面板可自由拖动、悬浮
- **缩放保持** — 图像查看器切换图片时保持缩放比例和中心位置

## 安装

```bash
# 克隆仓库
git clone https://github.com/GaoYue102/OpencvIDE.git
cd OpencvIDE

# 安装依赖
pip install -r requirements.txt
```

依赖：`PyQt6>=6.5.0` `opencv-contrib-python>=4.8.0` `numpy>=1.24.0`

## 使用

```bash
py -3 main.py
```

1. 在编辑器中编写 OpenCV 处理脚本（或使用默认示例）
2. **F6** — 单步执行一行
3. **F5** — 连续运行到结束（或到目标行）
4. **Esc** — 停止执行
5. 点击行号设置目标行，光标移动自动标记当前行
6. 右侧变量面板查看图像缩略图和控制变量值

## 项目结构

```
OpencvIDE/
├── main.py                    # 入口
├── core/
│   ├── execution_engine.py    # sys.settrace() + QThread 逐行执行
│   └── image_io.py            # 中文路径安全读取
├── ui/
│   ├── main_window.py         # 主窗口、状态机、跳转逻辑
│   ├── script_editor.py       # 代码编辑器 + 行号栏 + 高亮
│   ├── image_canvas.py        # 可缩放平移的图像查看器
│   ├── variable_panel.py      # 变量面板 (缩略图/控制变量/输出)
│   └── function_doc.py        # OpenCV 函数文档面板
└── tests/
    ├── conftest.py            # pytest fixtures
    └── test_execution_engine.py
```

## 开发

```bash
# 运行测试
py -3 -m pytest tests/ -v

# 单个测试
py -3 -m pytest tests/test_execution_engine.py::TestExecutionEngine::test_step_mode -v
```
