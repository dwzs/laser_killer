#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双目摄像头标定脚本
"""

import cv2
import numpy as np
import json
import glob
import os


class StereoCalibrator:
    """双目标定器"""
    
    def __init__(self, pattern_size=(7, 4), square_size=30.2):
        """
        初始化
        
        参数:
            pattern_size: 棋盘格内角点数 (列, 行)
            square_size: 方格边长 (mm)
        """
        self.pattern_size = pattern_size
        self.square_size = square_size
        
        # 生成3D世界坐标
        self.objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
        self.objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
        self.objp *= square_size
        
        print(f"[标定器] 棋盘格: {pattern_size[0]}x{pattern_size[1]}, 方格: {square_size}mm")
    
    def capture_images(self, num_images=20, save_dir="calib_images"):
        """
        采集标定图像
        
        参数:
            num_images: 采集图像数量
            save_dir: 保存目录
        """
        # 创建保存目录
        os.makedirs(f"{save_dir}/left", exist_ok=True)
        os.makedirs(f"{save_dir}/right", exist_ok=True)
        
        # 打开摄像头
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        count = 0
        print(f"\n[采集] 按空格拍摄，需要 {num_images} 张图像")
        
        while count < num_images:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 分离左右图像
            left = frame[:, :1280]
            right = frame[:, 1280:]
            
            # 检测角点
            gray_left = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)
            gray_right = cv2.cvtColor(right, cv2.COLOR_BGR2GRAY)
            ret_left, corners_left = cv2.findChessboardCorners(gray_left, self.pattern_size, None)
            ret_right, corners_right = cv2.findChessboardCorners(gray_right, self.pattern_size, None)
            
            # 显示
            display_left = left.copy()
            display_right = right.copy()
            if ret_left:
                cv2.drawChessboardCorners(display_left, self.pattern_size, corners_left, ret_left)
            if ret_right:
                cv2.drawChessboardCorners(display_right, self.pattern_size, corners_right, ret_right)
            
            display = np.hstack([display_left, display_right])
            cv2.putText(display, f"Captured: {count}/{num_images}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow('Stereo Calibration - Press SPACE to capture', display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' ') and ret_left and ret_right:
                # 保存图像
                cv2.imwrite(f"{save_dir}/left/img_{count:02d}.jpg", left)
                cv2.imwrite(f"{save_dir}/right/img_{count:02d}.jpg", right)
                count += 1
                print(f"  已拍摄: {count}/{num_images}")
            elif key == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        print(f"[完成] 采集了 {count} 张图像")
    
    def calibrate_from_images(self, image_dir="calib_images"):
        """
        从图像文件标定
        
        参数:
            image_dir: 图像目录
        
        返回:
            标定参数字典
        """
        # 读取图像
        left_images = sorted(glob.glob(f"{image_dir}/left/*.jpg"))
        right_images = sorted(glob.glob(f"{image_dir}/right/*.jpg"))
        
        if len(left_images) == 0 or len(right_images) == 0:
            raise ValueError("未找到标定图像")
        
        print(f"\n[标定] 找到 {len(left_images)} 对图像")
        
        # 存储角点
        objpoints = []  # 3D点
        imgpoints_left = []  # 左图2D点
        imgpoints_right = []  # 右图2D点
        
        image_size = None
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        
        # 检测所有图像的角点
        for left_path, right_path in zip(left_images, right_images):
            img_left = cv2.imread(left_path)
            img_right = cv2.imread(right_path)
            gray_left = cv2.cvtColor(img_left, cv2.COLOR_BGR2GRAY)
            gray_right = cv2.cvtColor(img_right, cv2.COLOR_BGR2GRAY)
            
            if image_size is None:
                image_size = gray_left.shape[::-1]
            
            # 查找角点
            ret_left, corners_left = cv2.findChessboardCorners(gray_left, self.pattern_size, None)
            ret_right, corners_right = cv2.findChessboardCorners(gray_right, self.pattern_size, None)
            
            if ret_left and ret_right:
                objpoints.append(self.objp)
                
                # 亚像素精度优化
                corners_left = cv2.cornerSubPix(gray_left, corners_left, (11, 11), (-1, -1), criteria)
                corners_right = cv2.cornerSubPix(gray_right, corners_right, (11, 11), (-1, -1), criteria)
                
                imgpoints_left.append(corners_left)
                imgpoints_right.append(corners_right)
                print(f"  ✓ {os.path.basename(left_path)}")
            else:
                print(f"  ✗ {os.path.basename(left_path)} - 角点检测失败")
        
        print(f"\n[有效图像] {len(objpoints)} 对")
        
        if len(objpoints) < 10:
            raise ValueError("有效图像太少，至少需要10对")
        
        # 单目标定 - 左相机
        print("\n[单目标定] 左相机...")
        ret_left, K_left, D_left, rvecs_left, tvecs_left = cv2.calibrateCamera(
            objpoints, imgpoints_left, image_size, None, None
        )
        print(f"  重投影误差: {ret_left:.4f} 像素")
        
        # 单目标定 - 右相机
        print("\n[单目标定] 右相机...")
        ret_right, K_right, D_right, rvecs_right, tvecs_right = cv2.calibrateCamera(
            objpoints, imgpoints_right, image_size, None, None
        )
        print(f"  重投影误差: {ret_right:.4f} 像素")
        
        # 双目标定
        print("\n[双目标定]...")
        flags = cv2.CALIB_FIX_INTRINSIC
        ret_stereo, K_left, D_left, K_right, D_right, R, T, E, F = cv2.stereoCalibrate(
            objpoints, imgpoints_left, imgpoints_right,
            K_left, D_left, K_right, D_right,
            image_size,
            flags=flags,
            criteria=criteria
        )
        print(f"  重投影误差: {ret_stereo:.4f} 像素")
        
        # 立体校正
        print("\n[立体校正]...")
        R1, R2, P1, P2, Q, roi_left, roi_right = cv2.stereoRectify(
            K_left, D_left, K_right, D_right,
            image_size, R, T,
            alpha=0
        )
        
        # 计算校正映射
        map1_left, map2_left = cv2.initUndistortRectifyMap(
            K_left, D_left, R1, P1, image_size, cv2.CV_32FC1
        )
        map1_right, map2_right = cv2.initUndistortRectifyMap(
            K_right, D_right, R2, P2, image_size, cv2.CV_32FC1
        )
        
        # 组织参数
        params = {
            "pattern_size": self.pattern_size,
            "square_size": self.square_size,
            "image_size": image_size,
            "left_camera": {
                "camera_matrix": K_left.tolist(),
                "distortion": D_left.tolist(),
                "rectification": R1.tolist(),
                "projection": P1.tolist()
            },
            "right_camera": {
                "camera_matrix": K_right.tolist(),
                "distortion": D_right.tolist(),
                "rectification": R2.tolist(),
                "projection": P2.tolist()
            },
            "stereo": {
                "rotation": R.tolist(),
                "translation": T.tolist(),
                "essential": E.tolist(),
                "fundamental": F.tolist(),
                "Q": Q.tolist(),
                "baseline": float(T[0, 0])  # 基线长度
            },
            "reprojection_error": {
                "left": float(ret_left),
                "right": float(ret_right),
                "stereo": float(ret_stereo)
            }
        }
        
        # 保存校正映射
        np.savez_compressed("stereo_maps.npz",
                           map1_left=map1_left, map2_left=map2_left,
                           map1_right=map1_right, map2_right=map2_right)
        
        print(f"\n[参数摘要]")
        print(f"  基线: {abs(T[0, 0]):.2f} mm")
        print(f"  左相机焦距: fx={K_left[0,0]:.1f}, fy={K_left[1,1]:.1f}")
        print(f"  右相机焦距: fx={K_right[0,0]:.1f}, fy={K_right[1,1]:.1f}")
        
        return params
    
    def save_params(self, params, filename="stereo_params.json"):
        """保存标定参数"""
        with open(filename, 'w') as f:
            json.dump(params, f, indent=2)
        print(f"\n[保存] 参数已保存到 {filename}")


if __name__ == "__main__":
    calibrator = StereoCalibrator(pattern_size=(7, 4), square_size=30)
    
    # 选择模式
    print("=" * 50)
    print("双目标定")
    print("=" * 50)
    print("1. 采集标定图像")
    print("2. 从已有图像标定")
    choice = input("选择模式 (1/2): ").strip()
    
    if choice == '1':
        # 采集图像
        calibrator.capture_images(num_images=20)
        print("\n继续标定? (y/n): ", end='')
        if input().strip().lower() != 'y':
            exit()
    
    # 执行标定
    params = calibrator.calibrate_from_images()
    
    # 保存参数
    calibrator.save_params(params)
    
    print("\n[完成] 双目标定完成！")
    print("  生成文件:")
    print("    - stereo_params.json (标定参数)")
    print("    - stereo_maps.npz (校正映射)")

