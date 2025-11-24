#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
激光跟踪红点（CSI摄像头版本）
"""

import sys
import os
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import cv2
import numpy as np
import json
import time
from picamera2 import Picamera2
from control.galvo.galvo_controller import GalvoController


class RedTrackerCSI:
    """红点跟踪器（使用CSI摄像头）"""
    
    def __init__(self):
        """初始化"""
        # 振镜控制器（指定仿射参数文件路径）
        # 使用绝对路径确保正确加载
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        affine_params_path = os.path.join(project_root, "control/galvo/calib/affine_params.json")
        self.galvo = GalvoController(affine_params_file=affine_params_path)
        
        # 加载双目参数
        with open("./calib/stereo_params.json", 'r') as f:
            params = json.load(f)
        self.Q = np.array(params['stereo']['Q'])
        
        # 图像尺寸（用于坐标系转换）
        self.image_width = params['image_size'][0]
        self.image_height = params['image_size'][1]
        self.cx = self.image_width / 2
        self.cy = self.image_height / 2
        
        # 加载校正映射
        maps = np.load("./calib/stereo_maps.npz")
        self.map1_left = maps['map1_left']
        self.map2_left = maps['map2_left']
        self.map1_right = maps['map1_right']
        self.map2_right = maps['map2_right']
        
        # 检测阈值
        self.threshold = 100
        
        # 显示开关
        # self.show_display = True
        self.show_display = False
        
        # 是否使用校正（关闭可提升速度，但3D精度会降低）
        self.use_rectification = False  # True=校正（精确）, False=不校正（快速）
        
        # 是否使用形态学去噪（关闭可提升速度，适合清晰红点）
        self.use_morphology = False  # True=去噪（精确）, False=跳过（极速）
        
        # 标定深度（仿射变换标定时的深度）
        self.calibration_depth = 1000.0  # mm
        
        self.offset_x = 100.0 # x轴偏移 mm
        self.offset_y = 50.0 # y轴偏移 mm

        # 初始化双目相机
        self._init_cameras()
        
        print("[跟踪器] 已启动")
        print(f"[提示] 仿射变换标定深度: {self.calibration_depth}mm")
        print(f"[优化] 校正: {'开' if self.use_rectification else '关'} | "
              f"形态学去噪: {'开' if self.use_morphology else '关'} | "
              f"图像显示: {'开' if self.show_display else '关'}")
    
    def _init_cameras(self):
        """初始化双目CSI相机"""
        # 相机配置
        FPS = 100
        # FPS = 30
        # FPS = 10
        RESOLUTION = (640, 480)  # 默认分辨率
        # RESOLUTION = (320, 240)  # 低分辨率，速度更快（校正时间减半）
        
        frame_duration = int(1000000 / FPS)
        
        # 初始化左相机（CAM1）
        print("[相机] 初始化左摄像头...")
        self.cam_left = Picamera2(1)
        config_left = self.cam_left.create_preview_configuration(
            main={"size": RESOLUTION, "format": "RGB888"}
        )
        self.cam_left.configure(config_left)
        self.cam_left.set_controls({
            "FrameDurationLimits": (frame_duration, frame_duration),
            "AwbEnable": True,
            "AeEnable": True
        })
        self.cam_left.start()
        
        # 初始化右相机（CAM0）
        print("[相机] 初始化右摄像头...")
        self.cam_right = Picamera2(0)
        config_right = self.cam_right.create_preview_configuration(
            main={"size": RESOLUTION, "format": "RGB888"}
        )
        self.cam_right.configure(config_right)
        self.cam_right.set_controls({
            "FrameDurationLimits": (frame_duration, frame_duration),
            "AwbEnable": True,
            "AeEnable": True
        })
        self.cam_right.start()
        
        print(f"[相机] 分辨率: {RESOLUTION}, 帧率: {FPS} fps")
    
    def detect_red(self, frame):
        """检测红色点（优化版）"""
        # 优化1: 避免split，直接用整数运算（比float32快）
        # frame是BGR格式：frame[:,:,0]=B, frame[:,:,1]=G, frame[:,:,2]=R
        b = frame[:, :, 0].astype(np.int16)
        g = frame[:, :, 1].astype(np.int16)
        r = frame[:, :, 2].astype(np.int16)
        
        # 红色检测：R - (G+B)/2 > threshold
        red_diff = r - ((g + b) >> 1)  # 右移1位 = 除以2，更快
        mask = (red_diff > self.threshold).astype(np.uint8) * 255
        
        # 优化2: 可选的形态学去噪
        if self.use_morphology:
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 优化3: 查找轮廓
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
        """
        计算3D坐标
        
        返回:
            (X, Y, Z) - 中心为原点，x右正，y上正
        """
        if left_pt is None or right_pt is None:
            return None
        
        disparity = left_pt[0] - right_pt[0]
        if disparity <= 0:
            return None
        
        # 使用Q矩阵计算3D坐标
        point_4d = self.Q @ [left_pt[0], left_pt[1], disparity, 1.0]
        
        # 归一化并转换坐标系
        X = point_4d[0] / point_4d[3]
        Y = -point_4d[1] / point_4d[3]  # Y轴反转（图像坐标向下，改为向上）
        Z = point_4d[2] / point_4d[3]
        
        return (X, Y, Z)
    
    def run(self):
        """运行跟踪"""
        print("\n[运行] 控制:")
        print("  'd': 切换图像显示")
        print("  'q': 退出")
        
        while True:
            t_start = time.perf_counter()
            
            # 采集双目图像
            t0 = time.perf_counter()
            frame_left = self.cam_left.capture_array()
            frame_right = self.cam_right.capture_array()
            t_capture = (time.perf_counter() - t0) * 1000  # ms

            # 校正图像（可选）
            t0 = time.perf_counter()
            if self.use_rectification:
                left = cv2.remap(frame_left, self.map1_left, self.map2_left, cv2.INTER_LINEAR)
                right = cv2.remap(frame_right, self.map1_right, self.map2_right, cv2.INTER_LINEAR)
            else:
                left = frame_left
                right = frame_right
            t_remap = (time.perf_counter() - t0) * 1000  # ms
            
            # 检测红色点
            t0 = time.perf_counter()
            left_pt = self.detect_red(left)
            right_pt = self.detect_red(right)
            t_detect = (time.perf_counter() - t0) * 1000  # ms
            
            # 显示图像（如果开启）
            t0 = time.perf_counter()
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
                
                cv2.imshow('Red Tracker CSI', display)
            t_display = (time.perf_counter() - t0) * 1000  # ms
            
            # 计算3D坐标并移动激光
            t_calc = 0
            t_move = 0
            if left_pt and right_pt:
                # 计算3D坐标
                t0 = time.perf_counter()
                target_3d = self.calculate_3d(left_pt, right_pt)
                t_calc = (time.perf_counter() - t0) * 1000  # ms
                
                if target_3d:
                    try:
                        # 根据实际深度调整XY坐标
                        # 仿射变换在calibration_depth标定，需要根据实际深度比例调整
                        depth_ratio = self.calibration_depth / target_3d[2]
                        target_x = target_3d[0] * depth_ratio
                        target_y = target_3d[1] * depth_ratio

                        target_x += self.offset_x
                        target_y += self.offset_y
                        
                        # 移动激光
                        t0 = time.perf_counter()
                        self.galvo.move_to_physical(target_x, target_y)
                        t_move = (time.perf_counter() - t0) * 1000  # ms
                        
                        # 获取RGB值和红色差值
                        b, g, r = left[left_pt[1], left_pt[0]]
                        red_diff = r - (g + b) / 2
                        
                        # 总循环时间（不包括waitKey，因为它在后面）
                        t_measured = t_capture + t_remap + t_detect + t_display + t_calc + t_move
                        t_total_before_wait = (time.perf_counter() - t_start) * 1000  # ms
                        t_other = t_total_before_wait - t_measured  # 其他开销（打印等）
                        

                        # 1. 只打印一行，不换行
                        # print(f"\r跟踪: 3D=({target_3d[0]:5.1f},{target_3d[1]:5.1f},{target_3d[2]:5.1f})mm | "
                        #       f"目标=({target_x:5.1f},{target_y:5.1f})mm | "
                        #       f"时间: 采集{t_capture:.1f} 校正{t_remap:.1f} 检测{t_detect:.1f} "
                        #       f"显示{t_display:.1f} 计算{t_calc:.1f} 移动{t_move:.1f} 其他{t_other:.1f} 总{t_total_before_wait:.1f}ms",
                        #       end='', flush=True)
                        # 2. 逐行打印
                        print(f"跟踪: 3D=({target_3d[0]:5.1f},{target_3d[1]:5.1f},{target_3d[2]:5.1f})mm | "
                              f"目标=({target_x:5.1f},{target_y:5.1f})mm | "
                              f"时间: 采集{t_capture:.1f} 校正{t_remap:.1f} 检测{t_detect:.1f} "
                              f"显示{t_display:.1f} 计算{t_calc:.1f} 移动{t_move:.1f} 其他{t_other:.1f} 总{t_total_before_wait:.1f}ms")
                    except Exception as e:
                        print(f"\n[错误] 移动失败: {e}")
                else:
                    print("\r[警告] 视差无效，无法计算3D坐标", end='', flush=True)
            
            # 等待键盘输入（也会刷新窗口显示）
            t0 = time.perf_counter()
            key = cv2.waitKey(1) & 0xFF
            t_waitkey = (time.perf_counter() - t0) * 1000  # ms
            
            if key == ord('q'):
                break
            elif key == ord('d'):
                self.show_display = not self.show_display
                if not self.show_display:
                    cv2.destroyAllWindows()
                print(f"\n[显示] {'开启' if self.show_display else '关闭'}")
        
        self.close()
        print("\n[退出]")
    
    def close(self):
        """关闭资源"""
        self.cam_left.stop()
        self.cam_right.stop()
        cv2.destroyAllWindows()
        self.galvo.close()


if __name__ == "__main__":
    tracker = RedTrackerCSI()
    tracker.run()

