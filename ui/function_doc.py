"""函数说明面板 — 显示当前行 OpenCV/numpy 函数的文档，支持动态 docstring 获取。"""
from typing import Optional, Tuple
import re
import cv2
import numpy as np
from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


_FUNC_DESCRIPTIONS = {
    # ---- 图像读写 ----
    "imread": ("cv2.imread(path, flags=cv2.IMREAD_COLOR) -> np.ndarray",
               "从文件读取图像。支持 BMP、JPEG、PNG、TIFF。flags: IMREAD_COLOR(默认BGR), IMREAD_GRAYSCALE(灰度), IMREAD_UNCHANGED(保留alpha)"),
    "imwrite": ("cv2.imwrite(filename, img) -> bool",
                "将图像写入文件。根据扩展名自动选择格式。"),
    "imdecode": ("cv2.imdecode(buf, flags) -> np.ndarray",
                 "从内存缓冲区解码图像（中文路径读取用）。"),
    "imencode": ("cv2.imencode(ext, img) -> (bool, buf)",
                 "将图像编码到内存缓冲区。"),

    # ---- 色彩空间 ----
    "cvtColor": ("cv2.cvtColor(src, code) -> np.ndarray",
                 "色彩空间转换。常用: COLOR_BGR2GRAY, COLOR_BGR2HSV, COLOR_BGR2RGB, COLOR_BGR2Lab, COLOR_GRAY2BGR"),
    "applyColorMap": ("cv2.applyColorMap(src, colormap) -> np.ndarray",
                      "对灰度图应用伪彩色映射。colormap: COLORMAP_JET, COLORMAP_HOT, COLORMAP_RAINBOW"),
    "LUT": ("cv2.LUT(src, lut) -> np.ndarray",
            "查表变换，对每个像素值执行映射。"),

    # ---- 滤波与平滑 ----
    "GaussianBlur": ("cv2.GaussianBlur(src, ksize, sigmaX, sigmaY=0) -> np.ndarray",
                     "高斯模糊。ksize: 核大小(w,h)正奇数。sigmaX: X方向标准差。"),
    "medianBlur": ("cv2.medianBlur(src, ksize) -> np.ndarray",
                   "中值滤波，去椒盐噪声。ksize 大于1的奇数。"),
    "bilateralFilter": ("cv2.bilateralFilter(src, d, sigmaColor, sigmaSpace) -> np.ndarray",
                        "双边滤波（保边去噪）。d: 滤波像素直径, sigmaColor: 颜色空间标准差, sigmaSpace: 坐标空间标准差"),
    "blur": ("cv2.blur(src, ksize) -> np.ndarray",
             "均值滤波（归一化盒式滤波）。"),
    "boxFilter": ("cv2.boxFilter(src, ddepth, ksize, normalize=True) -> np.ndarray",
                  "盒式滤波。normalize=True 等同于 blur。"),
    "filter2D": ("cv2.filter2D(src, ddepth, kernel) -> np.ndarray",
                 "自定义卷积核滤波。kernel: 任意大小的核矩阵。"),
    "sepFilter2D": ("cv2.sepFilter2D(src, ddepth, kernelX, kernelY) -> np.ndarray",
                    "可分离线性滤波，效率高于 filter2D。"),
    "fastNlMeansDenoising": ("cv2.fastNlMeansDenoising(src, h=3, templateWindowSize=7, searchWindowSize=21) -> np.ndarray",
                             "非局部均值去噪（灰度图）。"),
    "fastNlMeansDenoisingColored": ("cv2.fastNlMeansDenoisingColored(src, h=3, hColor=3) -> np.ndarray",
                                    "非局部均值去噪（彩色图）。"),
    "pyrDown": ("cv2.pyrDown(src) -> np.ndarray",
                "高斯金字塔下采样（图像缩小一半）。"),
    "pyrUp": ("cv2.pyrUp(src) -> np.ndarray",
              "高斯金字塔上采样（图像放大一倍）。"),

    # ---- 边缘检测与梯度 ----
    "Canny": ("cv2.Canny(image, threshold1, threshold2, apertureSize=3, L2gradient=False) -> np.ndarray",
              "Canny边缘检测。threshold1:低阈值, threshold2:高阈值。推荐比例1:2或1:3。"),
    "Sobel": ("cv2.Sobel(src, ddepth, dx, dy, ksize=3) -> np.ndarray",
              "Sobel梯度算子。dx/dy:求导阶数。ksize:核大小(1,3,5,7)。ddepth:通常用CV_64F。"),
    "Laplacian": ("cv2.Laplacian(src, ddepth, ksize=1) -> np.ndarray",
                  "Laplacian 边缘检测，计算图像的二阶导数。"),
    "Scharr": ("cv2.Scharr(src, ddepth, dx, dy) -> np.ndarray",
               "Scharr 梯度算子（3x3 优化核，比 Sobel 精度更高）。"),

    # ---- 阈值与二值化 ----
    "threshold": ("cv2.threshold(src, thresh, maxval, type) -> (retval, dst)",
                  "固定阈值二值化。type: THRESH_BINARY, THRESH_BINARY_INV, THRESH_TRUNC, THRESH_TOZERO, THRESH_OTSU"),
    "adaptiveThreshold": ("cv2.adaptiveThreshold(src, maxValue, adaptiveMethod, thresholdType, blockSize, C) -> np.ndarray",
                          "自适应阈值。blockSize:邻域大小(奇数)。C:从均值减去的常数。"),
    "inRange": ("cv2.inRange(src, lowerb, upperb) -> np.ndarray",
                "颜色范围过滤，返回二值掩膜。常用于 HSV 空间颜色分割。"),

    # ---- 几何变换 ----
    "resize": ("cv2.resize(src, dsize, fx=0, fy=0, interpolation=INTER_LINEAR) -> np.ndarray",
               "缩放图像。dsize:目标尺寸(w,h)。或通过fx/fy指定比例因子。"),
    "warpAffine": ("cv2.warpAffine(src, M, dsize) -> np.ndarray",
                   "仿射变换（旋转、平移、缩放、剪切）。M: 2x3 变换矩阵。"),
    "warpPerspective": ("cv2.warpPerspective(src, M, dsize) -> np.ndarray",
                        "透视变换（投影变换）。M: 3x3 变换矩阵。"),
    "getRotationMatrix2D": ("cv2.getRotationMatrix2D(center, angle, scale) -> np.ndarray(2x3)",
                            "计算 2D 旋转矩阵（配合 warpAffine 使用）。"),
    "getAffineTransform": ("cv2.getAffineTransform(src_pts, dst_pts) -> np.ndarray(2x3)",
                           "从三对点计算仿射变换矩阵。"),
    "getPerspectiveTransform": ("cv2.getPerspectiveTransform(src_pts, dst_pts) -> np.ndarray(3x3)",
                                "从四对点计算透视变换矩阵。"),
    "remap": ("cv2.remap(src, map1, map2, interpolation) -> np.ndarray",
              "通用重映射（极坐标变换、畸变校正等）。"),
    "flip": ("cv2.flip(src, flipCode) -> np.ndarray",
             "翻转图像。0=垂直, 1=水平, -1=双向。"),

    # ---- 形态学 ----
    "dilate": ("cv2.dilate(src, kernel, iterations=1) -> np.ndarray",
               "膨胀（扩大亮区域），闭合小孔洞。"),
    "erode": ("cv2.erode(src, kernel, iterations=1) -> np.ndarray",
              "腐蚀（缩小亮区域），去除小噪点。"),
    "morphologyEx": ("cv2.morphologyEx(src, op, kernel, iterations=1) -> np.ndarray",
                     "形态学操作。op: MORPH_OPEN(开运算), MORPH_CLOSE(闭运算), MORPH_GRADIENT(梯度), MORPH_TOPHAT, MORPH_BLACKHAT"),
    "getStructuringElement": ("cv2.getStructuringElement(shape, ksize) -> np.ndarray",
                              "创建结构元素。shape: MORPH_RECT, MORPH_ELLIPSE, MORPH_CROSS。"),

    # ---- 轮廓 ----
    "findContours": ("cv2.findContours(image, mode, method) -> contours, hierarchy",
                     "查找轮廓。mode: RETR_EXTERNAL(仅外轮廓), RETR_TREE(全部)。method: CHAIN_APPROX_SIMPLE(压缩), CHAIN_APPROX_NONE"),
    "drawContours": ("cv2.drawContours(image, contours, contourIdx, color, thickness) -> np.ndarray",
                     "绘制轮廓。contourIdx=-1 绘制全部。"),
    "contourArea": ("cv2.contourArea(contour) -> float",
                    "计算轮廓面积。"),
    "arcLength": ("cv2.arcLength(curve, closed) -> float",
                  "计算轮廓周长。closed=True 表示闭合曲线。"),
    "approxPolyDP": ("cv2.approxPolyDP(curve, epsilon, closed) -> np.ndarray",
                     "轮廓多边形逼近。epsilon 为逼近精度（如 0.01*周长）。"),
    "convexHull": ("cv2.convexHull(points, returnPoints=True) -> np.ndarray",
                   "计算凸包。"),
    "boundingRect": ("cv2.boundingRect(points) -> (x, y, w, h)",
                     "计算点集的直立外接矩形。"),
    "minAreaRect": ("cv2.minAreaRect(points) -> ((cx,cy), (w,h), angle)",
                    "计算最小外接旋转矩形。"),
    "minEnclosingCircle": ("cv2.minEnclosingCircle(points) -> ((cx,cy), r)",
                           "计算最小外接圆。"),
    "fitEllipse": ("cv2.fitEllipse(points) -> ((cx,cy), (w,h), angle)",
                   "拟合椭圆。"),
    "moments": ("cv2.moments(array) -> dict",
                "计算图像矩（用于求质心、面积、方向等）。"),

    # ---- 绘图 ----
    "rectangle": ("cv2.rectangle(img, pt1, pt2, color, thickness=-1) -> np.ndarray",
                  "绘制矩形。thickness=-1 为填充。"),
    "circle": ("cv2.circle(img, center, radius, color, thickness=-1) -> np.ndarray",
               "绘制圆。thickness=-1 为填充。"),
    "line": ("cv2.line(img, pt1, pt2, color, thickness=1) -> np.ndarray",
             "绘制直线。"),
    "ellipse": ("cv2.ellipse(img, center, axes, angle, startAngle, endAngle, color, thickness=-1) -> np.ndarray",
                "绘制椭圆/弧。"),
    "polylines": ("cv2.polylines(img, [pts], isClosed, color, thickness=1) -> np.ndarray",
                  "绘制多边形折线。"),
    "fillPoly": ("cv2.fillPoly(img, [pts], color) -> np.ndarray",
                 "填充多边形。"),
    "arrowedLine": ("cv2.arrowedLine(img, pt1, pt2, color, thickness=1) -> np.ndarray",
                    "绘制带箭头的直线。"),
    "putText": ("cv2.putText(img, text, org, fontFace, fontScale, color, thickness=1) -> np.ndarray",
                "在图像上绘制文字。fontFace: FONT_HERSHEY_SIMPLEX 等。"),
    "getTextSize": ("cv2.getTextSize(text, fontFace, fontScale, thickness) -> ((w,h), baseline)",
                    "获取文字渲染后的尺寸。"),

    # ---- 图像运算 ----
    "bitwise_and": ("cv2.bitwise_and(src1, src2, mask=None) -> np.ndarray",
                    "按位与，常用于掩膜提取。"),
    "bitwise_or": ("cv2.bitwise_or(src1, src2, mask=None) -> np.ndarray",
                   "按位或。"),
    "bitwise_not": ("cv2.bitwise_not(src) -> np.ndarray",
                    "按位取反。"),
    "bitwise_xor": ("cv2.bitwise_xor(src1, src2, mask=None) -> np.ndarray",
                    "按位异或。"),
    "add": ("cv2.add(src1, src2) -> np.ndarray",
            "图像加法（饱和运算，最大值255）。"),
    "subtract": ("cv2.subtract(src1, src2) -> np.ndarray",
                 "图像减法（饱和运算，最小值0）。"),
    "multiply": ("cv2.multiply(src1, src2) -> np.ndarray",
                 "图像乘法（饱和运算）。"),
    "divide": ("cv2.divide(src1, src2) -> np.ndarray",
               "图像除法（饱和运算）。"),
    "addWeighted": ("cv2.addWeighted(src1, alpha, src2, beta, gamma) -> np.ndarray",
                    "加权混合。dst = src1*alpha + src2*beta + gamma。"),
    "absdiff": ("cv2.absdiff(src1, src2) -> np.ndarray",
                "计算两幅图像绝对差值。"),
    "split": ("cv2.split(m) -> list[np.ndarray]",
              "分离多通道为单通道列表。"),
    "merge": ("cv2.merge(mv) -> np.ndarray",
              "合并单通道列表为多通道。"),

    # ---- 直方图 ----
    "calcHist": ("cv2.calcHist(images, channels, mask, histSize, ranges) -> np.ndarray",
                 "计算直方图。channels:[0]灰度,[0,1,2]BGR。histSize:[256]。ranges:[0,256]。"),
    "equalizeHist": ("cv2.equalizeHist(src) -> np.ndarray",
                     "直方图均衡化（仅灰度图）。"),
    "compareHist": ("cv2.compareHist(H1, H2, method) -> float",
                    "比较两个直方图的相似度。"),
    "calcBackProject": ("cv2.calcBackProject(images, channels, hist, ranges, scale=1) -> np.ndarray",
                        "反向投影（肤色检测等颜色分割用）。"),

    # ---- 模板匹配 ----
    "matchTemplate": ("cv2.matchTemplate(image, templ, method) -> np.ndarray",
                      "模板匹配。method: TM_CCOEFF_NORMED(推荐), TM_SQDIFF_NORMED, TM_CCORR_NORMED。"),
    "minMaxLoc": ("cv2.minMaxLoc(src) -> (minVal, maxVal, minLoc, maxLoc)",
                  "查找数组中的最小/最大值及其位置。"),

    # ---- 霍夫变换 ----
    "HoughLines": ("cv2.HoughLines(image, rho, theta, threshold) -> lines",
                   "标准霍夫直线检测。返回 (rho, theta) 数组。"),
    "HoughLinesP": ("cv2.HoughLinesP(image, rho, theta, threshold, minLineLength=0, maxLineGap=0) -> lines",
                    "概率霍夫直线检测。返回 (x1,y1,x2,y2) 数组。"),
    "HoughCircles": ("cv2.HoughCircles(image, method, dp, minDist, param1=100, param2=100) -> circles",
                     "霍夫圆检测。param1:Canny高阈值, param2:累加器阈值。"),

    # ---- 特征检测 ----
    "goodFeaturesToTrack": ("cv2.goodFeaturesToTrack(image, maxCorners, qualityLevel, minDistance) -> corners",
                            "Shi-Tomasi 角点检测。maxCorners:最大角点数, qualityLevel:质量阈值(0.01~0.1)。"),
    "cornerHarris": ("cv2.cornerHarris(src, blockSize, ksize, k) -> np.ndarray",
                     "Harris 角点检测。返回每个像素的角点响应。"),
    "cornerSubPix": ("cv2.cornerSubPix(image, corners, winSize, zeroZone, criteria) -> corners",
                     "角点亚像素精度优化。"),

    # ---- 标定 ----
    "findChessboardCorners": ("cv2.findChessboardCorners(image, patternSize) -> (ret, corners)",
                              "检测棋盘格角点（相机标定用）。"),
    "undistort": ("cv2.undistort(src, cameraMatrix, distCoeffs) -> np.ndarray",
                  "畸变校正，去除镜头畸变。"),

    # ---- 分割 ----
    "grabCut": ("cv2.grabCut(img, mask, rect, bgdModel, fgdModel, iterCount, mode=GC_INIT_WITH_RECT) -> mask",
                "GrabCut 图像分割（矩形初始化）。"),
    "watershed": ("cv2.watershed(image, markers) -> markers",
                  "分水岭分割算法。"),
    "distanceTransform": ("cv2.distanceTransform(src, distanceType, maskSize) -> np.ndarray",
                          "距离变换。distanceType: DIST_L2(欧氏), DIST_L1(曼哈顿)。"),
    "connectedComponents": ("cv2.connectedComponents(image, connectivity=8) -> (retval, labels)",
                            "连通组件分析。返回组件数和标签图。"),
    "floodFill": ("cv2.floodFill(image, mask, seedPoint, newVal) -> (retval, image, mask, rect)",
                  "漫水填充。从种子点开始填充连通区域。"),

    # ---- 视频 ----
    "VideoCapture": ("cv2.VideoCapture(index_or_path) -> VideoCapture",
                     "打开摄像头或视频文件。read()读取一帧, release()释放。"),
    "VideoWriter": ("cv2.VideoWriter(filename, fourcc, fps, frameSize, isColor=True) -> VideoWriter",
                    "写入视频文件。fourcc: cv2.VideoWriter_fourcc(*'XVID')。"),
    "calcOpticalFlowPyrLK": ("cv2.calcOpticalFlowPyrLK(prevImg, nextImg, prevPts, nextPts) -> (nextPts, status, err)",
                             "Lucas-Kanade 稀疏光流。"),
}


def _find_func_on_line(line_text: str) -> Optional[str]:
    m = re.search(r'cv2\.(\w+)\s*\(', line_text)
    if m:
        return m.group(1)
    m = re.search(r'np\.(\w+)\s*\(', line_text)
    if m:
        return f"np.{m.group(1)}"
    return None


def get_func_info(func_name: str) -> Tuple[str, str]:
    """获取 (签名, 说明)。优先查库，否则动态获取真实 __doc__。"""
    key = func_name
    for prefix in ("cv2.", "np."):
        if key.startswith(prefix):
            key = key[len(prefix):]

    if key in _FUNC_DESCRIPTIONS:
        return _FUNC_DESCRIPTIONS[key]

    # 动态 fallback: 从 cv2/np 任意层级获取 docstring
    try:
        obj = None
        if func_name.startswith("cv2."):
            obj = cv2
            for part in func_name.replace("cv2.", "").split("."):
                obj = getattr(obj, part, None)
                if obj is None:
                    break
        elif func_name.startswith("np."):
            obj = np
            for part in func_name.replace("np.", "").split("."):
                obj = getattr(obj, part, None)
                if obj is None:
                    break

        if obj is not None and getattr(obj, "__doc__", None):
            doc = obj.__doc__
            lines = [ln.strip() for ln in doc.strip().split('\n') if ln.strip()]
            if lines:
                first = lines[0]
                sig_match = re.match(r'^(\w+\.)?(\w+)\((.*?)\)', first)
                if sig_match:
                    sig = f"{func_name}({sig_match.group(3)})"
                    desc = lines[1] if len(lines) > 1 else first
                else:
                    sig = f"{func_name}(...)"
                    desc = first
                return (sig, desc if desc else "无说明")
    except Exception:
        pass

    return (f"{func_name}(...)", "暂无说明（该函数可正常运行，仅缺少文档记录）")


class FunctionDocPanel(QDockWidget):
    """显示当前行 OpenCV/np 函数的文档。可拖动。"""

    def __init__(self, parent=None):
        super().__init__("函数说明", parent)
        self.setObjectName("function_doc_panel")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.setMinimumHeight(80)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 10))
        self._text.setMaximumHeight(150)
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
