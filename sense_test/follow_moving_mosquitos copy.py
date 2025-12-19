#!/usr/bin/env python3
"""
运动蚊子追踪系统
1. 背景剪切：检测帧间变化
2. 颜色筛选：筛选黑色区域
3. 形状筛选：面积和长宽比
4. 跟踪：最近邻匹配
"""

import cv2
import numpy as np
import sys
import os
import math

# ========== 配置参数 ==========
# 背景剪切参数
# 两帧差分参数（适用于相机基本静止）
DIFF_THRESHOLD = 50         # 帧差阈值（越小越敏感）
MIN_CHANGE_AREA = 4         # 最小变化区域面积，小于该面积即为噪声

# 颜色筛选参数（黑色）
BLACK_MAX = 200              # RGB最大值（越小越黑）
RGB_GAP_MAX = 40             # RGB三通道最大差值(max-min)，越小越偏灰/白（过滤彩色）

# 形状筛选参数
MIN_AREA = 5               # 最小面积（像素）
MAX_AREA = 1000             # 最大面积（像素）
MIN_CIRCULARITY = 0.2       # 最小圆形度（轮廓面积/外接圆面积，圆形≈1.0）

# 跟踪参数
MATCH_BOX_SIZE = 50        # 匹配搜索框边长（像素）：以上一帧点为中心的方形窗口内找当前点
MIN_MATCH_DISTANCE = 0     # 最小匹配距离（像素）：小于该值则不认为是同一只（默认0=不限制）

# ========== 1. 背景剪切 ==========
def detect_motion(prev_gray, curr_gray, diff_threshold, min_area=0):
    """两帧差分：abs(t - t-1)"""
    diff = cv2.absdiff(curr_gray, prev_gray)
    _, motion_mask = cv2.threshold(diff, diff_threshold, 255, cv2.THRESH_BINARY)
    if min_area > 0:
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        out = np.zeros_like(motion_mask)
        for cnt in contours:
            tmp = np.zeros_like(motion_mask)
            cv2.drawContours(tmp, [cnt], -1, 255, -1)  # 填充：面积=边界+内部像素
            if cv2.countNonZero(tmp) >= min_area:
                cv2.drawContours(out, [cnt], -1, 255, -1)
        motion_mask = out
    return motion_mask

# ========== 2. 颜色筛选 ==========
def filter_black_color(frame, mask, black_max):
    """在运动区域中筛选黑/灰/白（通道接近）"""
    # 只在运动区域内检测颜色
    # mask 内最亮与最暗的差值小于 RGB_GAP_MAX 的点为黑色/灰色/白色
    b, g, r = cv2.split(frame)

    max_rgb = np.maximum(np.maximum(r, g), b)
    min_rgb = np.minimum(np.minimum(r, g), b)
    gap = max_rgb - min_rgb

    # 亮度上限 + 通道差值限制（灰/白更符合：gap 小）
    black_mask = (
        (r <= black_max) & (g <= black_max) & (b <= black_max) &
        (gap <= RGB_GAP_MAX)
    ).astype(np.uint8) * 255
    
    # 与运动区域求交集
    color_filtered = cv2.bitwise_and(black_mask, mask)
    return color_filtered

# ========== 3. 形状筛选 ==========
def filter_by_shape(mask, min_area, max_area, min_circ):
    """根据面积和圆形度筛选（圆形度越高越像蚊子）"""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    valid_contours = []
    shape_mask = np.zeros_like(mask)
    mosquito_centers = []
    
    for cnt in contours:
        # 面积：包含边界+内部像素（用填充后的像素计数）
        tmp = np.zeros_like(mask)
        cv2.drawContours(tmp, [cnt], -1, 255, -1)
        area = cv2.countNonZero(tmp)
        if area < min_area or area > max_area:
            continue
        
        # 检查圆形度（使用最小外接圆）
        (cx, cy), radius = cv2.minEnclosingCircle(cnt)
        if radius == 0:
            continue
        
        # 计算圆形度 = 轮廓面积 / 外接圆面积
        # 外接圆面积：用像素计数（包含边界+内部像素），与 area 的定义一致
        circle_mask = np.zeros_like(mask)
        cv2.circle(circle_mask, (int(cx), int(cy)), int(radius), 255, -1)
        circle_area = cv2.countNonZero(circle_mask)
        circularity = area / circle_area if circle_area > 0 else 0
        
        # 只保留比较圆的形状（蚊子通常是圆形或椭圆形）
        if circularity < min_circ:
            continue
        
        # 保存外接圆信息（用于后续可视化）
        w = h = int(radius * 2)  # 近似宽高（用于统计）
        
        # 通过筛选
        valid_contours.append(cnt)
        cv2.drawContours(shape_mask, [cnt], -1, 255, -1)
        
        # 计算质心
        M = cv2.moments(cnt)
        if M["m00"] > 0:
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]
            mosquito_centers.append([cx, cy, area, w, h])
    
    return shape_mask, mosquito_centers, valid_contours

# ========== 4. 跟踪 ==========
def track_mosquitos(prev_centers, curr_centers, box_size):
    """
    以上一帧每个点为中心，在当前帧的 box_size×box_size 方形窗口内找点：
    - 有点：认为同一只蚊子
    - 多个点：取最近的
    """
    if not prev_centers or not curr_centers:
        return []

    half = int(box_size // 2)
    matched_curr = set()
    matches = []

    for prev_idx, prev in enumerate(prev_centers):
        px, py = float(prev[0]), float(prev[1])
        best_i = -1
        best_d2 = None

        for curr_idx, curr in enumerate(curr_centers):
            if curr_idx in matched_curr:
                continue
            cx, cy = float(curr[0]), float(curr[1])
            dx = cx - px
            dy = cy - py

            # 只在以上一帧点为中心的矩形框内搜索
            if abs(dx) > half or abs(dy) > half:
                continue

            d2 = dx * dx + dy * dy
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best_i = curr_idx

        if best_i >= 0:
            dist = math.sqrt(best_d2) if best_d2 is not None else 0.0
            if dist < MIN_MATCH_DISTANCE:
                continue
            matched_curr.add(best_i)
            matches.append((best_i, prev_idx, dist))

    return matches

# ========== 主程序 ==========
def main():
    # 获取视频文件
    # default_file = "moving_mosquitos.mp4"
    # default_file = "moving_mosquitos1.mp4"
    # default_file = "moving_mosquitos2.mp4"
    default_file = "moving_mosquitos3.mp4"
    # default_file = "moving_mosquitos4.mp4"
    # default_file = "moving_mosquito_bedroom.mp4"
    video_file = sys.argv[1] if len(sys.argv) > 1 else default_file
    
    if not os.path.exists(video_file):
        print(f"错误: 视频文件 '{video_file}' 不存在")
        sys.exit(1)
    
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"错误: 无法打开视频 '{video_file}'")
        sys.exit(1)
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"视频: {video_file} | {width}x{height} @ {fps:.1f}fps")
    print(f"参数: 两帧差分阈值={DIFF_THRESHOLD}, 黑色阈值={BLACK_MAX}")
    print(f"      面积={MIN_AREA}-{MAX_AREA}, 最小圆形度={MIN_CIRCULARITY}")
    print(f"按键: 'q'=退出 | 'r'=重播 | 空格=暂停\n")
    
    # 读取第一帧
    ret, frame = cap.read()
    if not ret:
        print("错误: 无法读取视频")
        sys.exit(1)

    # 初始化两帧差分缓存
    prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    prev_centers = []
    mosquito_id = 0
    
    frame_idx = 0
    paused = False
    delay = int(1000 / fps) if fps > 0 else 30
    
    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("视频结束")
                key = cv2.waitKey(0) & 0xFF
                if key == ord('r'):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame0 = cap.read()
                    if not ret:
                        break
                    prev_gray = cv2.cvtColor(frame0, cv2.COLOR_BGR2GRAY)
                    prev_centers = []
                    frame_idx = 0
                    print("重播...\n")
                    continue
                break
            
            frame_idx += 1
            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # === 1. 背景剪切 ===
            motion_mask = detect_motion(prev_gray, curr_gray, DIFF_THRESHOLD, MIN_CHANGE_AREA)

            # === 2. 颜色筛选 ===
            color_mask = filter_black_color(frame, motion_mask, BLACK_MAX)

            # 颜色筛选后所有轮廓（用于 pd）
            all_contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

            # === 3. 形状筛选 ===
            shape_mask, curr_centers, contours = filter_by_shape(
                color_mask, MIN_AREA, MAX_AREA, MIN_CIRCULARITY
            )

            # === 4. 跟踪 ===
            matches = track_mosquitos(prev_centers, curr_centers, MATCH_BOX_SIZE)

            tracked_frame = frame.copy()
            
            # 绘制跟踪结果
            for i, center_info in enumerate(curr_centers):
                cx, cy, area, w, h = center_info
                x, y = int(cx), int(cy)
                
                # 检查是否被跟踪
                is_tracked = any(m[0] == i for m in matches)
                
                if is_tracked:
                    # 被跟踪的蚊子：红色圆圈
                    cv2.circle(tracked_frame, (x, y), 20, (0, 0, 255), 2)
                    # 显示信息
                    info = f"ID:{i} A:{int(area)}"
                    cv2.putText(tracked_frame, info, (x + 25, y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                else:
                    # 新出现的蚊子：绿色圆圈
                    cv2.circle(tracked_frame, (x, y), 15, (0, 255, 0), 2)
                
                # 绘制中心点
                cv2.circle(tracked_frame, (x, y), 3, (255, 0, 0), -1)
            
            # 打印跟踪信息
            if curr_centers:
                tracked_count = len(matches)
                new_count = len(curr_centers) - tracked_count
                print(f"[帧{frame_idx}] 检测到 {len(curr_centers)} 只蚊子 | 跟踪={tracked_count} 新={new_count}")
            
            # 更新两帧差分缓存 + 跟踪数据
            prev_gray = curr_gray
            prev_centers = curr_centers
            
            # === 显示结果（pa~pf）===
            white_bg = np.ones_like(frame) * 255
            
            # 1) pa 原始图
            im_original = frame.copy()
            
            # 2) pb 运动图（白底+彩色运动区域）
            im_motion = white_bg.copy()
            im_motion[motion_mask > 0] = frame[motion_mask > 0]
            
            # 3) pc pb过滤颜色后的彩图（白底+彩色）
            im_color = white_bg.copy()
            im_color[color_mask > 0] = frame[color_mask > 0]

            # 4) pd 在 pc 上画所有轮廓
            im_contour = im_color.copy()
            cv2.drawContours(im_contour, all_contours, -1, (255, 0, 0), 1)  # 黄：所有轮廓

            # 5) pe 在 pc 上画筛选后的轮廓
            im_mosquito = im_color.copy()
            cv2.drawContours(im_mosquito, contours, -1, (0, 255, 0), 1)  # 绿：筛选后轮廓

            # 6) pf 筛选出蚊子（在 pa 上圈出中心）
            im_tracking = im_original.copy()
            for center_info in curr_centers:
                cx, cy, area, w, h = center_info
                x, y = int(cx), int(cy)
                cv2.circle(im_tracking, (x, y), 15, (0, 0, 255), 2)
                cv2.circle(im_tracking, (x, y), 3, (255, 0, 0), -1)
            
            # 拼接显示（2x3布局）
            row1 = np.hstack([im_original, im_motion, im_color])
            row2 = np.hstack([im_contour, im_mosquito, im_tracking])
            combined = np.vstack([row1, row2])
            
            # 添加标签
            cv2.putText(combined, '1.original', (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(combined, '2.motion_filtered', (width + 10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(combined, '3.color_filtered', (width * 2 + 10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(combined, '4.all_contours', (10, height + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(combined, '5.shape_filtered', (width + 10, height + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(combined, '6.tracking', (width * 2 + 10, height + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow('Mosquito Tracking', combined)

            # （移除二次筛选显示）
        
        # 处理按键
        key = cv2.waitKey(delay if not paused else 100) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord(' '):
            paused = not paused
            print(f"[帧{frame_idx}] {'暂停' if paused else '继续'}")
        elif key == ord('r'):
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame0 = cap.read()
            if not ret:
                break
            prev_gray = cv2.cvtColor(frame0, cv2.COLOR_BGR2GRAY)
            prev_centers = []
            frame_idx = 0
            paused = False
            print("重播...\n")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
