#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
激光跟踪红点（简化版）
"""

import sys
import os
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import cv2
import numpy as np
import json
from control.galvo.galvo_controller import GalvoController


class RedTracker:
    """红点跟踪器"""
    
    def __init__(self):
        """初始化"""
        # 振镜控制器
        self.galvo = GalvoController()
        
        # 加载双目参数
        with open("./calib/stereo_params.json", 'r') as f:
            params = json.load(f)
        self.Q = np.array(params['stereo']['Q'])
        
        # 加载校正映射
        maps = np.load("./calib/stereo_maps.npz")
        self.map1_left = maps['map1_left']
        self.map2_left = maps['map2_left']
        self.map1_right = maps['map1_right']
        self.map2_right = maps['map2_right']
        
        # 检测阈值
        self.threshold = 50
        
        # 显示开关
        self.show_display = True
        
        print("[跟踪器] 已启动")
    
    def detect_red(self, frame):
        """检测红色点"""
        b, g, r = cv2.split(frame)
        b = b.astype(np.float32)
        g = g.astype(np.float32)
        r = r.astype(np.float32)
        
        # 红色检测
        mask = (r - (g + b) / 2 > self.threshold).astype(np.uint8) * 255
        
        # 去噪
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # 最大轮廓中心
        largest = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest)
        
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return (cx, cy)
        
        return None
    
    def calculate_3d(self, left_pt, right_pt):
        """计算3D坐标（Y轴反转）"""
        if left_pt is None or right_pt is None:
            return None
        
        disparity = left_pt[0] - right_pt[0]
        if disparity <= 0:
            return None
        
        point_4d = self.Q @ [left_pt[0], left_pt[1], disparity, 1.0]
        return (point_4d[0] / point_4d[3], 
                -point_4d[1] / point_4d[3],  # Y轴反转
                point_4d[2] / point_4d[3])
    
    def run(self):
        """运行跟踪"""
        # 打开摄像头
        # # 1. 高分辨率
        # cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        # cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
        # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # 2. 高帧率
        # cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        cap = cv2.VideoCapture(16, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # 获取并打印摄像头参数
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
        
        print("\n[摄像头参数]")
        print(f"  分辨率: {int(width)}x{int(height)}")
        print(f"  帧率: {fps:.1f} fps")
        print(f"  图像格式: {fourcc_str}")
        print()
        print("[运行] 控制:")
        print("  'd': 切换图像显示")
        print("  'q': 退出")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 分离左右图像并校正
            left = cv2.remap(frame[:, :1280], self.map1_left, self.map2_left, cv2.INTER_LINEAR)
            right = cv2.remap(frame[:, 1280:], self.map1_right, self.map2_right, cv2.INTER_LINEAR)
            
            # 检测红色点
            left_pt = self.detect_red(left)
            right_pt = self.detect_red(right)
            
            # 显示图像（如果开启）
            if self.show_display:
                display = left.copy()
                
                # 绘制红色点
                if left_pt:
                    cv2.circle(display, left_pt, 10, (0, 255, 0), 2)
                    cv2.drawMarker(display, left_pt, (0, 255, 0), 
                                  cv2.MARKER_CROSS, 20, 2)
                    cv2.putText(display, f"Target: {left_pt}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # 显示RGB值和红色差值
                    b, g, r = left[left_pt[1], left_pt[0]]
                    red_diff = r - (g + b) / 2
                    cv2.putText(display, f"RGB: ({r}, {g}, {b})", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    cv2.putText(display, f"Red Diff: {red_diff:.1f}", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                cv2.imshow('Red Tracker', display)
            
            # 计算3D坐标并移动激光
            if left_pt and right_pt:
                target_3d = self.calculate_3d(left_pt, right_pt)
                
                if target_3d:
                    try:
                        self.galvo.move_to_physical(target_3d[0] + 27, target_3d[1] - 3)
                        
                        # 获取RGB值和红色差值
                        b, g, r = left[left_pt[1], left_pt[0]]
                        red_diff = r - (g + b) / 2
                        
                        print(f"\r跟踪: ({target_3d[0]:6.1f}, {target_3d[1]:6.1f}, {target_3d[2]:6.1f})mm | "
                              f"RGB: ({r:3d}, {g:3d}, {b:3d}) | Diff: {red_diff:5.1f}",
                              end='', flush=True)
                    except:
                        pass
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                self.show_display = not self.show_display
                if not self.show_display:
                    cv2.destroyAllWindows()
                print(f"\n[显示] {'开启' if self.show_display else '关闭'}")
        
        cap.release()
        cv2.destroyAllWindows()
        self.galvo.close()
        print("\n[退出]")


if __name__ == "__main__":
    tracker = RedTracker()
    tracker.run()
