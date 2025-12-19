#!/usr/bin/env python3
import argparse
import os
import sys

import cv2


def open_writer(out_path: str, w: int, h: int, fps: float) -> cv2.VideoWriter:
    ext = os.path.splitext(out_path)[1].lower()
    fourcc_candidates = ["mp4v", "avc1"] if ext in [".mp4", ".m4v"] else ["XVID", "MJPG", "mp4v"]
    for code in fourcc_candidates:
        vw = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*code), fps, (w, h))
        if vw.isOpened():
            return vw
    return cv2.VideoWriter()  # unopened


def main() -> int:
    ap = argparse.ArgumentParser(description="Resize a video and save (simple).")
    ap.add_argument("input", nargs="?", default="moving_mosquito_bedroom_original.mp4", help="input video path (default: input.mp4)")
    ap.add_argument("output", nargs="?", default="moving_mosquito_bedroom.mp4", help="output video path (default: auto)")
    ap.add_argument("--w", type=int, default=640, help="target width (default: 640)")
    ap.add_argument("--h", type=int, default=480, help="target height (default: 480)")
    ap.add_argument("--fps", type=float, default=0.0, help="override fps (default: use input fps)")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"✗ 输入视频不存在: {args.input}")
        return 1

    if not args.output:
        base, ext = os.path.splitext(args.input)
        ext = ext if ext else ".mp4"
        args.output = f"{base}_{args.w}x{args.h}{ext}"

    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        print(f"✗ 无法打开输入视频: {args.input}")
        return 1

    fps = args.fps or (cap.get(cv2.CAP_PROP_FPS) or 30.0)
    out = open_writer(args.output, args.w, args.h, fps)
    if not out.isOpened():
        print(f"✗ 无法创建输出视频: {args.output}")
        return 2

    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        out.write(cv2.resize(frame, (args.w, args.h), interpolation=cv2.INTER_AREA))
        n += 1

    out.release()
    cap.release()
    print(f"✓ 完成: {args.input} -> {args.output} | size={args.w}x{args.h} fps={fps:.2f} frames={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

