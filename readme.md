ffplay -f v4l2 -input_format mjpeg -video_size 1280x480 -fflags nobuffer -flags low_delay -i /dev/video0
vcgencmd measure_temp


### 标定
1. 双目内参，外参
2. 振镜仿射标定





### 性能分析
fps: 100
resolution: 640 * 480
时间：
    图像获取： 2~10， 平均5
    双目矫正： 15， 可以关掉
    红点检测： 15，可以优化到5ms左右
    激光控制： 1~2，
    总时间： 5 + 5 + 1 = 11ms， 可以做到100hz频率跟踪红点，但识别蚊子速度可能需要20ms，这样总时间大概30ms，帧率大概30hz