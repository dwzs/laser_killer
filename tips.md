  
# 需求分析

### 1.蚊子特性
        体积: 
            长 3~6
            翼展6~12
        速度：
            水平–2 m/s； 
            垂直 0.3–0.6 m/s
            短距离冲刺：2.5–3 m/s
        飞行轨迹：
            随机性强，快速改变方向，每秒变化方向十几次。
                轨迹常常呈 Z 字形，抖动，螺旋状，小幅随机振荡。
            高机动性
                转弯半径极小，仅几厘米甚至更小。
                可瞬间改变速度与方向（毫秒级）。
### 2.感知的需求
        静态：蚊子纵向（3~6mm）在图片上最少要占16像素，最好32像素以上。
            分辨率
            范围

        动态
            分辨率
            范围
            帧率


        1. 1m的图像范围，若蚊子占用20个像素，图像像素点为4000。
### 3.控制的需求
        云台精度
        云台速度
        云台范围
        



# 性能分析 
                   all        670        670       0.97      0.934      0.982      0.748
            albopictus        670        670       0.97      0.934      0.982      0.748
Speed: 0.2ms preprocess, 1.2ms inference, 0.0ms loss, 0.7ms postprocess per image
Results saved to /home/wsy/laser_mosquite_killer/runs/detect/train
💡 Learn more at https://docs.ultralytics.com/modes/train

### 模型加载
20ms

### gpu：(640 * 640 jpg)
1. 推理（图像多）： 2.1ms = 0.2+1.2+0.7（gpu跑满，平均时间）
2. 预热（第一张）： 410ms
2. 推理（图像少）：5ms （gpu没跑满）

### cpu：
2. 预热（第一张）： 160ms
2. 推理（图像少）：30ms 


### ZEDXMini相机参数
[LEFT_CAM_FHD1200]
fx=736.862
fy=736.696
cx=999.971
cy=570.414
k1=-0.0120856
k2=-0.0309258
p1=0.000219736
p2=5.4555e-05
k3=0.00802708

[RIGHT_CAM_FHD1200]
fx=737.375
fy=736.982
cx=970.855
cy=630.481
k1=-0.0143275
k2=-0.0287108
p1=0.000223389
p2=-0.000192297
k3=0.00736656

Baseline=49.8789
TY=0.0509066
TZ=0.167848
CV_FHD=0.0107261
CV_SVGA=0.0107261
CV_FHD1200=0.0107261
RX_FHD=0.00124871
RX_SVGA=0.00124871
RX_FHD1200=0.00124871
RZ_FHD=0.00138949
RZ_SVGA=0.00138949
RZ_FHD1200=0.00138949




1. 深度计算与误差
z = bf/d  # b（基线）； f(焦距，可以是像素数量)；d（视差，也可以是像素数量）
b = 49.9mm
f = 737 像素(2.19mm)

假如待检测深度目标在z轴上。
z = 36776 / d
当深度在1m左右时（即d=37时）
d = 37 像素时： z = 993.9 mm
d = 36 像素时： z = 1021.6 mm
dz = 1021.6 - 993.9 = 27.7 mm

当深度在2m左右时（即d=19时）
d = 19 像素时： z = 1935.6 mm
d = 20 像素时： z = 1838.8 mm
dz = 1935.6 - 1838.8 = 96.8 mm

因此深度在1m 左右时，每个像素差对应的深度大概30mm， 这是深度误差，或者分辨率。
因此深度在2m 左右时，每个像素差对应的深度大概97mm， 这是深度误差，或者分辨率。

2. 平面距离计算与误差
x = dz/f # d(像素点距离中心像素点的距离，单位像素)；z（深度）；f（焦距，单位像素）

假如z = 1000mm
x = 1.36 * d

d = 1 像素时： x = 1.36 mm
d = 2 像素时： x = 2.72 mm
因此深度在1m 左右时，每个像素差对应的平面距离大概1.36mm， 这是平面误差，或者分辨率。

原理：
1. 双目识别并定位蚊子（包括深度）
    问题：识别精度，背景，环境光干扰。
2. 双轴振镜控制激光方向。（振镜角度会不会不够）
    问题：振镜精度，响应速度，调节范围。
3. 激光定位/伤害蚊子
    问题：激光波长，功率的选择，对人眼的危害。



steps：
1. 感知
    a. 识别： yolo
    b. 定位： 双目对级几何。
2. 控制
    a. 瞄准




yolo detect train data=./resources/mosquito_y8/data.yaml model=yolov8n.pt epochs=100 imgsz=640 batch=16

### usb双目参数




tips:
标定文件：/usr/local/zed/settings/SN53386446.conf
红点深度：920mm（未去畸变时图像计算得到896）

ffplay -f v4l2 -input_format mjpeg -video_size 1280x480 -fflags nobuffer -flags low_delay -i /dev/video0
ffplay -f v4l2 -input_format mjpeg -video_size 2560x720 -fflags nobuffer -flags low_delay -i /dev/video0

### 物料清单
1. 感知
    双目摄像头

2. 控制
    激光笔
    振镜
    振镜驱动
        dac： MCP4922
        op： OPA2277
        电阻：

3. 控制器
    树莓派
    jetson orin


### tips:
树莓派温度： vcgencmd measure_temp

rpicam-vid -t 100000 --framerate 20  --width 3280 --height 2464 -o slowmo.h264


### 问题记录：
1. 当激光点距离中心点较远时，激光点会抖动，激光器距离墙面1m， 红点坐标（-18, 0）, 抖动范围1~5mm， 没秒抖一到两次；
    红点距离中心点越近，抖动频率和范围会减少。