"""pytest 共享 fixtures。"""
import sys
import pytest
import numpy as np
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """会话级 QApplication，所有 GUI 测试共享。"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def sample_image():
    """生成测试用的合成图像。"""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[25:75, 25:75] = (0, 255, 0)
    return img
