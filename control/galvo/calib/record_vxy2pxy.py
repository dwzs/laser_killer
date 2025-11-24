#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标定脚本：记录振镜电压坐标
"""

import sys
import os
# 添加父目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# try:
#     from galvo_driver import GalvoDriver as GalvoController
# except ImportError:
#     from galvo import GalvoController

from galvo import GalvoController

class CalibrationRecorder:
    """标定数据记录器"""
    
    def __init__(self):
        """初始化控制器"""
        self.galvo = GalvoController()
        
        # 移动步长
        self.step = 0.1  # 电压步长
        
        # 记录数据
        self.records = []
        
        print("[启动] 标定记录系统")
        print("  方向键: 移动振镜")
        print("  +/-: 调整步长")
        print("  Enter: 记录当前点")
        print("  's': 保存并退出")
        print("  'q': 退出不保存")
    
    def run(self):
        """运行标定循环"""
        import sys
        import termios
        import tty
        
        # 保存终端设置
        old_settings = termios.tcgetattr(sys.stdin)
        
        try:
            tty.setcbreak(sys.stdin.fileno())
            print("\n[运行中] 使用方向键控制，按Enter记录")
            
            while True:
                # 显示当前状态
                print(f"\r[当前] Galvo:({self.galvo.current_xv:.2f}V, {self.galvo.current_yv:.2f}V) | "
                      f"步长:{self.step:.3f}V | 记录:{len(self.records)}点", end='', flush=True)
                
                # 读取键盘
                import select
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    
                    if key == 'q':  # 退出
                        print("\n[退出]")
                        break
                    elif key == 's':  # 保存并退出
                        print("\n[保存中...]")
                        self.save_records()
                        break
                    elif key == '\r' or key == '\n':  # Enter - 记录
                        self.record_point()
                    elif key == '\x1b':  # ESC序列（方向键）
                        sys.stdin.read(1)  # 跳过 '['
                        arrow = sys.stdin.read(1)
                        if arrow == 'A':  # 上
                            self.galvo.move_y(self.step)
                        elif arrow == 'B':  # 下
                            self.galvo.move_y(-self.step)
                        elif arrow == 'D':  # 左
                            self.galvo.move_x(-self.step)
                        elif arrow == 'C':  # 右
                            self.galvo.move_x(self.step)
                    elif key == '+' or key == '=':  # 增加步长
                        self.step = min(0.5, self.step + 0.01)
                        print(f"\n[步长] {self.step:.3f}V")
                    elif key == '-':  # 减小步长
                        self.step = max(0.01, self.step - 0.01)
                        print(f"\n[步长] {self.step:.3f}V")
        
        finally:
            # 恢复终端设置
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self.close()
    
    def record_point(self):
        """记录标定点"""
        record = {
            'xv': self.galvo.current_xv,
            'yv': self.galvo.current_yv
        }
        self.records.append(record)
        print(f"\n[记录 {len(self.records)}] Galvo:({record['xv']:.2f}V, {record['yv']:.2f}V)")
    
    def save_records(self):
        """保存记录到文件"""
        if not self.records:
            print("[提示] 没有记录可保存")
            return
        
        filename = "galvo_positions.txt"
        with open(filename, 'w') as f:
            f.write("# 振镜电压记录\n")
            f.write("# xv(V), yv(V)\n")
            for r in self.records:
                f.write(f"{r['xv']:.4f}, {r['yv']:.4f}\n")
        
        print(f"[保存] {len(self.records)} 个位置点 -> {filename}")
    
    def close(self):
        """清理资源"""
        self.galvo.center_position()
        self.galvo.close()
        print("\n[关闭] 标定系统")


if __name__ == "__main__":
    recorder = CalibrationRecorder()
    recorder.run()

