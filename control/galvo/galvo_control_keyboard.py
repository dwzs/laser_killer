#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
键盘控制振镜
"""

import sys
import termios
import tty
import select

# 支持作为模块导入和直接运行
try:
    from .galvo_controller import GalvoController
except ImportError:
    from galvo_controller import GalvoController


class KeyboardControl:
    """键盘控制器"""
    
    def __init__(self):
        """初始化"""
        self.galvo = GalvoController()
        self.step = 0.1  # 电压步长
        
        print("[键盘控制] 已启动")
        print("  方向键: 移动振镜")
        print("  c: 回到中心")
        print("  +/-: 调整步长")
        print("  q: 退出")
    
    def run(self):
        """运行控制循环"""
        # 保存终端设置
        old_settings = termios.tcgetattr(sys.stdin)
        
        try:
            tty.setcbreak(sys.stdin.fileno())
            
            while True:
                # 显示当前状态
                print(f"\r[电压] X:{self.galvo.current_xv:>6.2f}V  Y:{self.galvo.current_yv:>6.2f}V  "
                      f"步长:{self.step:.3f}V", end='', flush=True)
                
                # 读取键盘
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    
                    if key == 'q':  # 退出
                        break
                    elif key == 'c':  # 回中心
                        self.galvo.center()
                        print("\n[中心]")
                    elif key == '\x1b':  # 方向键
                        sys.stdin.read(1)  # 跳过 '['
                        arrow = sys.stdin.read(1)
                        if arrow == 'A':  # 上
                            self.galvo.set_voltage(self.galvo.current_xv, 
                                                  self.galvo.current_yv + self.step)
                        elif arrow == 'B':  # 下
                            self.galvo.set_voltage(self.galvo.current_xv, 
                                                  self.galvo.current_yv - self.step)
                        elif arrow == 'D':  # 左
                            self.galvo.set_voltage(self.galvo.current_xv - self.step, 
                                                  self.galvo.current_yv)
                        elif arrow == 'C':  # 右
                            self.galvo.set_voltage(self.galvo.current_xv + self.step, 
                                                  self.galvo.current_yv)
                    elif key == '+' or key == '=':  # 增大步长
                        self.step = min(0.5, self.step + 0.01)
                        print(f"\n[步长] {self.step:.3f}V")
                    elif key == '-':  # 减小步长
                        self.step = max(0.01, self.step - 0.01)
                        print(f"\n[步长] {self.step:.3f}V")
        
        finally:
            # 恢复终端设置
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self.galvo.close()
            print("\n[退出]")


if __name__ == "__main__":
    control = KeyboardControl()
    control.run()

