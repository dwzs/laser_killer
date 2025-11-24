#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
识别红色点并计算3D坐标（CSI相机版本）
使用双目标定参数和立体匹配
"""

import cv2
import numpy as np
import json
from picamera2 import Picamera2


class DepthCalculator:
    """深度计算器"""
    
    def __init__(self, params_file="stereo_params.json", maps_file="stereo_maps.npz"):
        """初始化"""
        # 加载标定参数
        with open(params_file, 'r') as f:
            self.params = json.load(f)
        
        # 加载校正映射
        maps = np.load(maps_file)
        self.map1_left = maps['map1_left']
        self.map2_left = maps['map2_left']
        self.map1_right = maps['map1_right']
        self.map2_right = maps['map2_right']
        
        # Q矩阵（视差转3D）
        self.Q = np.array(self.params['stereo']['Q'])
        
        # 基线和焦距
        self.baseline = abs(self.params['stereo']['baseline'])
        self.fx = self.params['left_camera']['projection'][0][0]
        
        # 图像尺寸（用于坐标系转换）
        self.image_width = self.params['image_size'][0]
        self.image_height = self.params['image_size'][1]
        self.cx = self.image_width / 2
        self.cy = self.image_height / 2
        
        # RGB通道差值阈值（检测红色）
        self.threshold = 50
        
        print("[初始化] 深度计算器")
        print(f"  基线: {self.baseline:.1f}mm")
        print(f"  焦距: {self.fx:.1f}px")
        print(f"  图像尺寸: {self.image_width}x{self.image_height}")
        print(f"  坐标系: 中心为原点(0,0), x右正, y上正")
    
    def detect_red_spot(self, frame):
        """
        检测红色点
        
        参数:
            frame: BGR图像
        
        返回:
            (cx, cy) 中心坐标，若未检测到返回None
        """
        # 高斯模糊
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        
        # 分离BGR通道
        b, g, r = cv2.split(blurred)
        b = b.astype(np.float32)
        g = g.astype(np.float32)
        r = r.astype(np.float32)
        
        # 红色检测：R通道比(G+B)/2平均高出threshold
        other_avg = (g + b) / 2
        red_mask = (r - other_avg > self.threshold).astype(np.uint8) * 255
        
        # 形态学操作
        kernel = np.ones((3, 3), np.uint8)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # 获取最大轮廓中心
        largest = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest)
        
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return (cx, cy)
        
        return None
    
    def calculate_depth(self, left_point, right_point):
        """
        计算深度
        
        参数:
            left_point: 左图点坐标 (x, y) - 图像坐标系
            right_point: 右图点坐标 (x, y) - 图像坐标系
        
        返回:
            (X, Y, Z) 3D坐标 (mm) - 中心为原点，x右正，y上正
        """
        if left_point is None or right_point is None:
            return None
        
        # 将图像坐标转换为以中心为原点的坐标系（y轴向上）
        # x: 图像坐标系向右为正，转换后也向右为正
        # y: 图像坐标系向下为正，转换后向上为正
        left_x = left_point[0] - self.cx
        left_y = self.cy - left_point[1]  # 反转y轴
        right_x = right_point[0] - self.cx
        right_y = self.cy - right_point[1]  # 反转y轴
        
        # 计算视差（使用原始图像坐标）
        disparity = left_point[0] - right_point[0]
        
        if disparity <= 0:
            return None
        
        # 使用Q矩阵计算3D坐标（使用转换后的坐标）
        # 注意：Q矩阵是基于图像左上角为原点的，所以需要用原始坐标
        point_4d = self.Q @ [left_point[0], left_point[1], disparity, 1.0]
        
        # 归一化并转换坐标系
        X = point_4d[0] / point_4d[3]
        Y = -point_4d[1] / point_4d[3]  # Y轴反转（图像坐标向下，改为向上）
        Z = point_4d[2] / point_4d[3]
        
        # X坐标平移到中心为原点（如果Q矩阵没有包含这个平移）
        # 这取决于标定时的光心位置，通常Q矩阵已经考虑了这一点
        
        return (X, Y, Z)
    
    def calculate_depth_simple(self, disparity):
        """
        简单深度计算（仅Z方向）
        
        参数:
            disparity: 视差（像素）
        
        返回:
            深度Z (mm)
        """
        if disparity <= 0:
            return None
        
        return (self.baseline * self.fx) / disparity
    
    def run(self):
        """运行实时检测（CSI相机）"""
        # 初始化CSI双目相机
        print("\n[相机] 初始化CSI双目相机...")
        FPS = 40
        RESOLUTION = (640, 480)
        frame_duration = int(1000000 / FPS)
        
        # 左相机 (CAM1)
        cam_left = Picamera2(1)
        config_left = cam_left.create_preview_configuration(
            main={"size": RESOLUTION, "format": "RGB888"}
        )
        cam_left.configure(config_left)
        cam_left.set_controls({"FrameDurationLimits": (frame_duration, frame_duration)})
        cam_left.start()
        
        # 右相机 (CAM0)
        cam_right = Picamera2(0)
        config_right = cam_right.create_preview_configuration(
            main={"size": RESOLUTION, "format": "RGB888"}
        )
        cam_right.configure(config_right)
        cam_right.set_controls({"FrameDurationLimits": (frame_duration, frame_duration)})
        cam_right.start()
        
        print("[运行] 按 'q' 退出")
        
        try:
            while True:
                # 采集双目图像
                frame_left = cam_left.capture_array()
                frame_right = cam_right.capture_array()
                
                # 校正图像
                left_rect = cv2.remap(frame_left, self.map1_left, self.map2_left, cv2.INTER_LINEAR)
                right_rect = cv2.remap(frame_right, self.map1_right, self.map2_right, cv2.INTER_LINEAR)
                
                # 检测红色点
                left_point = self.detect_red_spot(left_rect)
                right_point = self.detect_red_spot(right_rect)
                
                # 显示
                display_left = left_rect.copy()
                display_right = right_rect.copy()
                
                # 绘制检测结果
                if left_point:
                    cv2.circle(display_left, left_point, 10, (0, 0, 255), 2)
                    cv2.putText(display_left, f"L: {left_point}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                if right_point:
                    cv2.circle(display_right, right_point, 10, (0, 0, 255), 2)
                    cv2.putText(display_right, f"R: {right_point}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # 计算3D坐标
                if left_point and right_point:
                    point_3d = self.calculate_depth(left_point, right_point)
                    
                    if point_3d:
                        X, Y, Z = point_3d
                        disparity = left_point[0] - right_point[0]
                        
                        # 显示3D坐标
                        cv2.putText(display_left, f"X: {X:.1f}mm", (10, 60),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(display_left, f"Y: {Y:.1f}mm", (10, 90),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(display_left, f"Z: {Z:.1f}mm", (10, 120),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(display_left, f"Disp: {disparity:.1f}px", (10, 150),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                        
                        print(f"\r3D坐标: X={X:7.1f}mm, Y={Y:7.1f}mm, Z={Z:7.1f}mm, 视差={disparity:5.1f}px",
                              end='', flush=True)
                
                # 拼接显示
                display = np.hstack([display_left, display_right])
                cv2.imshow('Red Spot Depth Calculation (CSI)', display)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cam_left.stop()
            cam_right.stop()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    calculator = DepthCalculator()
    calculator.run()

