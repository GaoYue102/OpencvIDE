"""函数说明面板 —— 显示当前行 OpenCV 函数的文档。"""
from typing import Optional, Tuple
import re
import cv2
import numpy as np
from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


# OpenCV 函数签名和说明
_FUNC_DESCRIPTIONS = {
    "imread": ("cv2.imread(path, flags=cv2.IMREAD_COLOR) -> np.ndarray",
               "从文件读取图像。支持 BMP、JPEG、PNG、TIFF 等格式。\n"
               "flags: cv2.IMREAD_COLOR(默认BGR), "
               "cv2.IMREAD_GRAYSCALE(灰度), cv2.IMREAD_UNCHANGED(保留alpha)"),
    "cvtColor": ("cv2.cvtColor(src, code) -> np.ndarray",
                 "色彩空间转换。\n常用 code: cv2.COLOR_BGR2GRAY, "
                 "cv2.COLOR_BGR2HSV, cv2.COLOR_BGR2RGB"),
    "GaussianBlur": ("cv2.GaussianBlur(src, ksize, sigmaX, sigmaY=0) -> np.ndarray",
                     "高斯模糊/平滑。ksize: 核大小(w,h)必须为正奇数。sigmaX: 标准差。"),
    "Canny": ("cv2.Canny(image, threshold1, threshold2) -> np.ndarray",
              "Canny边缘检测。threshold1:低阈值, threshold2:高阈值。推荐比例1:2或1:3。"),
    "threshold": ("cv2.threshold(src, thresh, maxval, type) -> (retval, dst)",
                  "固定阈值二值化。type: cv2.THRESH_BINARY, cv2.THRESH_OTSU等。"),
    "adaptiveThreshold": ("cv2.adaptiveThreshold(src, maxValue, adaptiveMethod, "
                          "thresholdType, blockSize, C) -> np.ndarray",
                          "自适应阈值二值化。blockSize:邻域大小(奇数)。C:从均值减去的常数。"),
    "resize": ("cv2.resize(src, dsize, fx=0, fy=0, interpolation=INTER_LINEAR) -> np.ndarray",
               "缩放图像。dsize:目标尺寸(w,h)。或通过fx/fy指定比例因子。"),
    "dilate": ("cv2.dilate(src, kernel, iterations=1) -> np.ndarray",
               "膨胀操作（扩大亮区域），用于闭合小孔洞。"),
    "erode": ("cv2.erode(src, kernel, iterations=1) -> np.ndarray",
              "腐蚀操作（缩小亮区域），用于去除小噪点。"),
    "morphologyEx": ("cv2.morphologyEx(src, op, kernel, iterations=1) -> np.ndarray",
                     "形态学操作。op: cv2.MORPH_OPEN(先腐后胀), cv2.MORPH_CLOSE(先胀后腐)等。"),
    "findContours": ("cv2.findContours(image, mode, method) -> contours, hierarchy",
                     "查找轮廓。mode: cv2.RETR_EXTERNAL(仅外轮廓), cv2.RETR_TREE。"),
    "drawContours": ("cv2.drawContours(image, contours, contourIdx, color, thickness)",
                     "绘制轮廓。contourIdx=-1 绘制全部。"),
    "bitwise_and": ("cv2.bitwise_and(src1, src2, mask=None) -> np.ndarray",
                    "按位与，常用于掩膜提取。"),
    "addWeighted": ("cv2.addWeighted(src1, alpha, src2, beta, gamma) -> np.ndarray",
                    "加权混合。dst = src1*alpha + src2*beta + gamma。"),
    "Sobel": ("cv2.Sobel(src, ddepth, dx, dy, ksize=3) -> np.ndarray",
              "Sobel梯度算子。dx/dy:求导阶数。ksize:核大小(1,3,5,7)。"),
    "medianBlur": ("cv2.medianBlur(src, ksize) -> np.ndarray",
                   "中值滤波，去椒盐噪声。ksize为大于1的奇数。"),
    "bilateralFilter": ("cv2.bilateralFilter(src, d, sigmaColor, sigmaSpace) -> np.ndarray",
                        "双边滤波（保边去噪）。"),
    "HoughLinesP": ("cv2.HoughLinesP(image, rho, theta, threshold, "
                    "minLineLength, maxLineGap) -> lines",
                    "概率霍夫直线检测。"),
    "HoughCircles": ("cv2.HoughCircles(image, method, dp, minDist, "
                     "param1, param2, minRadius, maxRadius) -> circles",
                     "霍夫圆检测。"),
    "equalizeHist": ("cv2.equalizeHist(src) -> np.ndarray",
                     "直方图均衡化（仅灰度图）。"),
    "inRange": ("cv2.inRange(src, lowerb, upperb) -> np.ndarray",
                "颜色范围过滤，返回二值掩膜。常用于HSV颜色空间。"),
    "flip": ("cv2.flip(src, flipCode) -> np.ndarray",
             "翻转图像。0=垂直, 1=水平, -1=双向。"),
    "absdiff": ("cv2.absdiff(src1, src2) -> np.ndarray",
                "计算两幅图像绝对差值。"),
    "split": ("cv2.split(m) -> list[np.ndarray]",
              "分离多通道为单通道列表。"),
    "merge": ("cv2.merge(mv) -> np.ndarray",
              "合并单通道列表为多通道。"),
    "Laplacian": ("cv2.Laplacian(src, ddepth, ksize=1) -> np.ndarray",
                  "Laplacian边缘检测。"),
    "blur": ("cv2.blur(src, ksize) -> np.ndarray",
             "均值滤波（归一化盒式滤波）。"),
    "filter2D": ("cv2.filter2D(src, ddepth, kernel) -> np.ndarray",
                 "自定义卷积核滤波。"),
    "calcHist": ("cv2.calcHist(images, channels, mask, histSize, ranges) -> np.ndarray",
                 "计算直方图。"),
}


def _find_func_on_line(line_text: str) -> Optional[str]:
    m = re.search(r'cv2\.(\w+)\s*\(', line_text)
    if m:
        return m.group(1)
    # numpy 函数
    m = re.search(r'np\.(\w+)\s*\(', line_text)
    if m:
        return f"np.{m.group(1)}"
    return None


def get_func_info(func_name: str) -> Tuple[str, str]:
    """获取 (签名, 说明)。"""
    key = func_name.replace("cv2.", "").replace("np.", "")
    if key in _FUNC_DESCRIPTIONS:
        return _FUNC_DESCRIPTIONS[key]

    # fallback: 尝试获取实际 docstring
    try:
        obj = cv2
        for p in key.split("."):
            obj = getattr(obj, p, None)
            if obj is None:
                break
        if obj is not None and getattr(obj, "__doc__", None):
            first_line = obj.__doc__.strip().split('\n')[0]
            return (f"{func_name}(...)", first_line)
    except Exception:
        pass

    return (f"{func_name}(...)", "暂无说明")


class FunctionDocPanel(QDockWidget):
    """显示当前执行行中 OpenCV 函数的文档。可拖动。"""

    def __init__(self, parent=None):
        super().__init__("函数说明", parent)
        self.setObjectName("function_doc_panel")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setMinimumHeight(80)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 10))
        self._text.setMaximumHeight(130)
        self._text.setStyleSheet("background: #FAFAFA;")
        layout.addWidget(self._text)

        self.setWidget(container)

    def show_line_doc(self, line_text: str):
        func_name = _find_func_on_line(line_text)
        if func_name is None:
            return
        sig, desc = get_func_info(func_name)
        html = (
            f"<b style='color:#1565C0;'>{func_name}</b><br>"
            f"<code>{sig}</code><br><br>"
            f"{desc}"
        )
        self._text.setHtml(html)

    def clear(self):
        self._text.clear()
