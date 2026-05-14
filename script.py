# OpenCV IDE — 交互式视觉编程
# F6 单步执行，F5 运行全部，Esc 停止
import cv2
import numpy as np

# === 参数区（控制变量窗口会显示这些变量） ===
blur_ksize = (5, 5)       # 高斯模糊核大小
canny_low = 30            # Canny 低阈值
canny_high = 200           # Canny 高阈值

# === 图像处理流程 ===
img = cv2.imread(r"C:\Users\gaoyu\Desktop\HdevelopInerface.png")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

blur = cv2.GaussianBlur(gray, blur_ksize, 0)

edges = cv2.Canny(blur, canny_low, canny_high)
print(f"edges: {edges.shape}, dtype={edges.dtype}")
