#!/usr/bin/env python3
"""
简洁版蚊子检测器 - 基于形态特征
流程：预处理 → 筛选候选区域 → 逐个判断 → 输出结果
蚊子特点：
    1. 结构： 头，身体，翅膀，腿
    2. 头： 三角形，最黑（90）
    3. 身体： 长条形，次黑（70），被翅膀覆盖，有的品种上有白斑
    4. 翅膀： 长条形，较黑（50），覆盖在身体上
    5. 腿： 细长，较黑（30），分布在身体两侧，有6条
    6. 白斑： 白色，分布在身体上，有的品种上有白斑

检测逻辑：明显特征快速筛选，细节特征精细判断
    1. 明显特征快速筛选：
        1.1 颜色：黑色物体（阈值可以严格些，后面根据蚊子最明显的特征对对应区域调整阈值判断）
        1.2 面积：合适大小
        1.3 形状：细长形
    2. 细节特征精细判断：
        2.1 颜色：不同部位颜色不同
        2.2 面积：合适大小
        2.3 形状：
             a. 是否包含蚊子各个部位，
             b. 各个部位颜色是否正确
             c. 各个部位形状是否正确
             d. 各个部位之间的关系是否正确

检测流程：
    A: 静止的蚊子（翅膀会挡住身体）
        1. 找到图片中所有最黑的点
        2. 以对这些最黑为中心，扩展一个应该包含蚊子的区域
        3. 对上面每个区域做仔细判断：
            1. 颜色判断：对颜色聚类，分成3~4个颜色区间，对应头，身体，翅膀，腿
            2. 形状判断：上面每个颜色区间的形状做判断
            3. 结构关系判断：每个形状之间的位置关系
        4. 构造代价函数，判断是蚊子的可能性。

    B: 飞行的蚊子（翅膀应该看不见，或者非常小的灰度）
        1. 筛选有效区域
            1. 找到图片中所有最黑的点
            2. 以对这些最黑为中心，扩展一个应该包含蚊子的区域
        3. 蚊子判断：
            1. 颜色判断：对颜色聚类，分成3~4个颜色区间，对应头，身体，翅膀，腿
            2. 形状判断：上面每个颜色区间的形状做判断
            3. 结构关系判断：每个形状之间的位置关系
        4. 构造代价函数，判断是蚊子的可能性。

流程2：先判断身体部位，在判断蚊子，方案较难；因为其实识别单个蚊子部件比识别整个蚊子难度大。
    静止的蚊子（翅膀会挡住身体）
        1. 筛选有效区域
            1. 找到图片中所有最黑的点块
            2. 以对这些最黑为中心，扩展一个应该包含蚊子的区域
        2. 有用信息提取
            1. 颜色（感知的基础）：即使相同颜色也有颜色梯度，平滑度
            2. 轮廓： 根据阈值大小有不同明显度的轮廓
            3. 形状

            分割： 根据轮廓，
            tips： 蚊子只可能包含黑色，灰色，白色，其他颜色全部可以排除，抠掉。
        3. 蚊子判断：
            身体部位的识别：
                头： 三角形，最黑（90）
                身体： 长条形，次黑（70），被翅膀覆盖，有的品种上有白斑
                翅膀： 长条形，较黑（50），覆盖在身体上
                腿： 细长，较黑（30），分布在身体两侧，有6条
            蚊子的识别： 蚊子有不同部位按指定结构组合
                1. 部位完整性： 是否缺失某个部位
                2. 部位逻辑关系： 部位之间是否符合蚊子的结构关系
            基于以上构建代价函数，判断是蚊子的可能性。

流程3：先判断蚊子，再确定是否为蚊子。
    静止的蚊子（翅膀会挡住身体）
        1. 蚊子粗判断：通过颜色（假设蚊子头为图片中最黑的点块）来找到头和身体
            1. 找到图片中所有黑的点块，绿色通道阈值低于50
            2. 筛选点块，从面积(25 ~ 3600像素)、长宽比(1 ~ 5.0)，筛选出可能包含蚊子的点块
            2. 以对这些黑块中点为中心，扩展一个应该包含蚊子的正方形区域，边长可定为60像素
        2. 蚊子细判断：在可能区间快速筛选出可能是蚊子的区域，根据头和身体的颜色、位置、面积、长宽比关系选择
            1. 颜色判断：蚊子为黑色，灰色，白色，其他颜色全部可以排除，抠掉。
            2. 图像分割：根据物体边缘颜色突变，分割目标区域，其中包含头、身体、翅膀、腿。
            3. 形状判断：头为三角形，身体为长条形，翅膀为长条形，腿为细长形。
            4. 结构关系判断：头与身体相连，身体与翅膀相连，身体与腿相连。但不同角度看这个关系不同。
            5. 代价函数：根据身体的完整性与结构关系构建代价函数

            tips： 
                1. 蚊子只可能包含黑色，灰色，白色，其他颜色全部可以排除，抠掉。
                2. 头： 三角形，最黑（90）
                3. 身体： 长条形，次黑（70），被翅膀覆盖，，长宽比（2~10）
        3. 蚊子细判断：
            1. 轮廓完整性： 哪些零件缺失

tips：
    1. 单纯的颜色信息容易受背景，光线影响，相对颜色信息，轮廓信息是否更重要。
    2. 部位和结构相关，部位识别和结构识别是相互依赖的。（比如细长型的黑色，当连在长条形身体上，与身体成指定角度时，很可能是蚊子腿，假如对应的有六条这种细长黑线，则可能性还会升高）
    3. 图像识别最重要的能力：
        1. 专注： 处理自己重要的区域，提高效率
        2. 分割： 根据边界把图像分割成不同区域，现实空间中不同的物体在图像中对应不同颜色，即使相同颜色，在空间中由于光线，表面等因素，也会出现边界。
        3. 整合： 属于统一对象的区域整合成一个整体，比如彩色的盘子，虽然有很多区域，但他们同属于一个对象，现实中人对事物的理解，操作视乎都以对象为基础。
    4. 计算机处理图像的能力：
        1. 索引： 根据索引获取某个像素值
        2. 运算： 四则运算，逻辑运算，比较运算，位运算，
    5. 蚊子重要特征：
        1. 距离较远时看不见腿。
        2. 翅膀会挡住身体。
        3. 头的黑色比身体更深，且相连。

        
"""


import cv2
import numpy as np
import time


class MosquitoDetector:
    """蚊子检测器"""
    
    def __init__(self):
        # ========== 参数配置 ==========
        # 颜色参数
        self.max_brightness = 120      # 蚊子最大亮度（黑色）
        
        # 面积参数
        self.min_area = 80
        self.max_area = 6000
        
        # 形状参数
        self.min_aspect_ratio = 1.8    # 最小长宽比
        self.max_circularity = 0.6     # 最大圆形度
        self.min_solidity = 0.3        # 最小实心度（腿间有空隙）
        self.max_solidity = 0.8        # 最大实心度


        # 形态学处理
        self.original_image = None
        self.gray_image = None
        self.blurred_image = None
        self.processed_image = None

        self.valid_regions = []  # 一些点，有效区域是以这些点为中心的圆
        self.valid_region_length = 30 # 有效区域正方形的边长，单位像素

        # 特征检测


    def preprocess_image(self, image_path):
        """1. 图像预处理：去噪"""
        img = cv2.imread(image_path)
        self.original_image = img
        self.gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.image_r = img[:, :, 2]
        self.image_g = img[:, :, 1]
        self.image_b = img[:, :, 0]
        
        # # 高斯模糊去噪
        # self.blurred_image = cv2.GaussianBlur(self.gray_image, (5, 5), 0)
        # self.processed_image = self.blurred_image
        
        cv2.imshow('Original Image', self.original_image)
        # cv2.imshow('Gray Image', self.gray_image)
        # cv2.imshow('Blurred Image', self.blurred_image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        self.processed_image = img
        
        return self.processed_image
    
    
    # def filter_valid_region(self, processed_image):
    #     """2. 筛选有效信息：筛选出可能是蚊子的圆区域
    #         input: 处理后的图像
    #         return: 可能包含蚊子的正方形区域列表
    #         1. 先找到图片中所有最黑的点块（头），绿色通道阈值低于50
    #         2. 筛选点块，从面积(25 ~ 3600像素)、长宽比(1 ~ 5.0)，筛选出可能包含蚊子的点块
    #         3. 以对这些黑块中点为中心，扩展一个应该包含蚊子的正方形区域，边长可定为60像素
    #     """
    #     # ===== 可调参数 =====
    #     threshold_green = 40      # 绿色通道阈值
    #     min_pixels = 4            # 最小像素点数
    #     max_pixels = 900          # 最大像素点数
    #     min_bbox_pixels = 4       # 最小外接矩形像素点数
    #     max_bbox_pixels = 1200    # 最大外接矩形像素点数
    #     min_fill_ratio = 0.5      # 最小填充率（轮廓像素点数/外接矩形像素点数）
    #     max_fill_ratio = 1.0      # 最大填充率
    #     min_aspect_ratio = 1.0    # 最小长宽比
    #     max_aspect_ratio = 2.0    # 最大长宽比
    #     region_size = 60          # 正方形区域边长
    #     # ===================
        
    #     print("\n========== 筛选黑色部分 ==========")
        
    #     # 1. 找到绿色通道中所有最黑的点块
    #     green_channel = processed_image[:, :, 1]
    #     _, binary = cv2.threshold(green_channel, threshold_green, 255, cv2.THRESH_BINARY_INV)
    #     cv2.imshow("Binary Image (Green Channel)", binary)
        
    #     # 2. 找到所有轮廓
    #     contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
    #     # 计算轮廓内的像素点数量
    #     def count_contour_pixels(contour, img_shape):
    #         """计算轮廓内包含的像素点数量"""
    #         mask = np.zeros(img_shape, dtype=np.uint8)
    #         cv2.drawContours(mask, [contour], -1, 255, -1)  # 填充轮廓
    #         return cv2.countNonZero(mask)
        
    #     # 打印所有轮廓的像素点数量（从小到大）
    #     pixel_counts = [count_contour_pixels(c, binary.shape) for c in contours]
    #     pixel_counts_sorted = sorted(pixel_counts)
    #     zero_count = sum(1 for p in pixel_counts if p == 0)
    #     print(f"找到 {len(contours)} 个轮廓")
    #     print(f"其中像素点数为0的有 {zero_count} 个（通常是单点或线段）")
    #     print(f"轮廓像素点数从小到大：{pixel_counts_sorted}")
        
    #     # 计算并打印外接矩形包含的像素点数量
    #     bbox_pixel_counts = []
    #     for c in contours:
    #         x, y, w, h = cv2.boundingRect(c)
    #         bbox_pixel_counts.append(w * h)
    #     bbox_pixel_counts_sorted = sorted(bbox_pixel_counts)
    #     print(f"外接矩形像素点数从小到大：{bbox_pixel_counts_sorted}")
        
    #     # 过滤掉像素点数为0的轮廓
    #     contours_with_pixels = [(c, count_contour_pixels(c, binary.shape)) for c in contours]
    #     contours = [c for c, count in contours_with_pixels if count > 0]
    #     print(f"过滤后剩余 {len(contours)} 个有效轮廓")
        
    #     # 3. 筛选轮廓：像素点数、填充率和长宽比
    #     valid_regions = []
    #     valid_contours = []  # 保存筛选后的轮廓用于可视化
    #     valid_pixel_counts = []  # 保存筛选后的轮廓像素点数
    #     valid_bbox_pixel_counts = []  # 保存筛选后的外接矩形像素点数
    #     valid_fill_ratios = []  # 保存筛选后的填充率
    #     h, w = processed_image.shape[:2]
        
    #     for contour in contours:
    #         # 计算轮廓内像素点数
    #         pixel_count = count_contour_pixels(contour, binary.shape)
    #         if pixel_count < min_pixels or pixel_count > max_pixels:
    #             continue
            
    #         # 计算外接矩形像素点数
    #         x, y, cw, ch = cv2.boundingRect(contour)
    #         bbox_pixel_count = cw * ch
    #         if bbox_pixel_count < min_bbox_pixels or bbox_pixel_count > max_bbox_pixels:
    #             continue
            
    #         # 计算填充率（轮廓像素点数 / 外接矩形像素点数）
    #         fill_ratio = pixel_count / bbox_pixel_count
    #         if fill_ratio < min_fill_ratio or fill_ratio > max_fill_ratio:
    #             continue
            
    #         # 计算长宽比
    #         aspect_ratio = max(cw, ch) / (min(cw, ch) + 1e-6)
    #         if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
    #             continue
            
    #         # 保存通过筛选的轮廓和像素点数信息
    #         valid_contours.append(contour)
    #         valid_pixel_counts.append(pixel_count)
    #         valid_bbox_pixel_counts.append(bbox_pixel_count)
    #         valid_fill_ratios.append(fill_ratio)
            
    #         # 4. 以轮廓中点为中心，扩展正方形区域
    #         M = cv2.moments(contour)
    #         if M["m00"] == 0:
    #             continue
    #         cx = int(M["m10"] / M["m00"])
    #         cy = int(M["m01"] / M["m00"])
            
    #         # 计算正方形区域的边界
    #         half_size = region_size // 2
    #         x1 = max(0, cx - half_size)
    #         y1 = max(0, cy - half_size)
    #         x2 = min(w, cx + half_size)
    #         y2 = min(h, cy + half_size)
            
    #         valid_regions.append((x1, y1, x2, y2))
        
    #     # 打印筛选后的像素点数信息
    #     print(f"\n筛选出 {len(valid_regions)} 个有效区域")
    #     print(f"筛选后的轮廓像素点数（从小到大）：{sorted(valid_pixel_counts)}")
    #     print(f"筛选后的外接矩形像素点数（从小到大）：{sorted(valid_bbox_pixel_counts)}")
    #     print(f"筛选后的填充率（从小到大）：{[f'{r:.2%}' for r in sorted(valid_fill_ratios)]}")
        
    #     # 显示筛选后的二值图
    #     filtered_binary = np.zeros_like(binary)
    #     cv2.drawContours(filtered_binary, valid_contours, -1, 255, -1)  # -1表示填充
    #     cv2.imshow("Filtered Binary", filtered_binary)
        
    #     # 可视化
    #     vis_image = processed_image.copy()
    #     for (x1, y1, x2, y2) in valid_regions:
    #         cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
    #     cv2.imshow("Valid Regions", vis_image)
    #     cv2.waitKey(0)
    #     cv2.destroyAllWindows()
        
    #     return valid_regions 
   
    def filter_valid_region2(self, processed_image):
        """2. 筛选有效信息：筛选出可能是蚊子的轮廓
            input: 处理后的图像
            return: 可能是蚊子的轮廓列表
            1. 找身体和头颜色：先找到图片中所有黑色（0~100）的点块
            2. 找身体和头形状：
                1. 点块占用像素数量： 10~300像素
                2. 矩形边框边长范围： 10~3000像素
                3. 矩形边框长宽比： 1~5.0
                4. 矩形边框包含像素数量： 10~3000像素
                5. 填充率（轮廓像素点数 / 外接矩形像素点数）： 0.3~0.99
        """
        # ===== 可调参数 =====
        threshold_green = 100     # 绿色通道阈值
        min_pixels = 10           # 最小像素点数
        max_pixels = 50000          # 最大像素点数
        min_bbox_pixels = 10      # 最小外接矩形像素点数
        max_bbox_pixels = 100000    # 最大外接矩形像素点数
        min_fill_ratio = 0.3      # 最小填充率
        max_fill_ratio = 0.99     # 最大填充率
        min_aspect_ratio = 1.0    # 最小长宽比
        max_aspect_ratio = 5.0    # 最大长宽比
        # ===================
        
        print("\n========== 筛选黑色部分 (方法2) ==========")
        
        # 1. 筛选出绿色通道小于阈值的点
        b, g, r = cv2.split(processed_image)
        mask_green = g < threshold_green
        
        # 2. 从这些点中筛选出黑色的点（R、G、B都小于阈值）
        mask_black = (r < threshold_green) & (g < threshold_green) & (b < threshold_green)
        
        # 3. 生成黑色二值图
        binary = np.zeros(g.shape, dtype=np.uint8)
        binary[mask_black] = 255
        cv2.imshow("black binary", binary)
        
        # 2. 找到所有轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 辅助函数：计算轮廓内像素点数
        def count_pixels(contour):
            mask = np.zeros(binary.shape, dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, -1)
            return cv2.countNonZero(mask)
        
        # 3. 筛选轮廓
        valid_contours = []
        valid_fill_ratios = []  # 保存填充率
        valid_pixel_counts = []  # 保存色块像素点数
        valid_bbox_pixel_counts = []  # 保存外接矩形像素点数
        
        for contour in contours:
            # 筛选色块像素点数
            pixel_count = count_pixels(contour)
            if pixel_count < min_pixels or pixel_count > max_pixels:
                continue
            
            # 筛选外接矩形像素点数
            x, y, cw, ch = cv2.boundingRect(contour)
            bbox_pixels = cw * ch
            if bbox_pixels < min_bbox_pixels or bbox_pixels > max_bbox_pixels:
                continue
            
            # 筛选填充率（色块像素点数 / 外接矩形像素点数）
            fill_ratio = pixel_count / bbox_pixels
            if fill_ratio < min_fill_ratio or fill_ratio > max_fill_ratio:
                continue
            
            # 筛选外接矩形长宽比
            aspect_ratio = max(cw, ch) / (min(cw, ch) + 1e-6)
            if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
                continue
            
            # 保存筛选后的轮廓和信息
            valid_contours.append(contour)
            valid_fill_ratios.append(fill_ratio)
            valid_pixel_counts.append(pixel_count)
            valid_bbox_pixel_counts.append(bbox_pixels)
        
        # 打印筛选结果
        print(f"\n筛选出 {len(valid_contours)} 个可能是蚊子的轮廓")
        print(f"色块像素点数（从小到大）：{sorted(valid_pixel_counts)}")
        print(f"外接矩形像素点数（从小到大）：{sorted(valid_bbox_pixel_counts)}")
        print(f"填充率（从小到大）：{[f'{r:.2%}' for r in sorted(valid_fill_ratios)]}")
        
        # 可视化
        filtered_binary = np.zeros_like(binary)
        cv2.drawContours(filtered_binary, valid_contours, -1, 255, -1)
        cv2.imshow("Filtered Binary", filtered_binary)
        
        
        return valid_contours

    # def judge_each_region(self, processed_image, contours):
    #     """3. 逐个判断：判断每个轮廓是否为蚊子
    #         input: 处理后的图像，候选轮廓列表
    #         return: 检测结果字典列表
    #             每个蚊子占用的像素
    #             每个蚊子的可能性
    #         流程：
    #             1. 颜色判断：蚊子为黑色，灰色，白色，其他颜色全部可以排除，抠掉。
    #             2. 图像分割：根据物体边缘颜色突变，分割目标区域，其中包含头、身体、翅膀、腿。
    #             3. 形状判断：头为三角形，身体为长条形，翅膀为长条形，腿为细长形。
    #             4. 结构关系判断：头与身体相连，身体与翅膀相连，身体与腿相连。但不同角度看这个关系不同。
    #             5. 代价函数：根据身体的完整性与结构关系构建代价函数

    #         # 1. 对输入的每个轮廓，以轮廓中点为中心，扩展一个应该包含蚊子的区域，边长可定为60像素的矩形区域
    #         # 2. 找到上面区域内的蚊子：
    #         #     1. 只保留蚊子颜色：黑色，白色
    #         #     2. 找轮廓：canny 找边缘
    #         #     3. 颜色判断：计算每个轮廓内平均颜色
    #         #     4. 部位判断：
    #         #         头：最黑的是否为近似三角形
    #         #         翅膀：第二黑的是否为近似椭圆
    #         #         腿：第三黑的是否类似细线


    #     """
    #     print("\n========== 判断每个区域 ==========")
        
    #     results = []
    #     # 正确的灰度转换：使用加权平均 Gray = 0.299*R + 0.587*G + 0.114*B
    #     gray_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2GRAY)
    #     img_h, img_w = processed_image.shape[:2]
    #     region_size = 60  # 矩形区域边长
        
    #     # 创建一张大图用于显示所有子轮廓
    #     vis_all = processed_image.copy()
    #     # 创建一张灰度图用于显示所有ROI的灰度信息
    #     gray_combined = np.full(gray_image.shape, 255, dtype=np.uint8)  # 白色背景
    #     # 创建一张边缘图用于显示所有ROI的边缘
    #     edges_combined = np.zeros(gray_image.shape, dtype=np.uint8)  # 黑色背景
    #     # 创建一张彩色图用于显示过滤后的ROI（只保留黑色）
    #     filtered_combined = np.full(processed_image.shape, 255, dtype=np.uint8)  # 白色背景
    #     # 创建一张彩色图用于显示原始ROI
    #     roi_combined = np.full(processed_image.shape, 255, dtype=np.uint8)  # 白色背景
        
    #     for i, contour in enumerate(contours):
    #         # 1. 以轮廓中点为中心，扩展矩形区域
    #         M = cv2.moments(contour)
    #         if M["m00"] == 0:
    #             continue
    #         cx = int(M["m10"] / M["m00"])
    #         cy = int(M["m01"] / M["m00"])
            
    #         half_size = region_size // 2
    #         x1 = max(0, cx - half_size)
    #         y1 = max(0, cy - half_size)
    #         x2 = min(img_w, cx + half_size)
    #         y2 = min(img_h, cy + half_size)
            
    #         # 提取扩展后的ROI区域（彩色）
    #         roi_color = processed_image[y1:y2, x1:x2].copy()

    #         # 将 roi_color 叠加到大图上
    #         roi_combined[y1:y2, x1:x2] = np.minimum(roi_combined[y1:y2, x1:x2], roi_color)

    #         # 1. 只保留黑色部分，移除其他颜色
    #         black_threshold = 170  # RGB三通道都 < 此值 → 黑色
    #         b, g, r = cv2.split(roi_color)
    #         mask_black = (r < black_threshold) & (g < black_threshold) & (b < black_threshold)
    #         # 将非黑色的区域设为白色（背景）
    #         roi_filtered = roi_color.copy()
    #         roi_filtered[~mask_black] = [255, 255, 255]  # 非黑色区域变白色
    #         # 将 roi_filtered 叠加到大图上
    #         filtered_combined[y1:y2, x1:x2] = np.minimum(filtered_combined[y1:y2, x1:x2], roi_filtered)
            
    #         # 在大图上标注区域编号和矩形框
    #         cv2.rectangle(vis_all, (x1, y1), (x2, y2), (255, 0, 0), 1)
    #         cv2.putText(vis_all, f"#{i+1}", (x1, y1-5), 
    #                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)


    #     # 显示所有图像
    #     cv2.imshow("1. ROI Regions", vis_all)
    #     cv2.imshow("2. ROI Original", roi_combined)
    #     cv2.imshow("3. Filtered (Black Only)", filtered_combined)

    #     return results

    def judge_each_region2(self, processed_image, contours):
        """3. 逐个判断：判断每个轮廓是否为蚊子
            input: 处理后的图像，候选轮廓列表
            return: 检测结果字典列表
            流程：
                1. 颜色划分：对轮廓内的像素进行颜色聚类，分成两个区间
                2. 结构划分：两个颜色对应头+身体和翅膀
                翅膀应该是长条形，头应该在两端。
        """
        # ===== 可调参数 =====
        dark_threshold = 60              # 深色区域阈值（头+身体）
        min_distance_factor = 0.5        # 最小重心距离系数（边长的倍数）
        max_distance_factor = 5.0        # 最大重心距离系数（边长的倍数）
        # ===================
        
        results = []
        excluded_count = 0  # 被排除的数量
        excluded_near = 0   # 距离太近被排除的数量
        excluded_far = 0    # 距离太远被排除的数量
        
        gray_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2GRAY)
        img_h, img_w = processed_image.shape[:2]
        
        # 创建可视化图像：显示两种颜色区域
        color_vis = processed_image.copy()
        
        for contour in contours:
            # 1. 创建轮廓掩码
            mask = np.zeros((img_h, img_w), dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, -1)  # 填充轮廓
            
            # 2. 提取轮廓内的灰度值
            contour_gray = gray_image[mask == 255]
            
            if len(contour_gray) == 0:
                continue
            
            # 3. 颜色聚类：将轮廓内像素分成两个区间
            mask_dark = (gray_image < dark_threshold) & (mask == 255)    # 头+身体：最黑
            mask_light = (gray_image >= dark_threshold) & (mask == 255)  # 翅膀：次黑
            
            pixels_dark = np.sum(mask_dark)
            pixels_light = np.sum(mask_light)
            
            # 4. 计算两种颜色的重心
            centroid_dark = None
            centroid_light = None
            
            if pixels_dark > 0:
                # 计算深色区域重心
                ys_dark, xs_dark = np.where(mask_dark)
                cx_dark = np.mean(xs_dark)
                cy_dark = np.mean(ys_dark)
                centroid_dark = (int(cx_dark), int(cy_dark))
            
            if pixels_light > 0:
                # 计算浅色区域重心
                ys_light, xs_light = np.where(mask_light)
                cx_light = np.mean(xs_light)
                cy_light = np.mean(ys_light)
                centroid_light = (int(cx_light), int(cy_light))
            
            # 5. 可视化：标记深色和浅色区域
            color_vis[mask_dark] = [0, 0, 255]    # 深色区域（头+身体）→ 红色
            color_vis[mask_light] = [255, 0, 0]   # 浅色区域（翅膀）→ 蓝色
            
            # 6. 可视化：标记重心
            if centroid_dark is not None:
                cv2.circle(color_vis, centroid_dark, 1, (0, 0, 255), -1)  # 深色重心：红色实心圆
            
            if centroid_light is not None:
                cv2.circle(color_vis, centroid_light, 1, (255, 0, 0), -1)  # 浅色重心：蓝色实心圆
            
            # 7. 筛选判断：基于头部面积和重心距离
            if centroid_dark is not None and centroid_light is not None:
                # 计算重心距离
                distance = np.sqrt((centroid_dark[0] - centroid_light[0])**2 + 
                                 (centroid_dark[1] - centroid_light[1])**2)
                
                # 计算头部（深色区域）像素数量对应的正方形边长
                # 像素数 = 边长²，所以边长 = sqrt(像素数)
                head_side_length = np.sqrt(pixels_dark)
                
                # 计算距离范围
                min_distance = min_distance_factor * head_side_length
                max_distance = max_distance_factor * head_side_length
                
                # 判断距离是否在合理范围内
                if min_distance <= distance <= max_distance:
                    # 通过筛选，标记为蚊子候选
                    # 保存结果
                    x, y, w, h = cv2.boundingRect(contour)
                    results.append({
                        'contour': contour,
                        'bbox': (x, y, w, h),
                        'dark_pixels': pixels_dark,
                        'light_pixels': pixels_light,
                        'ratio': pixels_dark / pixels_light,
                        'centroid_dark': centroid_dark,
                        'centroid_light': centroid_light,
                        'centroid_distance': distance,
                        'head_side_length': head_side_length,
                        'min_distance': min_distance,
                        'max_distance': max_distance,
                        'confidence': 0.8
                    })
                    
                    # 绘制连接线（绿色表示通过筛选）
                    cv2.line(color_vis, centroid_dark, centroid_light, (0, 255, 0), 1)
                    
                    # 绘制重心距离标签
                    label_text = f"{distance:.1f}"
                    
                    # 标签位置：在轮廓边界框的左上角
                    label_pos = (x, y - 5)
                    
                    # 绘制标签（黄色文字，加黑色描边）
                    cv2.putText(color_vis, label_text, label_pos,
                               cv2.FONT_HERSHEY_SIMPLEX, 0.2, (0, 0, 0), 1)  # 黑色描边
                    cv2.putText(color_vis, label_text, label_pos,
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1)  # 黄色文字
                    
                    # # 绘制边界框（绿色）
                    # cv2.rectangle(color_vis, (x, y), (x+w, y+h), (0, 255, 0), 1)
                else:
                    # 未通过筛选
                    excluded_count += 1
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # 判断排除原因
                    if distance < min_distance:
                        # 距离太近（红色）
                        excluded_near += 1
                        cv2.line(color_vis, centroid_dark, centroid_light, (0, 0, 255), 1)
                        reason = "NEAR"
                        label_color = (0, 0, 255)  # 红色
                    else:
                        # 距离太远（橙色）
                        excluded_far += 1
                        cv2.line(color_vis, centroid_dark, centroid_light, (0, 165, 255), 1)
                        reason = "FAR"
                        label_color = (0, 165, 255)  # 橙色
                    
                    # 绘制排除标签
                    label_text = f"X{distance:.1f}"
                    label_pos = (x, y - 5)
                    
                    # 绘制标签（带黑色描边）
                    cv2.putText(color_vis, label_text, label_pos,
                               cv2.FONT_HERSHEY_SIMPLEX, 0.2, (0, 0, 0), 1)  # 黑色描边
                    cv2.putText(color_vis, label_text, label_pos,
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, label_color, 1)  # 彩色文字
                    
                    # 绘制边界框
                    cv2.rectangle(color_vis, (x, y), (x+w, y+h), label_color, 1)
            

        
        print(f"\n========== 判断结果 ==========")
        print(f"✓ 通过筛选: {len(results)} 个")
        print(f"✗ 被排除: {excluded_count} 个 (太近: {excluded_near}, 太远: {excluded_far})")
        print(f"\n通过筛选的蚊子候选:")
        for i, det in enumerate(results):
            print(f"  #{i+1}:")
            print(f"    像素数: 深色={det['dark_pixels']}, 浅色={det['light_pixels']}, 比例={det['ratio']:.2f}")
            print(f"    重心距离: {det['centroid_distance']:.1f}px")
            print(f"    头部边长: {det['head_side_length']:.1f}px")
            print(f"    距离范围: {det['min_distance']:.1f}px ~ {det['max_distance']:.1f}px (0.5~5倍边长)")
        
        # 显示颜色分类结果
        cv2.imshow("Color Classification (Red=Dark, Blue=Light)", color_vis)

        return results



    
    def detect(self, image_path):
        """完整检测流程"""
        # 1. 预处理
        processed_image = self.preprocess_image(image_path)
        
        # 2. 筛选候选区域
        contours = self.filter_valid_region2(processed_image)
        
        # 3. 逐个判断
        detections = self.judge_each_region2(processed_image, contours)
        
        # 4. 可视化结果
        result_image = processed_image.copy()
        for i, det in enumerate(detections):
            x, y, w, h = det['bbox']
            conf = det['confidence']
            
            # 颜色：可能性越高越绿
            color = (0, int(255 * conf), int(255 * (1 - conf)))
            
            # 绘制边界框
            cv2.rectangle(result_image, (x, y), (x+w, y+h), color, 2)
            
            # 标签
            label = f"#{i+1} {conf:.0%}"
            cv2.putText(result_image, label, (x, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # cv2.imshow("Detection Result", result_image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        
        return detections, result_image


# ========== 主程序 ==========
if __name__ == "__main__":
    print("🦟 蚊子检测器")
    print("=" * 60)
    print("检测流程：")
    print("  1. 图像预处理：去噪")
    print("  2. 筛选候选区域：颜色+面积+形状")
    print("  3. 逐个判断：身体+腿+白斑")
    print("  4. 输出结果")
    print("=" * 60)
    
    # 选择图片
    # image_path = 'mosquitos.png'
    # image_path = 'mosquito.jpg'
    # image_path = 'mosquito1.jpg'
    # image_path = 'mosquito2.jpg'
    image_path = 'mosquito3.jpg'
    
    # 创建检测器
    detector = MosquitoDetector()
    
    # 计时检测
    start = time.time()
    detections, result = detector.detect(image_path)
    elapsed = time.time() - start
    
    # 打印结果
    print(f"\n⚡ 检测时间: {elapsed*1000:.2f}ms")
    print(f"🦟 检测到 {len(detections)} 只可能的蚊子\n")
    
    # for i, det in enumerate(detections):
    #     x, y, w, h = det['bbox']
    #     print(f"  蚊子 #{i+1}:")
    #     print(f"    位置: ({x}, {y})  大小: {w}×{h}")
    #     print(f"    可能性: {det['confidence']:.1%}")
    #     print(f"    像素点数: {det['pixel_count']}")
    #     print(f"    部位: {det['part_detail']}")
    #     print(f"    检测特征: {', '.join(det['features'])}")
    
    print("\n" + "=" * 60)
    print("💡 提示：可调整 filter_valid_region2 中的参数优化检测效果")
    print("  threshold_green = 100  # 绿色通道阈值")
    print("  min_pixels = 10  # 最小像素点数")
    print("  max_pixels = 300  # 最大像素点数")
    print("=" * 60)

    cv2.waitKey(0)
    cv2.destroyAllWindows()