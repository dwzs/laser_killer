#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
识别红色点并计算3D坐标
使用双目标定参数和立体匹配
"""

import cv2
import numpy as np
import json


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
        
        # RGB通道差值阈值（检测红色）
        self.threshold = 15
        
        print("[初始化] 深度计算器")
        print(f"  基线: {self.baseline:.1f}mm")
        print(f"  焦距: {self.fx:.1f}px")
    
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
            left_point: 左图点坐标 (x, y)
            right_point: 右图点坐标 (x, y)
        
        返回:
            (X, Y, Z) 3D坐标 (mm)
        """
        if left_point is None or right_point is None:
            return None
        
        # 计算视差
        disparity = left_point[0] - right_point[0]
        
        if disparity <= 0:
            return None
        
        # 使用Q矩阵计算3D坐标
        point_4d = self.Q @ [left_point[0], left_point[1], disparity, 1.0]
        
        # 归一化
        X = point_4d[0] / point_4d[3]
        Y = point_4d[1] / point_4d[3]
        Z = point_4d[2] / point_4d[3]
        
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
        """运行实时检测"""
        # 打开摄像头
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        print("\n[运行] 按 'q' 退出")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 分离左右图像
            left_raw = frame[:, :1280]
            right_raw = frame[:, 1280:]
            
            # 校正图像
            left_rect = cv2.remap(left_raw, self.map1_left, self.map2_left, cv2.INTER_LINEAR)
            right_rect = cv2.remap(right_raw, self.map1_right, self.map2_right, cv2.INTER_LINEAR)
            
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
            cv2.imshow('Red Spot Depth Calculation', display)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    calculator = DepthCalculator()
    calculator.run()

