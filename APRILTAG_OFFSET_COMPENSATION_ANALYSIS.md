# AprilTag 坐标原点漂移补偿完整实施方案

## 一、问题描述

按压位置基于 `AprilTag坐标原点 + offset_xyz` 计算，但AprilTag坐标原点每次识别会漂移，导致所有按键按压位置跟着偏移。

**示例**：AprilTag原点y轴漂移+0.02m → 所有按键y轴都偏移+0.02m

---

## 二、解决方案

### 核心思路

1. **基准标定**：记录AprilTag坐标原点基准位置 `P_baseline`
2. **调试offset**：基于该基准调试所有按键 `offset_xyz`
3. **运行时补偿**：
   ```
   当前检测原点: P_current
   偏移量: offset_compensation = P_current - P_baseline
   补偿后位置: target = P_current + offset_xyz - offset_compensation
   ```

### 当前系统架构

**执行命令**：
```bash
ros2 launch unitree_g1_dex3_stack apriltag_button_press.launch.py \
    v4l2_config_file:=/workspaces/unitree_dex3/src/unitree_g1_dex3_stack-main/config/apriltag_button_number5.yaml
```

**数据流**：
```
v4l2_apriltag_trigger.py
  ├─ 检测AprilTag
  ├─ 多帧平均（已实现，第472-495行）
  ├─ 发布 /apriltag/tag_pose (坐标原点)
  └─ 发布 /apriltag/target_pose (原点 + offset_xyz)
       ↓
apriltag_button_press_node.py
  └─ 订阅并执行按压
```

**关键发现** ✅：
- AprilTag坐标原点已通过 `/apriltag/tag_pose` topic发布
- 多帧平均已实现，噪声已抑制
- 可直接在现有代码中添加补偿逻辑

---

## 三、实施步骤

### 步骤1：创建基准标定工具

**文件**：`scripts/apriltag_baseline_calibrator.py`

```python
#!/usr/bin/python3
"""AprilTag基准位置标定工具 - 自动采集多次样本取平均"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import yaml
import sys

class BaselineCalibrator(Node):
    def __init__(self, output_file, samples=10):
        super().__init__('baseline_calibrator')
        self.output_file = output_file
        self.samples = samples
        self.data = []
        self.create_subscription(PoseStamped, '/apriltag/tag_pose', self.cb, 10)
        self.get_logger().info(f'采集 {samples} 个AprilTag原点位置样本...')
    
    def cb(self, msg):
        self.data.append([
            msg.pose.position.x,
            msg.pose.position.y,
            msg.pose.position.z
        ])
        self.get_logger().info(f'已采集: {len(self.data)}/{self.samples}')
        if len(self.data) >= self.samples:
            self.save()
            rclpy.shutdown()
    
    def save(self):
        import numpy as np
        data = np.array(self.data)
        baseline = {
            'x': float(np.mean(data[:, 0])),
            'y': float(np.mean(data[:, 1])),
            'z': float(np.mean(data[:, 2])),
            'std_x': float(np.std(data[:, 0])),
            'std_y': float(np.std(data[:, 1])),
            'std_z': float(np.std(data[:, 2])),
        }
        with open(self.output_file, 'w') as f:
            yaml.dump({'apriltag_baseline': baseline}, f)
        print(f'\n✅ 基准位置已保存: {self.output_file}')
        print(f'   位置: ({baseline["x"]:.4f}, {baseline["y"]:.4f}, {baseline["z"]:.4f})')
        print(f'   标准差: ({baseline["std_x"]:.4f}, {baseline["std_y"]:.4f}, {baseline["std_z"]:.4f})')

def main():
    if len(sys.argv) < 2:
        print('用法: apriltag_baseline_calibrator.py <输出yaml文件>')
        sys.exit(1)
    rclpy.init()
    node = BaselineCalibrator(sys.argv[1])
    rclpy.spin(node)

if __name__ == '__main__':
    main()
```

**说明**：
- 订阅 `/apriltag/tag_pose` 获取AprilTag坐标原点
- 自动采集10次样本取平均值
- 保存到YAML文件供后续使用

---

### 步骤2：修改 `v4l2_apriltag_trigger.py`

#### 修改点1：添加参数声明（约第93行后）

在现有参数声明后添加：

```python
# 基准补偿参数
self.declare_parameter('baseline_compensation_enabled', False)
self.declare_parameter('baseline_x', 0.0)
self.declare_parameter('baseline_y', 0.0)
self.declare_parameter('baseline_z', 0.0)

self.baseline_enabled = _as_bool(
    self.get_parameter('baseline_compensation_enabled').value)
self.baseline = np.array([
    float(self.get_parameter('baseline_x').value),
    float(self.get_parameter('baseline_y').value),
    float(self.get_parameter('baseline_z').value),
])
```

#### 修改点2：添加补偿逻辑（第495行后）

在 `_on_trigger` 方法中，`final_target_pose` 位置赋值后添加：

```python
# 原有代码（保持不变）
final_target_pose.pose.position.x = avg_x
final_target_pose.pose.position.y = avg_y
final_target_pose.pose.position.z = avg_z

# 【新增】基准补偿逻辑
if self.baseline_enabled:
    current_tag = np.array([tag_avg_x, tag_avg_y, tag_avg_z])
    offset_compensation = current_tag - self.baseline
    final_target_pose.pose.position.x -= offset_compensation[0]
    final_target_pose.pose.position.y -= offset_compensation[1]
    final_target_pose.pose.position.z -= offset_compensation[2]
    self.get_logger().info(
        f'[baseline_compensation] 偏移: ({offset_compensation[0]:.4f}, '
        f'{offset_compensation[1]:.4f}, {offset_compensation[2]:.4f}) '
        f'补偿后: ({final_target_pose.pose.position.x:.3f}, '
        f'{final_target_pose.pose.position.y:.3f}, '
        f'{final_target_pose.pose.position.z:.3f})')
```

---

### 步骤3：更新配置文件

在现有YAML配置中添加基准补偿参数（例如 `apriltag_button_number5.yaml`）：

```yaml
v4l2_apriltag_trigger:
  ros__parameters:
    # ... 现有参数保持不变 ...
    
    # 基准补偿（标定后启用）
    baseline_compensation_enabled: false  # 标定完成后改为true
    baseline_x: 0.0000  # 从标定工具生成的baseline.yaml复制
    baseline_y: 0.0000  # 从标定工具生成的baseline.yaml复制
    baseline_z: 0.0000  # 从标定工具生成的baseline.yaml复制
```

---

## 四、使用流程

### 阶段1：基准标定（一次性，5分钟）

```bash
# 1. 启动系统（补偿功能关闭）
ros2 launch unitree_g1_dex3_stack apriltag_button_press.launch.py \
    v4l2_config_file:=/workspaces/unitree_dex3/src/unitree_g1_dex3_stack-main/config/apriltag_button_number5.yaml

# 2. 新终端运行标定工具
ros2 run unitree_g1_dex3_stack apriltag_baseline_calibrator.py \
    /workspaces/unitree_dex3/src/unitree_g1_dex3_stack-main/config/baseline.yaml

# 3. 按 'g' 键10次，每次触发一次AprilTag检测
#    工具会自动采集10个样本后保存基准位置
```

**采集方式说明** ⚠️：
- 需要**按10次'g'键**，每次采集一个样本
- 不是一次触发自动采集10次
- 每次按'g'内部已采集4帧取平均（sample_count=4）
- 最终baseline = 10次 × 4帧 = **40帧平均**，精度高

**输出示例**：
```
已采集: 1/10
已采集: 2/10
...
已采集: 10/10
✅ 基准位置已保存: .../baseline.yaml
   位置: (0.4523, 0.0234, 0.8456)
   标准差: (0.0021, 0.0018, 0.0025)
```

### 阶段2：调试按键offset

基于标定的基准位置，调试所有按键的 `offset_xyz` 参数，确保每个按键都能准确按压。

### 阶段3：启用补偿运行

```bash
# 1. 将 baseline.yaml 中的 x/y/z 值复制到配置文件
# 2. 设置 baseline_compensation_enabled: true
# 3. 启动系统
ros2 launch unitree_g1_dex3_stack apriltag_button_press.launch.py \
    v4l2_config_file:=/workspaces/unitree_dex3/src/unitree_g1_dex3_stack-main/config/apriltag_button_number5.yaml
```

**运行日志示例**：
```
[baseline_compensation] 偏移: (0.0012, 0.0234, -0.0189)
补偿后: (0.451, 0.000, 0.865)
```

---

## 五、代码修改清单

| 文件 | 位置 | 操作 | 代码量 |
|------|------|------|--------|
| `scripts/apriltag_baseline_calibrator.py` | 新建 | 创建标定工具 | 45行 |
| `scripts/v4l2_apriltag_trigger.py` | 约93行后 | 添加参数声明 | 10行 |
| `scripts/v4l2_apriltag_trigger.py` | 495行后 | 添加补偿逻辑 | 11行 |
| `config/apriltag_button_number5.yaml` | 末尾 | 添加补偿参数 | 4行 |

**总计**：约70行代码（含注释）

---

## 六、工作原理

### 补偿逻辑验证

**核心公式**：
```python
offset_cover = P_current - P_baseline  # 计算偏移量
target位置 -= offset_cover            # 反向补偿
```

### 数值示例

| 项目 | 值 | 说明 |
|------|------|------|
| 基准位置 | (0.450, 0.020, 0.850) | 第一次标定记录 |
| 当前检测 | (0.450, 0.040, 0.830) | y轴+0.02, z轴-0.02 |
| 偏移补偿 | (0.000, 0.020, -0.020) | current - baseline |
| 原始target | (0.450, -0.130, 0.780) | 原点 + offset_xyz |
| 补偿后target | (0.450, -0.150, 0.800) | 原始 - 偏移补偿 |

**结果**：AprilTag原点漂移被完全抵消，按压位置恢复准确 ✅

### 正确性验证

#### 情况1：无漂移
```
P_baseline = (0.450, 0.020, 0.850)
P_current  = (0.450, 0.020, 0.850)  # 无变化
offset_cover = (0.000, 0.000, 0.000)
target位置 -= (0, 0, 0)  → target不变 ✅
```

#### 情况2：有漂移（y轴+0.02）
```
P_baseline = (0.450, 0.020, 0.850)
P_current  = (0.450, 0.040, 0.850)  # y+0.02
offset_cover = (0.000, 0.020, 0.000)
target.y -= 0.020  → 补偿了AprilTag的+0.02偏移 ✅
```

#### 情况3：多轴漂移（主人的例子）
```
AprilTag偏移: x:-0.02, y:+0.03, z:-0.02
offset_cover = (-0.02, +0.03, -0.02)
target -= offset_cover = target + (0.02, -0.03, 0.02)
结果：x补偿+0.02, y补偿-0.03, z补偿+0.02 ✅
```

---

## 七、方案优势

1. ✅ **最小侵入** - 仅21行代码修改现有文件
2. ✅ **配置化** - 基准值存储在YAML，易于管理
3. ✅ **自动化标定** - 独立工具，简单易用
4. ✅ **实时反馈** - 每次补偿打印日志，便于调试
5. ✅ **利用多帧平均** - 基于现有噪声抑制机制

---

*创建时间：2026-06-17*  
*方案：AprilTag坐标原点漂移基准补偿*
