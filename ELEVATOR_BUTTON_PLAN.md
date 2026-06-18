# 电梯按键视觉定位方案

**核心策略：一次性标定 + 纯视觉运行**

---

## 一、方案概述

### 核心思路

**标定阶段（实验室，一次性）：**
使用 AprilTag 建立相机坐标系到机器人坐标系的变换关系，保存变换矩阵。

**运行阶段（电梯内，无需 AprilTag）：**
使用 yolonas_ocr + D435i 深度信息直接检测和定位按键，应用变换矩阵转换到机器人坐标系。

### 方案优势

| 项目 | 说明 |
|------|------|
| ✅ 实用性强 | 实际使用不需要 AprilTag 辅助板 |
| ✅ 适用性广 | 适用于任何电梯环境 |
| ✅ 精度足够 | 总误差 ±7mm，满足按压需求 |
| ✅ 部署快速 | 一次标定，永久使用 |

---

## 二、技术架构

### 2.1 系统流程

```
标定阶段（一次性）：
AprilTag 检测 → 相机坐标 Pc
       +
机器人按压记录 → 机器人坐标 Pr
       ↓
  计算变换矩阵 T
       ↓
   保存到配置文件

运行阶段（实际使用）：
yolonas_ocr 检测 → 像素坐标 (u,v) + 深度 d
       ↓
   相机坐标 Pc = deproject(u,v,d)
       ↓
   应用变换 Pr = T × Pc
       ↓
   机器人按压目标位置
```

### 2.2 硬件配置

- **相机：** Intel RealSense D435i（RGB-D）
- **机器人：** 宇树 G1 右臂 + Dex3 灵巧手
- **检测模型：** yolonas_ocr（已训练）
  - `frozen_model/detection_graph.pb`（按键检测）
  - `frozen_model/ocr_graph.pb`（字符识别）

---

## 三、坐标变换原理

### 3.1 坐标系定义

**相机坐标系：**
- 原点：相机光心
- X 向右，Y 向下，Z 向前
- 单位：米

**机器人坐标系：**
- 原点：机器人基座/躯干
- 根据机器人定义（通常 X 前 Y 左 Z 上）
- 单位：米

### 3.2 变换公式

**步骤 1：像素坐标 → 相机 3D 坐标**

```python
# 使用 D435i 内参和深度
point_camera = rs.rs2_deproject_pixel_to_point(
    intrinsics,  # 相机内参（fx, fy, cx, cy）
    [pixel_x, pixel_y],
    depth  # 单位：米
)
# 返回：[Xc, Yc, Zc] 在相机坐标系中
```

**步骤 2：相机坐标系 → 机器人坐标系**

```python
# 应用标定得到的变换矩阵 T (4×4)
point_camera_homo = np.array([Xc, Yc, Zc, 1.0])
point_robot_homo = T @ point_camera_homo
point_robot = point_robot_homo[:3]
# 返回：[Xr, Yr, Zr] 在机器人坐标系中
```

---

## 四、精度分析

### 4.1 误差来源

假设按键距离相机 **0.5 米**：

| 误差源 | 典型值 | 说明 |
|--------|--------|------|
| 检测框中心 | ±2-3 像素 | yolonas_ocr 边界框定位 |
| 像素投影误差 | ±3mm | 2像素 @ 0.5m 距离 |
| D435i 深度 | ±5mm | 深度传感器精度 @ 0.5m |
| 坐标变换 | ±3mm | 标定质量决定 |

### 4.2 总误差估算

使用误差传播公式（RSS）：

```
σ_total = √(σ_pixel² + σ_depth² + σ_transform²)
        = √(3² + 5² + 3²)
        ≈ ±7mm
```

**结论：**
- 按键尺寸：40-50mm
- 误差：±7mm（< 15% 按键尺寸）
- ✅ **满足按压精度需求**

---

## 五、实施步骤

### 阶段 1：环境准备（0.5 天）

**硬件检查：**
- [ ] D435i 相机连接测试
- [ ] 相机固定稳定性检查
- [ ] 相机视野覆盖按键区域

**软件环境：**
```bash
pip install pyrealsense2 opencv-python numpy scipy
```

**模型验证：**
```bash
cd yolonas_ocr
python batch_detect.py  # 验证模型可用
```

### 阶段 2：相机内参确认（0.5 天）

D435i 出厂已标定，直接读取内参：

```python
import pyrealsense2 as rs

pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)

pipeline.start(config)
frames = pipeline.wait_for_frames()
color_frame = frames.get_color_frame()

intrinsics = color_frame.profile.as_video_stream_profile().intrinsics
print(f"fx={intrinsics.fx}, fy={intrinsics.fy}")
print(f"cx={intrinsics.cx}, cy={intrinsics.cy}")
```

### 阶段 3：坐标系标定（1-2 天）

**3.1 准备 AprilTag 板**
- 打印 AprilTag（推荐 tag36h11）
- 固定在平整板上
- 记录 Tag 尺寸

**3.2 数据采集（5-10 个位姿）**

在不同位置和角度采集数据：

```
位姿要求：
- 距离：0.3m - 1.0m
- 角度：±30° 俯仰和偏航
- 位置：左、中、右、上、下

每个位姿记录：
1. 相机检测 AprilTag → Pc_tag
2. 机器人按压 Tag 中心 → Pr_tag
3. 保存数据对
```

**3.3 计算变换矩阵**

```python
import numpy as np

def compute_transform(camera_points, robot_points):
    """
    计算从相机坐标系到机器人坐标系的变换
    """
    # 中心化
    cam_mean = np.mean(camera_points, axis=0)
    rob_mean = np.mean(robot_points, axis=0)
    cam_centered = camera_points - cam_mean
    rob_centered = robot_points - rob_mean
    
    # SVD 求解旋转矩阵
    H = cam_centered.T @ rob_centered
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T
    
    t = rob_mean - R @ cam_mean
    
    # 构造齐次变换矩阵
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    
    return T

# 使用采集的数据
T = compute_transform(camera_points_array, robot_points_array)
np.save('camera_to_robot_transform.npy', T)
```

### 阶段 4：检测节点开发（2-3 天）

**4.1 创建检测节点**

文件：`elevator_vision/scripts/button_detector_node.py`

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import numpy as np
import cv2
import pyrealsense2 as rs
from geometry_msgs.msg import PoseStamped

class ButtonDetectorNode(Node):
    def __init__(self):
        super().__init__('button_detector')
        
        # 加载变换矩阵
        self.T = np.load('camera_to_robot_transform.npy')
        
        # 加载 yolonas_ocr 模型
        self.load_detection_model()
        
        # 初始化相机
        self.init_camera()
        
        # 发布检测结果
        self.pose_pub = self.create_publisher(
            PoseStamped, 
            '/elevator/button_pose', 
            10
        )
        
        # 定时检测
        self.create_timer(0.1, self.detect_callback)
    
    def detect_callback(self):
        # 1. 获取图像和深度
        frames = self.pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        
        if not color_frame or not depth_frame:
            return
        
        # 2. 转换为 numpy 数组
        color_image = np.asanyarray(color_frame.get_data())
        depth_image = np.asanyarray(depth_frame.get_data())
        
        # 3. yolonas_ocr 检测
        detections = self.detect_buttons(color_image)
        
        # 4. 对每个检测结果
        for det in detections:
            cx, cy = det['center']
            text = det['text']
            
            # 5. 获取深度
            depth = depth_frame.get_distance(int(cx), int(cy))
            
            if depth == 0 or depth > 3.0:
                continue
            
            # 6. 像素 → 相机 3D
            point_cam = rs.rs2_deproject_pixel_to_point(
                self.intrinsics, [cx, cy], depth
            )
            
            # 7. 相机 → 机器人坐标系
            point_cam_homo = np.array([*point_cam, 1.0])
            point_robot = self.T @ point_cam_homo
            
            # 8. 发布目标位置
            pose = PoseStamped()
            pose.header.frame_id = 'torso_link'
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = point_robot[0]
            pose.pose.position.y = point_robot[1]
            pose.pose.position.z = point_robot[2]
            
            self.pose_pub.publish(pose)
            self.get_logger().info(
                f"检测到按键 '{text}' 位置: "
                f"({point_robot[0]:.3f}, {point_robot[1]:.3f}, {point_robot[2]:.3f})"
            )
```

**4.2 集成到现有系统**

修改 `apriltag_button_press_node.py`，订阅 `/elevator/button_pose` 替代原来的 AprilTag 话题。

### 阶段 5：测试和优化（1-2 天）

**测试内容：**
1. 静态精度测试（固定距离和角度）
2. 动态鲁棒性测试（不同光照、角度）
3. 实际按压成功率统计

**优化方向：**
- 深度滤波（去除噪声）
- 多帧平均（提高稳定性）
- 置信度阈值调整

---

## 六、关键参数配置

```yaml
# 相机配置
camera:
  width: 1280
  height: 720
  fps: 30
  
# 检测参数
detection:
  confidence_threshold: 0.5  # 检测置信度阈值
  max_distance: 1.5  # 最大检测距离（米）
  min_distance: 0.3  # 最小检测距离（米）

# 深度处理
depth:
  filter_enable: true
  filter_type: 'bilateral'  # 双边滤波
  filter_d: 9
  filter_sigma: 75

# 坐标变换
transform:
  matrix_file: 'camera_to_robot_transform.npy'
```

---

## 七、故障排查

### 问题 1：深度值为 0 或不准确

**可能原因：**
- 反光表面
- 距离超出范围
- 光照太强/太弱

**解决方案：**
```python
# 使用邻域深度中值
roi = depth_image[cy-5:cy+5, cx-5:cx+5]
depth = np.median(roi[roi > 0])
```

### 问题 2：检测不到按键

**可能原因：**
- 模型不适配当前环境
- 光照条件差异大

**解决方案：**
- 调低置信度阈值
- 图像预处理（对比度增强）
- 重新训练或微调模型

### 问题 3：按压位置偏移

**可能原因：**
- 标定精度不够
- 相机移动或松动

**解决方案：**
- 重新标定（多采集几个位姿）
- 检查相机固定是否牢固
- 使用 AprilTag 实时校准（混合模式）

---

## 八、项目时间表

| 阶段 | 任务 | 预计时间 |
|------|------|---------|
| 1 | 环境准备 | 0.5 天 |
| 2 | 相机内参确认 | 0.5 天 |
| 3 | 坐标系标定 | 1-2 天 |
| 4 | 检测节点开发 | 2-3 天 |
| 5 | 测试和优化 | 1-2 天 |
| **总计** | | **5-8 天** |

---

## 九、总结

本方案通过 **一次性标定 + 纯视觉运行** 实现了无需 AprilTag 辅助板的电梯按键检测和按压。

**核心优势：**
1. ✅ **实用性强：** 适用于任何电梯，无需辅助设备
2. ✅ **精度足够：** ±7mm 误差满足按压需求
3. ✅ **部署简单：** 一次标定，永久使用
4. ✅ **成本低：** 复用现有硬件和模型

**预期效果：**
- 检测成功率：> 95%
- 按压成功率：> 90%
- 单次检测时间：< 1s

---

*文档版本：v2.0*  
*创建日期：2026-06-16*  
*方案：一次性标定 + 纯视觉运行*
