#!/usr/bin/env python3
"""激光亮度控制 - GPIO18 PWM"""

import RPi.GPIO as GPIO


class Laser:
    """激光控制器"""
    
    def __init__(self, pin=18, frequency=1000):
        """初始化激光控制器"""
        self.pin = pin
        self.frequency = frequency
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.OUT)
        
        self.pwm = GPIO.PWM(self.pin, self.frequency)
        self.pwm.start(0)  # 默认关闭
        self._brightness = 0
    
    def on(self, brightness=100):
        """打开激光"""
        self.set_brightness(brightness)
    
    def off(self):
        """关闭激光"""
        self.set_brightness(0)
    
    def set_brightness(self, brightness):
        """设置亮度 (0-100%)"""
        self._brightness = max(0, min(100, brightness))
        self.pwm.ChangeDutyCycle(self._brightness)
    
    def get_brightness(self):
        """获取当前亮度"""
        return self._brightness
    
    def close(self):
        """关闭并清理资源"""
        self.pwm.stop()
        GPIO.cleanup(self.pin)


if __name__ == "__main__":
    import time
    
    laser = Laser()
    
    try:
        # # 测试：逐渐增加亮度
        # print("测试激光控制")
        # for brightness in range(0, 101, 20):
        #     laser.set_brightness(brightness)
        #     print(f"亮度: {brightness}%")
        #     time.sleep(1)
        
        # laser.off()
        # print("关闭激光")

        laser.on(10)
        time.sleep(10000)
        
    except KeyboardInterrupt:
        print("\n中断")
    finally:
        laser.close()
