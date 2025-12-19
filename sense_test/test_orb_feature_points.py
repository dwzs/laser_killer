#!/usr/bin/env python3
"""使用ORB检测特征点"""

import cv2
import numpy as np
import sys
import time

video_file = "moving_red_point.mp4"
# video_file = "video_static.mp4"

# 参数
video_file = sys.argv[1] if len(sys.argv) > 1 else video_file
max_features = 100     # ORB最大特征点数量

print(f"ORB特征点参数: 最大数量={max_features}")
print("按 'q' 退出 | 按 '空格' 暂停 | 按 'r' 重播 | 按 '+/-' 调整数量\n")

# 创建ORB检测器
orb = cv2.ORB_create(nfeatures=max_features)

while True:
    cap = cv2.VideoCapture(video_file)
    
    ret, first_frame = cap.read()
    if not ret:
        print("无法读取视频")
        sys.exit(1)
    
    paused = False
    video_ended = False
    frame_idx = 0
    
    # 初始化跟踪数据
    prev_keypoints = None
    prev_descriptors = None
    point_ids = {}         # keypoint索引 -> ID的映射
    next_id = 0            # 下一个可用的ID
    
    # 创建BFMatcher用于特征匹配
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    
    while True:
        if not paused and not video_ended:
            ret, frame = cap.read()
            if not ret:
                print("视频结束，按 'r' 重播 | 按 'q' 退出")
                video_ended = True
            else:
                frame_idx += 1
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                result = frame.copy()
                
                # ORB检测特征点
                start_time = time.time()
                keypoints, descriptors = orb.detectAndCompute(gray, None)
                detect_time = (time.time() - start_time) * 1000  # 转换为毫秒
                
                if keypoints:
                    print(f"[帧 {frame_idx}] 检测到 {len(keypoints)} 个ORB特征点 | 耗时: {detect_time:.2f}ms")
                    
                    # 第一帧：初始化所有特征点ID
                    if prev_keypoints is None:
                        for i in range(len(keypoints)):
                            point_ids[i] = next_id
                            next_id += 1
                    else:
                        # 后续帧：通过特征匹配来关联特征点
                        if prev_descriptors is not None and descriptors is not None:
                            start_match = time.time()
                            matches = bf.match(prev_descriptors, descriptors)
                            match_time = (time.time() - start_match) * 1000
                            
                            # 创建新的ID映射
                            new_point_ids = {}
                            matched_count = 0
                            
                            for match in matches:
                                prev_idx = match.queryIdx
                                curr_idx = match.trainIdx
                                if prev_idx in point_ids:
                                    new_point_ids[curr_idx] = point_ids[prev_idx]
                                    matched_count += 1
                            
                            # 为未匹配的特征点分配新ID
                            for i in range(len(keypoints)):
                                if i not in new_point_ids:
                                    new_point_ids[i] = next_id
                                    next_id += 1
                            
                            point_ids = new_point_ids
                            print(f"[帧 {frame_idx}] 匹配 {matched_count}/{len(matches)} 个特征点 | 耗时: {match_time:.2f}ms")
                    
                    # 绘制特征点和ID
                    for i, kp in enumerate(keypoints):
                        x, y = int(kp.pt[0]), int(kp.pt[1])
                        pt_id = point_ids.get(i, -1)
                        
                        # 绘制特征点
                        cv2.circle(result, (x, y), 5, (0, 255, 0), -1)
                        # 绘制ID
                        cv2.putText(result, str(pt_id), (x + 8, y - 8),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
                    
                    # 显示信息
                    info = f"Frame:{frame_idx} | Features:{len(keypoints)} | Time:{detect_time:.1f}ms"
                    cv2.putText(result, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.7, (0, 255, 255), 2)
                    
                    # 更新上一帧数据
                    prev_keypoints = keypoints
                    prev_descriptors = descriptors
                else:
                    print(f"[帧 {frame_idx}] 未检测到特征点")
                    info = f"Frame:{frame_idx} | Features:0"
                    cv2.putText(result, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.7, (0, 0, 255), 2)
                
                # 显示
                cv2.imshow('ORB Feature Points', result)
        
        # 处理按键
        key = cv2.waitKey(30 if not paused else 100) & 0xFF
        
        if key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(0)
        elif key == ord(' '):
            paused = not paused
        elif key == ord('r'):
            print("重播")
            break
        elif key == ord('+') or key == ord('='):
            max_features = min(2000, max_features + 100)
            orb = cv2.ORB_create(nfeatures=max_features)
            print(f"最大特征点数: {max_features}")
        elif key == ord('-') or key == ord('_'):
            max_features = max(100, max_features - 100)
            orb = cv2.ORB_create(nfeatures=max_features)
            print(f"最大特征点数: {max_features}")
    
    cap.release()

cv2.destroyAllWindows()

