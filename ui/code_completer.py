"""代码补全器 —— OpenCV / numpy / Python 内置函数名。"""
from PyQt6.QtWidgets import QCompleter
from PyQt6.QtCore import Qt, QStringListModel


_CV2_FUNCS = [
    "imread", "imwrite", "imdecode", "imencode",
    "cvtColor", "applyColorMap", "LUT",
    "GaussianBlur", "medianBlur", "bilateralFilter", "blur",
    "boxFilter", "filter2D", "sepFilter2D", "Scharr",
    "fastNlMeansDenoising", "fastNlMeansDenoisingColored",
    "pyrDown", "pyrUp",
    "Canny", "Sobel", "Laplacian",
    "threshold", "adaptiveThreshold", "inRange",
    "resize", "warpAffine", "warpPerspective",
    "getRotationMatrix2D", "getAffineTransform",
    "getPerspectiveTransform", "remap", "flip",
    "dilate", "erode", "morphologyEx", "getStructuringElement",
    "findContours", "drawContours",
    "contourArea", "arcLength", "approxPolyDP", "convexHull",
    "boundingRect", "minAreaRect", "minEnclosingCircle",
    "fitEllipse", "moments",
    "rectangle", "circle", "line", "ellipse",
    "polylines", "fillPoly", "arrowedLine",
    "putText", "getTextSize",
    "bitwise_and", "bitwise_or", "bitwise_not", "bitwise_xor",
    "add", "subtract", "multiply", "divide", "addWeighted", "absdiff",
    "split", "merge",
    "calcHist", "equalizeHist", "compareHist", "calcBackProject",
    "matchTemplate", "minMaxLoc",
    "HoughLines", "HoughLinesP", "HoughCircles",
    "goodFeaturesToTrack", "cornerHarris", "cornerSubPix",
    "findChessboardCorners", "undistort",
    "grabCut", "watershed", "distanceTransform",
    "connectedComponents", "floodFill",
    "VideoCapture", "VideoWriter", "calcOpticalFlowPyrLK",
]

_NP_FUNCS = [
    "array", "zeros", "ones", "full", "eye", "arange", "linspace",
    "reshape", "ravel", "flatten", "transpose", "expand_dims",
    "squeeze", "stack", "concatenate", "hstack", "vstack", "split",
    "mean", "std", "var", "min", "max", "argmin", "argmax",
    "sum", "cumsum", "clip", "where", "nonzero", "unique",
    "uint8", "uint16", "int32", "float32", "float64",
    "abs", "sqrt", "sin", "cos", "arctan2", "degrees", "radians",
    "dot", "cross", "random.rand", "random.randint", "random.randn",
]

_PYTHON_FUNCS = [
    "enumerate", "zip", "sorted", "reversed", "filter", "map",
    "range", "len", "str", "int", "float", "bool", "list",
    "dict", "set", "tuple",
]


def _make_model() -> QStringListModel:
    all_funcs = []
    for f in _CV2_FUNCS:
        all_funcs.append(f"cv2.{f}")
        all_funcs.append(f"cv2.{f}(")
    for f in _NP_FUNCS:
        all_funcs.append(f"np.{f}")
        all_funcs.append(f"np.{f}(")
    for f in _PYTHON_FUNCS:
        all_funcs.append(f)
        all_funcs.append(f"{f}(")
    return QStringListModel(sorted(set(all_funcs)))


class CodeCompleter(QCompleter):
    """OpenCV + numpy 代码补全，绑定到 ScriptEditor。"""

    def __init__(self, parent=None):
        super().__init__(_make_model(), parent)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setWrapAround(False)
