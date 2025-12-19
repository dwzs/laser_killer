#!/usr/bin/env python3
"""检测两帧间变化的像素点"""

import cv2
import sys

# 参数
# file_name = "video_static.mp4"
file_name = "moving_red_point.mp4"

video_file = sys.argv[1] if len(sys.argv) > 1 else file_name
diff_threshold = 5  # 像素变化阈值（可按 +/- 调整）

print(f"阈值: {diff_threshold} | 按 'q' 退出 | 按 '空格' 暂停 | 按 'r' 重播 | 按 '+/-' 调整阈值\n")

while True:
    cap = cv2.VideoCapture(video_file)
    
    # 读取第一帧
    ret, prev_frame = cap.read()
    if not ret:
        print("无法读取视频")
        sys.exit(1)
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    paused = False
    replay = False
    
    video_ended = False
    
    while True:
        if not paused and not video_ended:
            ret, curr_frame = cap.read()
            if not ret:
                print("视频结束，按 'r' 重播 | 按 'q' 退出")
                video_ended = True
            else:
                curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
                
                # 计算帧差并二值化
                diff = cv2.absdiff(prev_gray, curr_gray)
                _, changed_pixels = cv2.threshold(diff, diff_threshold, 255, cv2.THRESH_BINARY)
                
                # 统计变化像素数
                pixel_count = cv2.countNonZero(changed_pixels)
                if pixel_count > 0:
                    print(f"变化像素: {pixel_count}")
                
                # 显示
                cv2.imshow('Original', curr_frame)
                cv2.imshow('Changed Pixels', changed_pixels)
                
                # 更新上一帧
                prev_gray = curr_gray
        
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
            replay = True
            break
        elif key == ord('+') or key == ord('='):
            diff_threshold = min(255, diff_threshold + 5)
            print(f"阈值: {diff_threshold}")
        elif key == ord('-') or key == ord('_'):
            diff_threshold = max(0, diff_threshold - 5)
            print(f"阈值: {diff_threshold}")
    
    cap.release()

cv2.destroyAllWindows()
