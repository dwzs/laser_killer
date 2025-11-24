#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
振镜控制器 - 提供物理坐标和相对坐标的控制接口
"""

import json
import numpy as np

# 支持作为模块导入和直接运行
try:
    from .galvo_driver import GalvoDriver
except ImportError:
    from galvo_driver import GalvoDriver


class GalvoController:
    """振镜控制器（带坐标转换）"""
    
    def __init__(self, affine_params_file="./calib/affine_params.json"):
        """初始化控制器"""
        # 底层驱动
        self.driver = GalvoDriver()
        
        # 电压范围和中心
        self.v_min = 0.0
        self.v_max = 4.8
        self.v_center = (self.v_min + self.v_max) / 2
        
        # 方向配置（用于坐标系调整）
        self.direction_x = -1  # X轴方向：1=正向，-1=反向
        self.direction_y = 1   # Y轴方向：1=正向，-1=反向
        
        # 当前位置（相对电压）
        self.current_xv = 0.0
        self.current_yv = 0.0
        
        # 加载仿射变换参数
        try:
            with open(affine_params_file, 'r') as f:
                params = json.load(f)
            
            p = params['parameters']
            self.affine_matrix = np.array([
                [p['a'], p['b']],
                [p['d'], p['e']]
            ])
            self.affine_offset = np.array([p['c'], p['f']])
            self.inverse_matrix = np.linalg.inv(self.affine_matrix)
            self.affine_loaded = True
            print("[控制器] 仿射参数已加载")
        except:
            self.affine_loaded = False
            print("[控制器] 仿射参数未加载，仅支持电压控制")
        
        # 初始化到中心
        self.center()
        print("[控制器] 初始化完成")
    
    def set_voltage(self, xv, yv):
        """
        设置相对电压（相对于中心）
        
        参数:
            xv: X轴相对电压 (-2.4 ~ +2.4V)
            yv: Y轴相对电压 (-2.4 ~ +2.4V)
        """
        # 限幅
        xv = max(self.v_min - self.v_center, min(self.v_max - self.v_center, xv))
        yv = max(self.v_min - self.v_center, min(self.v_max - self.v_center, yv))
        
        # 应用方向转换，转为绝对电压
        voltage_a = self.v_center + xv * self.direction_x
        voltage_b = self.v_center + yv * self.direction_y
        
        # 写入驱动
        self.driver.set_voltage(voltage_a, voltage_b)
        
        # 更新当前位置
        self.current_xv = xv
        self.current_yv = yv
    
    def move_to_physical(self, px, py):
        """
        移动到物理坐标
        
        参数:
            px: X轴物理坐标 (mm)
            py: Y轴物理坐标 (mm)
        """
        if not self.affine_loaded:
            raise RuntimeError("仿射参数未加载，无法使用物理坐标")
        
        # 物理坐标 -> 电压
        p = np.array([px, py]) - self.affine_offset
        v = self.inverse_matrix @ p
        
        # 设置电压
        self.set_voltage(v[0], v[1])
    
    def get_physical_position(self):
        """获取当前物理坐标"""
        if not self.affine_loaded:
            raise RuntimeError("仿射参数未加载")
        
        v = np.array([self.current_xv, self.current_yv])
        p = self.affine_matrix @ v + self.affine_offset
        return p[0], p[1]
    
    def center(self):
        """回到中心位置"""
        self.set_voltage(0, 0)
    
    def move_rectangle(self, margin=0.2, steps=100, delay=0.01):
        """
        沿最大范围边界矩形运动
        
        参数:
            margin: 边界余量 (V)，避免到达极限
            steps: 每条边的步数
            delay: 每步延时 (秒)
        """
        import time
        
        # 计算边界范围（相对电压）
        v_min_rel = self.v_min - self.v_center + margin
        v_max_rel = self.v_max - self.v_center - margin
        
        # 四个角点（左下、右下、右上、左上）
        corners = [
            (v_min_rel, v_min_rel),  # 左下
            (v_max_rel, v_min_rel),  # 右下
            (v_max_rel, v_max_rel),  # 右上
            (v_min_rel, v_max_rel),  # 左上
        ]
        
        print(f"[矩形运动] 范围: {v_min_rel:.2f}V ~ {v_max_rel:.2f}V")
        
        # 绘制四条边
        for i in range(4):
            x1, y1 = corners[i]
            x2, y2 = corners[(i + 1) % 4]
            
            # 插值运动
            for j in range(steps + 1):
                t = j / steps
                x = x1 + (x2 - x1) * t
                y = y1 + (y2 - y1) * t
                self.set_voltage(x, y)
                time.sleep(delay)
        
        print("[矩形运动] 完成")
    
    def close(self):
        """关闭控制器"""
        self.center()
        self.driver.close()
        print("[控制器] 关闭")


def generate_chessboard_corners(rows, cols, cell_length, origin=(0, 0)):
    """
    生成棋盘格角点坐标
    
    参数:
        rows: 棋盘行数
        cols: 棋盘列数
        cell_length: 方格边长(mm)
        origin: 左上角原点(mm)
    
    返回:
        角点列表 [(px, py), ...]
    """
    corners = []
    ox, oy = origin
    
    for i in range(rows + 1):
        for j in range(cols + 1):
            px = ox + j * cell_length
            py = oy - i * cell_length
            corners.append((px, py))
    
    return corners


if __name__ == "__main__":
    import time
    
    controller = GalvoController()
    
    print("\n[测试] 选择功能:")
    print("  1. 边界矩形运动")
    print("  2. 棋盘格角点遍历")
    choice = input("选择 (1/2): ").strip()
    
    if choice == '1':
        # 边界矩形运动
        print("\n[测试] 边界矩形运动")
        controller.move_rectangle(margin=0.2, steps=100, delay=0.01)
        controller.center()
        
    elif choice == '2':
        # 棋盘格参数
        rows = 4
        cols = 7
        cell_length = 30.2
        origin = (-2 * cell_length, 2 * cell_length)
        
        # 生成角点
        corners = generate_chessboard_corners(rows, cols, cell_length, origin)
        
        print(f"\n[棋盘格] {rows}行 x {cols}列 = {len(corners)}个角点")
        print(f"  方格边长: {cell_length}mm")
        print(f"  起点: ({origin[0]:.1f}, {origin[1]:.1f})mm\n")
        
        # 遍历角点
        for idx, (px, py) in enumerate(corners):
            input(f"[{idx+1}/{len(corners)}] 按Enter移动到 ({px:.1f}, {py:.1f})mm")
            controller.move_to_physical(px, py)
            current = controller.get_physical_position()
            print(f"  实际位置: ({current[0]:.1f}, {current[1]:.1f})mm")
            print(f"  电压: ({controller.current_xv:.2f}, {controller.current_yv:.2f})V")
    
    # 回中心
    print("\n回到中心")
    controller.close()
