#!/usr/bin/env python3
"""录制视频（极简、安全）

功能：
1) 参数传入保存文件名
2) 仅按 's' 才保存（覆盖同名文件）
3) 其他任何退出方式都不保存，也不会覆盖原同名文件
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2


def _make_target_and_temp(path_str: str) -> tuple[Path, Path]:
    p = Path(path_str)
    if p.suffix == "":
        p = p.with_suffix(".mp4")
    # 临时文件必须保留原后缀，否则 VideoWriter 可能无法创建（靠后缀选择容器）
    tmp = p.with_name(f"{p.stem}.recording{p.suffix}")
    return p, tmp


def main() -> int:
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

    target_path, temp_path = _make_target_and_temp(target)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 仅用最常见 mp4v；如果你的系统不支持 mp4v，可以把目标后缀改成 .avi 再录
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(temp_path), fourcc, fps, (width, height))
    if not out.isOpened():
        print("✗ 无法创建 VideoWriter")
        print(f"  临时文件: {temp_path.resolve()}")
        print("  提示: 临时文件必须是 .mp4/.avi 这类已知后缀；可尝试把目标文件名改成 .avi")
        cap.release()
        return 1

    print(f"目标文件: {target_path.resolve()}")
    print(f"临时文件: {temp_path.resolve()}")
    print(f"分辨率: {width}x{height} @ {fps}fps")
    print("按 's' 保存并退出；按 'q'/任意键/关闭窗口/Ctrl+C 都取消（不保存）\n")

    start_time = time.time()
    frame_count = 0
    should_save = False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            out.write(frame)
            frame_count += 1

            secs = int(time.time() - start_time)
            cv2.putText(
                frame,
                f"REC {secs}s | {frame_count} frames | s=Save q=Cancel",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )
            cv2.imshow("Recording", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("s"):
                should_save = True
                break
            if key != 255:  # 任意其他按键（包括 q）
                break
    except KeyboardInterrupt:
        pass

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    time.sleep(0.2)  # 给写入落盘一点时间

    if should_save and frame_count > 0 and temp_path.exists():
        # 覆盖同名文件：仅在保存时才覆盖
        if target_path.exists():
            target_path.unlink()
        temp_path.rename(target_path)
        print(f"✓ 已保存: {target_path.resolve()}")
        return 0

    # 取消：删除临时文件，原文件不动
    if temp_path.exists():
        temp_path.unlink()
    print("已取消，未保存（原同名文件未被覆盖）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
