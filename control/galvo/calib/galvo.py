#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
振镜控制脚本 - 绘制正方形图案
通过 MCP4922 DAC 控制 X/Y 轴振镜，让激光绘制正方形
"""

import time
import spidev


class GalvoController:
    """振镜控制器"""
    
    def __init__(self, bus=0, device=0):
        """初始化 SPI 和振镜参数"""
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = 1000000
        
        # DAC 通道配置
        self.channel_x = '0011'  # 通道 A (X 轴)
        self.channel_y = '1011'  # 通道 B (Y 轴)

        self.direction_x = -1    # 1表示递增，-1表示递减
        self.direction_y = 1    # 1表示递增，-1表示递减
        
        # 电压范围（根据振镜驱动器调整）
        self.v_min = 0.0
        self.v_max = 4.8
        self.v_center = (self.v_min + self.v_max) / 2  # 中心电压 2.4V
        
        self.current_xv = 0
        self.current_yv = 0
        self.xv_min = self.v_min - self.v_center
        self.yv_min = self.v_min - self.v_center
        self.xv_max = self.v_max - self.v_center
        self.yv_max = self.v_max - self.v_center

        self.center_position()
        print("[INFO] 振镜控制器初始化完成")
        print(f"  电压范围: {self.v_min}V ~ {self.v_max}V")
        print(f"  中心电压: {self.v_center}V")
    
    def voltage_to_dac(self, voltage):
        """
        将电压转换为 DAC 码值
        
        参数:
            voltage: 电压值 (0-5V)
        
        返回:
            DAC 码值 (0-4095)
        """
        # 限幅保护
        voltage = max(self.v_min, min(self.v_max, voltage))
        return int(voltage * 819.2)  # 819.2 = 4096 / 5
    
    def dac_write(self, channel, voltage):
        """
        写入 DAC
        
        参数:
            channel: 通道配置字符串 ('0011' 或 '1011')
            voltage: 电压值 (V)
        """
        dac_code = self.voltage_to_dac(voltage)
        voltage_bin = bin(dac_code)[2:].zfill(12)
        
        # 拼接 16 位数据：4位控制 + 12位数据
        data = channel + voltage_bin
        byte1 = int(data[:8], 2)
        byte2 = int(data[8:], 2)
        
        self.spi.xfer2([byte1, byte2])
    
    def set_position(self, voltage_x, voltage_y):
        """
        设置振镜位置
        
        参数:
            voltage_x: X 轴相对中心电压的电压，右边为正，左边为负 (V)
            voltage_y: Y 轴相对中心电压的电压，上边为正，下边为负 (V)
        """
        self.dac_write(self.channel_x, self.v_center + voltage_x * self.direction_x)
        self.dac_write(self.channel_y, self.v_center + voltage_y * self.direction_y)
        self.current_xv = voltage_x
        self.current_yv = voltage_y
    
    def move_x(self, dxv = 0.1):
        """
        移动X轴
        
        参数:
            dv: X轴电压步进
        """
        self.current_xv += dxv
        if self.current_xv > self.xv_max:
            self.current_xv = self.xv_max
            print(f"[warning] X轴到达最大电压: {self.current_xv:.2f}V")
        elif self.current_xv < self.xv_min:
            self.current_xv = self.xv_min
            print(f"[warning] X轴到达最小电压: {self.current_xv:.2f}V")
        self.set_position(self.current_xv, self.current_yv)

    def move_y(self, dyv = 0.1):
        """
        移动Y轴
        
        参数:
            dyv: Y轴电压步进
        """
        self.current_yv += dyv
        if self.current_yv > self.yv_max:
            self.current_yv = self.yv_max
            print(f"[warning] Y轴到达最大电压: {self.current_yv:.2f}V")
        elif self.current_yv < self.yv_min:
            self.current_yv = self.yv_min
            print(f"[warning] Y轴到达最小电压: {self.current_yv:.2f}V")
        self.set_position(self.current_xv, self.current_yv)


    def move_dir(self, dxv = 0.1, dyv = 0.1):
        """
        移动方向
        
        参数:
            dxv: X轴电压步进
            dyv: Y轴电压步进
        """
        self.move_x(dxv)
        self.move_y(dyv)
    
    def center_position(self):
        """回到中心位置"""
        print(f"[INFO] 回到中心位置: ({self.v_center:.2f}V, {self.v_center:.2f}V)")
        self.set_position(0, 0)
    
    def close(self):
        """关闭 SPI 连接"""
        self.spi.close()
        print("[INFO] SPI 连接已关闭")


def main():

    # 初始化控制器
    galvo = GalvoController(bus=0, device=0)
    galvo.center_position()

    # # 2. 移动X轴
    # for i in range(10):
    #     galvo.move_x(0.1)
    #     time.sleep(0.1)
    # # 3. 移动Y轴
    # for i in range(10):
    #     galvo.move_y()
    #     time.sleep(0.1)

    # 4. 移动方向
    for i in range(10):
        galvo.move_dir(0.1, 0.1)
        time.sleep(0.1)

    print(f"[INFO] X轴当前相对电压: {galvo.current_xv:.2f}V")
    print(f"[INFO] Y轴当前相对电压: {galvo.current_yv:.2f}V")

    galvo.center_position()


if __name__ == "__main__":
    main()