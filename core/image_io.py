import numpy as np
import cv2


def imread_unicode(path: str, flags: int = cv2.IMREAD_COLOR) -> np.ndarray:
    """cv2.imread 替代，支持中文路径。"""
    with open(path, "rb") as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    img = cv2.imdecode(data, flags)
    if img is None:
        raise OSError(f"无法读取图像: {path}")
    return img
