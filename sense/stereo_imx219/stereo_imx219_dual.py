#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
树莓派双目相机控制脚本
"""

from tkinter.constants import TRUE
import cv2
import numpy as np
from picamera2 import Picamera2


# ==================== 配置参数 ====================
#  640x480 [103.33 fps - (1000, 752)/1280x960 crop]
#  1640x1232 [41.85 fps - (0, 0)/3280x2464 crop]
#  1920x1080 [47.57 fps - (680, 692)/1920x1080 crop]
#  3280x2464 [21.19 fps - (0, 0)/3280x2464 crop]


# 相机选择
ENABLE_CAM_LEFT  = TRUE   # 启用左相机
ENABLE_CAM_RIGHT = TRUE   # 启用右相机
CAM_LEFT_ID = 1           # 左相机物理ID
CAM_RIGHT_ID = 0          # 右相机物理ID

# 左相机参数
CAM_LEFT_CONFIG = {
    "size": (640, 480),    # 分辨率
    "format": "RGB888",      # 图像格式
}
# CAM_LEFT_CONFIG = {
#     "size": (3280, 2464),    # 分辨率
#     "format": "RGB888",      # 图像格式
# }
# CAM_LEFT_CONFIG = {
#     "size": (1920, 1080),    # 分辨率
#     "format": "RGB888",      # 图像格式
# }

# 右相机参数
# CAM_RIGHT_CONFIG = {
#     "size": (1640, 1232),    # 分辨率
#     "format": "RGB888",      # 图像格式
# }
CAM_RIGHT_CONFIG = {
    "size": (640, 480),    # 分辨率
    "format": "RGB888",      # 图像格式
}

# 通用参数
FPS = 40                 # 帧率 (根据分辨率选择合适的值)
                         # 640x480: 最高103fps
                         # 1640x1232: 最高42fps
                         # 1920x1080: 最高48fps
                         # 3280x2464: 最高21fps

# 显示设置
SHOW_DISPLAY = True      # 是否显示图像
SAVE_IMAGES = False      # 是否保存图像

# ==================================================


class StereoCamera:
    """双目相机控制器"""
    
    def __init__(self):
        """初始化相机"""
        self.cameras = []
        
        # 计算帧时间（微秒）
        frame_duration = int(1000000 / FPS)
        
        # 初始化左相机
        if ENABLE_CAM_LEFT:
            print("[左相机] 初始化中...")
            cam_left = Picamera2(CAM_LEFT_ID)
            config_left = cam_left.create_preview_configuration(
                main={"size": CAM_LEFT_CONFIG["size"], "format": CAM_LEFT_CONFIG["format"]}
            )
            cam_left.configure(config_left)
            cam_left.set_controls({
                "FrameDurationLimits": (frame_duration, frame_duration),
                "AwbEnable": True,  # 启用自动白平衡
                "AeEnable": True    # 启用自动曝光
            })
            cam_left.start()
            
            # 获取实际配置
            actual_config = cam_left.camera_configuration()
            main_stream = actual_config["main"]
            print(f"  实际分辨率: {main_stream['size']}")
            print(f"  实际格式: {main_stream['format']}")
            print(f"  目标帧率: {FPS} fps")
            
            self.cameras.append(("Left Camera", cam_left))
        
        # 初始化右相机
        if ENABLE_CAM_RIGHT:
            print("[右相机] 初始化中...")
            cam_right = Picamera2(CAM_RIGHT_ID)
            config_right = cam_right.create_preview_configuration(
                main={"size": CAM_RIGHT_CONFIG["size"], "format": CAM_RIGHT_CONFIG["format"]}
            )
            cam_right.configure(config_right)
            cam_right.set_controls({
                "FrameDurationLimits": (frame_duration, frame_duration),
                "AwbEnable": True,  # 启用自动白平衡
                "AeEnable": True    # 启用自动曝光
            })
            cam_right.start()
            
            # 获取实际配置
            actual_config = cam_right.camera_configuration()
            main_stream = actual_config["main"]
            print(f"  实际分辨率: {main_stream['size']}")
            print(f"  实际格式: {main_stream['format']}")
            print(f"  目标帧率: {FPS} fps")
            
            self.cameras.append(("Right Camera", cam_right))
        
        if not self.cameras:
            raise RuntimeError("未启用任何相机")
        
        print(f"\n[启动] {len(self.cameras)}个相机已就绪")
        print("  按 'q' 退出")
        print("  按 's' 保存图像")
    
    def run(self):
        """运行采集循环"""
        frame_count = 0
        
        while True:
            frames = []
            
            # 采集所有相机的图像
            for name, cam in self.cameras:
                frame = cam.capture_array()
                frames.append((name, frame))
            
            frame_count += 1
            
            # 显示图像
            if SHOW_DISPLAY:
                if len(frames) == 1:
                    # 单个相机
                    cv2.imshow(frames[0][0], frames[0][1])
                elif len(frames) == 2:
                    # 双目相机，并排显示
                    combined = np.hstack([frames[0][1], frames[1][1]])
                    cv2.imshow('Stereo Camera', combined)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # 保存图像
                for name, frame in frames:
                    filename = f"{name.replace(' ', '_').lower()}_{frame_count:04d}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"\n[保存] {filename}")
        
        self.close()
    
    def close(self):
        """关闭相机"""
        for name, cam in self.cameras:
            cam.stop()
            print(f"[关闭] {name}")
        cv2.destroyAllWindows()


if __name__ == "__main__":
    camera = StereoCamera()
    camera.run()

