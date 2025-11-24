#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算振镜电压到物理坐标的仿射变换参数
"""

import numpy as np
import json

# 物理坐标 (mm)
cell_length = 30.2
points_physical = np.array([
    [-2 * cell_length, 2 * cell_length],   # p1
    [4 * cell_length, 2 * cell_length],    # p2
    [4 * cell_length, -1 * cell_length],
    [-2 * cell_length, -1 * cell_length]  # p3
       # p4
])

# 振镜电压 (V) - 从 galvo_positions.txt
points_voltage = np.array([
    [-1.1800, 1.1800],   # v1
    [1.5200, 0.7000],    # v2
    [1.9200, -0.7400],   # v3
    [-0.8800, -0.2600]   # v4
])

# 最小二乘法求解仿射变换: px = a*xv + b*yv + c, py = d*xv + e*yv + f
def calculate_affine(voltage_points, physical_points):
    """使用最小二乘法计算仿射变换参数"""
    # 构建系数矩阵 A: [xv, yv, 1]
    A = np.column_stack([voltage_points, np.ones(len(voltage_points))])
    
    # 分别求解 x 和 y 方向
    params_x = np.linalg.lstsq(A, physical_points[:, 0], rcond=None)[0]
    params_y = np.linalg.lstsq(A, physical_points[:, 1], rcond=None)[0]
    
    return params_x, params_y

# 计算参数
params_x, params_y = calculate_affine(points_voltage, points_physical)

print("=" * 50)
print("仿射变换参数（电压 → 物理坐标）")
print("=" * 50)
print(f"px = {params_x[0]:.4f} * xv + {params_x[1]:.4f} * yv + {params_x[2]:.4f}")
print(f"py = {params_y[0]:.4f} * xv + {params_y[1]:.4f} * yv + {params_y[2]:.4f}")
print()

# 验证精度
print("验证结果：")
print(f"{'点':<6} {'电压(V)':<20} {'实际(mm)':<18} {'计算(mm)':<18} {'误差(mm)'}")
print("-" * 80)

for i in range(len(points_voltage)):
    xv, yv = points_voltage[i]
    px_real, py_real = points_physical[i]
    
    # 计算坐标
    px_calc = params_x[0] * xv + params_x[1] * yv + params_x[2]
    py_calc = params_y[0] * xv + params_y[1] * yv + params_y[2]
    
    # 计算误差
    error = np.sqrt((px_calc - px_real)**2 + (py_calc - py_real)**2)
    
    print(f"P{i+1:<5} ({xv:>6.2f}, {yv:>6.2f})   "
          f"({px_real:>6.1f}, {py_real:>6.1f})   "
          f"({px_calc:>6.1f}, {py_calc:>6.1f})   "
          f"{error:>6.2f}")

print()
print("=" * 50)

# 保存参数到JSON文件
affine_params = {
    "description": "仿射变换参数：电压(V) -> 物理坐标(mm)",
    "formula": {
        "px": "a * xv + b * yv + c",
        "py": "d * xv + e * yv + f"
    },
    "parameters": {
        "a": float(params_x[0]),
        "b": float(params_x[1]),
        "c": float(params_x[2]),
        "d": float(params_y[0]),
        "e": float(params_y[1]),
        "f": float(params_y[2])
    },
    "depth_mm": 1000,
    "cell_length_mm": cell_length
}

filename = "affine_params.json"
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(affine_params, f, indent=2, ensure_ascii=False)

print(f"[保存] 参数已保存到 {filename}")
