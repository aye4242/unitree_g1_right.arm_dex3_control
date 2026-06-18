# 电梯按钮视觉检测 - 完整测试指南

**测试日期：** 2026-06-17  
**方案版本：** v2.0（一次性标定 + 纯视觉运行）

---

## 📋 测试前准备

### 1. 本地代码优化清单

**已完成优化：**
- ✅ 深度中值滤波（5×5邻域，替代单点查询）
- ✅ 代码语法验证通过

**优化位置：**
- `unitree_dex3/elevator_vision/scripts/button_detector_node.py` (line 167-191)

---

## 📦 需要上传到机器人的文件

### 必须上传的文件：

```bash
# 主检测节点（已优化深度滤波）
unitree_dex3/elevator_vision/scripts/button_detector_node.py
```

### 上传方法（从本地到机器人）：

```bash
# 使用 scp 上传文件
scp unitree_dex3/elevator_vision/scripts/button_detector_node.py \
    unitree@192.168.100.30:/home/unitree/Desktop/unitree_dex3/elevator_vision/scripts/

# 密码: 123
```

---

## 🧪 测试流程

### 阶段 1：纯视觉检测测试（推荐先做）

**目的：** 验证按钮检测和坐标变换功能，不控制机器人

#### 步骤 1.1：SSH 连接到机器人

```bash
ssh unitree@192.168.100.30
# 密码: 123
```

#### 步骤 1.2：进入 Docker 容器

```bash
cd /home/unitree/Desktop/unitree_container
./run.sh
```

#### 步骤 1.3：启动纯视觉测试

```bash
cd /workspaces/unitree_dex3/elevator_vision/scripts

python3 button_detector_node.py --ros-args \
  -p input_backend:=v4l2 \
  -p frozen_model_dir:=/workspaces/yolonas_ocr/frozen_model \
  -p target_floor:=0 \
  -p det_threshold:=0.3 \
  -p save_debug_images:=true \
  -p debug_image_dir:=/tmp/button_debug
```

**参数说明：**
- `target_floor:=0` - 自动选择置信度最高的楼层
- `det_threshold:=0.3` - 降低阈值以增加检测率

#### 步骤 1.4：观察输出

**正常输出示例：**
```
[INFO] floor='3' conf=0.87 depth=0.523m  torso(0.412,-0.156,0.234)
```

**检查点：**
- ✅ 检测到楼层按钮
- ✅ 置信度 > 0.3
- ✅ 深度值合理（0.3-1.5米）
- ✅ 机器人坐标在工作空间内

#### 步骤 1.5：查看调试图像

```bash
# 从机器人下载到本地查看
scp unitree@192.168.100.30:/tmp/button_debug/latest_button_detector.jpg .
```

---

### 阶段 2：坐标精度验证

**目的：** 验证坐标变换精度，检查多次检测的稳定性

#### 步骤 2.1：监听发布的位置

在**新的终端**中：

```bash
ssh unitree@192.168.100.30
cd /home/unitree/Desktop/unitree_container
./run.sh ros2 topic echo /elevator/target_pose
```

#### 步骤 2.2：记录多次检测结果

保持相机和按钮相对静止，记录连续 5-10 次检测的坐标。

**验收标准：**
- x/y/z 标准差 < 10mm（0.010m）

---

### 阶段 3：不同场景测试

**目的：** 验证鲁棒性

#### 测试场景：

| 场景 | 测试内容 | 预期结果 |
|------|---------|---------|
| **不同距离** | 0.3m, 0.5m, 0.8m, 1.0m | 全部检测成功 |
| **不同角度** | 正面、±15°、±30° | 检测率 > 85% |
| **不同光照** | 正常、偏暗、偏亮 | 检测率 > 80% |

---

## 📊 测试验收标准

| 指标 | 目标值 |
|------|--------|
| 检测成功率 | > 95% |
| 坐标稳定性（标准差）| < 10mm |
| 单次检测时间 | < 1s |

---

## 🔧 常见问题排查

### 问题 1：检测不到按钮

**解决方案：**
```bash
# 1. 检查模型文件
ls -lh /workspaces/yolonas_ocr/frozen_model/*.pb

# 2. 降低阈值
-p det_threshold:=0.2
```

### 问题 2：深度值为 0

**解决方案：**
```bash
# 检查深度话题
ros2 topic hz /camera/realsense2_camera/depth/image_rect_raw
```

### 问题 3：坐标偏差大（> 20mm）

**解决方案：**
1. 重新标定变换矩阵
2. 检查相机固定是否牢固

### 问题 4：V4L2 设备占用

**解决方案：**
```bash
# 检查占用进程
fuser -v /dev/video4

# 杀掉占用进程
kill <PID>
```

---

**文档版本：** v1.0  
**创建日期：** 2026-06-17
