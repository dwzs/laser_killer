#!/usr/bin/env python3
"""彩色点追踪 - 支持自定义颜色检测"""

import cv2
import numpy as np
import sys
import os

# ========== 配置参数 ==========
# 颜色检测模式
COLOR_MODE = 'custom'  # 'red', 'green', 'blue', 'custom'

# 颜色配置
COLOR_PRESETS = {
    'red':    {'ch': 2, 'min': 170, 'gap': 90, 'color': (0, 0, 255)},
    'green':  {'ch': 1, 'min': 150, 'gap': 80, 'color': (0, 255, 0)},
    'blue':   {'ch': 0, 'min': 150, 'gap': 80, 'color': (255, 0, 0)},
    'custom': {'r': (0, 50), 'g': (0, 50), 'b': (0, 50), 'color': (0, 0, 0)}
}

# 追踪参数
MOTION_THRESHOLD = 3.0      # 运动判断阈值（像素）
MAX_MATCH_DISTANCE = 20     # 帧间最大匹配距离（像素）

# ========== 颜色检测函数 ==========
def detect_color_points(frame, mode, config):
    """检测指定颜色的点，返回质心坐标列表"""
    b, g, r = cv2.split(frame)
    
    if mode == 'custom':
        # 自定义模式：RGB范围
        r_min, r_max = config['r']
        g_min, g_max = config['g']
        b_min, b_max = config['b']
        mask = ((r >= r_min) & (r <= r_max) &
                (g >= g_min) & (g <= g_max) &
                (b >= b_min) & (b <= b_max)).astype(np.uint8) * 255
    else:
        # 预设模式：目标通道比其他通道高
        channels = [b, g, r]
        target = channels[config['ch']].astype(np.int16)
        others = [channels[i].astype(np.int16) for i in range(3) if i != config['ch']]
        
        mask = (channels[config['ch']] > config['min'])
        for other in others:
            mask &= (target - other > config['gap'])
        mask = mask.astype(np.uint8) * 255
    
    # 找轮廓并计算质心
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    points = []
    for cnt in contours:
        M = cv2.moments(cnt)
        if M["m00"] > 0:
            cx, cy = M["m10"] / M["m00"], M["m01"] / M["m00"]
            points.append([cx, cy])
    
    return np.array(points, dtype=np.float32) if points else None, mask

# ========== 点匹配函数 ==========
def match_points(prev_pts, curr_pts, max_dist):
    """最近邻匹配，返回匹配结果：[(curr_idx, prev_idx, distance), ...]"""
    if prev_pts is None or curr_pts is None:
        return []
    
    matches = []
    matched_prev = set()
    
    for i, curr in enumerate(curr_pts):
        min_dist = float('inf')
        best_match = -1
        
        for j, prev in enumerate(prev_pts):
            if j in matched_prev:
                continue
            dist = np.linalg.norm(curr - prev)
            if dist < min_dist:
                min_dist = dist
                best_match = j
        
        if best_match >= 0 and min_dist <= max_dist:
            matches.append((i, best_match, min_dist))
            matched_prev.add(best_match)
    
    return matches

# ========== 主程序 ==========
def main():
    # 获取视频文件
    default_file = "moving_mosquitos.mp4"
    video_file = sys.argv[1] if len(sys.argv) > 1 else default_file
    
    if not os.path.exists(video_file):
        print(f"错误: 视频文件 '{video_file}' 不存在")
        sys.exit(1)
    
    # 打开视频
    cap = cv2.VideoCapture(video_file)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    delay = int(1000 / fps) if fps > 0 else 30
    
    print(f"视频: {video_file} | {width}x{height} @ {fps:.1f}fps")
    print(f"颜色: {COLOR_MODE.upper()} | 运动阈值: {MOTION_THRESHOLD}px")
    print(f"按键: 'q'=退出 | 'r'=重播 | 空格=暂停\n")
    
    # 分析第一帧
    ret, frame = cap.read()
    if not ret:
        print("错误: 无法读取视频")
        sys.exit(1)
    
    b, g, r = cv2.split(frame)
    print(f"第一帧RGB统计: R={np.mean(r):.1f} G={np.mean(g):.1f} B={np.mean(b):.1f}\n")
    
    # 初始化
    config = COLOR_PRESETS[COLOR_MODE]
    prev_points = None
    trail_mask = np.zeros_like(frame)
    frame_idx = 0
    paused = False
    
    # 重置函数
    def reset_video():
        nonlocal prev_points, trail_mask, frame_idx
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        prev_points = None
        trail_mask = np.zeros_like(frame)
        frame_idx = 0
        print("重播...\n")
    
    # 主循环
    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("视频结束")
                key = cv2.waitKey(0) & 0xFF
                if key == ord('r'):
                    reset_video()
                    continue
                break
            
            frame_idx += 1
            
            # 检测颜色点
            curr_points, color_mask = detect_color_points(frame, COLOR_MODE, config)
            
            # 创建显示图像
            white_bg = np.ones_like(frame) * 255
            
            if curr_points is None:
                print(f"[帧{frame_idx}] 未检测到点")
                prev_points = None
            else:
                # 第一帧或上一帧无点：直接显示
                if prev_points is None:
                    for pt in curr_points:
                        x, y = int(pt[0]), int(pt[1])
                        cv2.circle(white_bg, (x, y), 5, config['color'], -1)
                    print(f"[帧{frame_idx}] 检测到 {len(curr_points)} 个点")
                else:
                    # 匹配点
                    matches = match_points(prev_points, curr_points, MAX_MATCH_DISTANCE)
                    matched_curr = set(m[0] for m in matches)
                    
                    moving = 0
                    static = 0
                    
                    # 绘制匹配的点
                    for curr_idx, prev_idx, dist in matches:
                        curr_x, curr_y = int(curr_points[curr_idx][0]), int(curr_points[curr_idx][1])
                        prev_x, prev_y = int(prev_points[prev_idx][0]), int(prev_points[prev_idx][1])
                        
                        if dist > MOTION_THRESHOLD:
                            # 运动点：空心圆 + 轨迹
                            cv2.circle(white_bg, (curr_x, curr_y), 10, config['color'], 2)
                            cv2.line(trail_mask, (prev_x, prev_y), (curr_x, curr_y), 
                                   config['color'], 2)
                            cv2.circle(frame, (curr_x, curr_y), 5, config['color'], -1)
                            moving += 1
                            print(f"[帧{frame_idx}] 运动点 #{curr_idx}: ({curr_x},{curr_y}) 距离={dist:.1f}px")
                        else:
                            # 静止点：实心圆
                            cv2.circle(white_bg, (curr_x, curr_y), 5, config['color'], -1)
                            static += 1
                    
                    # 绘制未匹配的点（新点）
                    for i, pt in enumerate(curr_points):
                        if i not in matched_curr:
                            x, y = int(pt[0]), int(pt[1])
                            cv2.circle(white_bg, (x, y), 5, (0, 255, 0), -1)
                            print(f"[帧{frame_idx}] 新点 #{i}: ({x},{y})")
                    
                    if moving + static > 0:
                        print(f"[帧{frame_idx}] 运动={moving} 静止={static} 新点={len(curr_points)-len(matched_curr)}")
                
                prev_points = curr_points
            
            # 显示
            img_flow = cv2.add(frame, trail_mask)
            cv2.imshow('Detected Points', white_bg)
            cv2.imshow('Motion Trail', img_flow)
            cv2.imshow('Color Mask', color_mask)
        
        # 处理按键
        key = cv2.waitKey(delay if not paused else 100) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('r'):
            reset_video()
        elif key == ord(' '):
            paused = not paused
            print(f"[帧{frame_idx}] {'暂停' if paused else '继续'}")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
