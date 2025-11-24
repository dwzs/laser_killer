#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
振镜驱动器 - 最底层的DAC控制
只负责将电压值写入MCP4922 DAC，不涉及任何坐标转换
"""

import spidev


class GalvoDriver:
    """振镜驱动器（纯电压控制）"""
    
    def __init__(self, bus=0, device=0):
        """初始化SPI"""
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = 1000000
        
        # DAC通道配置
        self.channel_a = '0011'  # 通道A
        self.channel_b = '1011'  # 通道B
        
        # 电压范围
        self.v_min = 0.0
        self.v_max = 4.8
        
        print("[驱动器] 初始化完成")
    
    def voltage_to_dac(self, voltage):
        """电压转DAC码值 (0-5V -> 0-4095)"""
        voltage = max(self.v_min, min(self.v_max, voltage))
        return int(voltage * 819.2)  # 4096 / 5
    
    def write_dac(self, channel, voltage):
        """写入DAC通道"""
        dac_code = self.voltage_to_dac(voltage)
        voltage_bin = bin(dac_code)[2:].zfill(12)
        
        # 拼接16位数据
        data = channel + voltage_bin
        byte1 = int(data[:8], 2)
        byte2 = int(data[8:], 2)
        
        self.spi.xfer2([byte1, byte2])
    
    def set_voltage(self, voltage_a, voltage_b):
        """
        设置两个通道的电压
        
        参数:
            voltage_a: 通道A电压 (0-5V)
            voltage_b: 通道B电压 (0-5V)
        """
        self.write_dac(self.channel_a, voltage_a)
        self.write_dac(self.channel_b, voltage_b)
    
    def close(self):
        """关闭SPI"""
        self.spi.close()
        print("[驱动器] 关闭")


if __name__ == "__main__":
    import time
    
    driver = GalvoDriver()
    
    # 测试：设置不同电压
    print("测试：扫描电压")
    for v in [2.4, 3.0, 2.0, 2.4]:
        driver.set_voltage(v, v)
        print(f"  电压: {v}V")
        time.sleep(0.5)
    
    driver.close()
