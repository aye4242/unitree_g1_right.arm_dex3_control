# AprilTag坐标原点偏移补偿方案

## 问题描述

ros2 launch运行时机器人按压位置不准确，根本原因是：
- AprilTag坐标原点每次识别会漂移
- 所有按键位置都基于原点计算offset_xyz
- 原点漂移导致整体按压位置偏移

## 解决方案核心思路

**基准补偿法（Baseline Compensation）**：
1. 做一次标定实验，拿到坐标原点基准值 P_baseline
2. 基于基准调试好所有按键的offset_xyz
3. 运行时自动检测当前原点P_current，计算偏移量并反向补偿

**补偿公式**：
```
offset_compensation = P_current - P_baseline
P_target_corrected = P_target_original - offset_compensation
```

## 实施方案

### 1. 代码修改

**文件**：`unitree_dex3/src/unitree_g1_dex3_stack-main/unitree_g1_dex3_stack/v4l2_apriltag_trigger.py`

**修改点1：参数声明（第104行后，jpeg_quality参数之后插入）**
```python
# Baseline compensation parameters
self.declare_parameter('baseline_compensation_enabled', False)
self.declare_parameter('baseline_x', 0.0)
self.declare_parameter('baseline_y', 0.0)
self.declare_parameter('baseline_z', 0.0)
```

**修改点2：参数读取（约第188行后，参数读取区域）**
```python
# Read baseline compensation parameters
self.baseline_enabled = _as_bool(self.get_parameter('baseline_compensation_enabled').value)
self.baseline = np.array([
    float(self.get_parameter('baseline_x').value),
    float(self.get_parameter('baseline_y').value),
    float(self.get_parameter('baseline_z').value),
])
if self.baseline_enabled:
    self.get_logger().info(
        f'[baseline_compensation] 已启用，基准值: ({self.baseline[0]:.4f}, '
        f'{self.baseline[1]:.4f}, {self.baseline[2]:.4f})'
    )
```

**修改点3：补偿逻辑（第607行后，final_target_pose.pose.position.z赋值之后）**
```python
# Apply baseline compensation
if self.baseline_enabled:
    current_tag = np.array([tag_avg_x, tag_avg_y, tag_avg_z])
    offset_compensation = current_tag - self.baseline
    
    final_target_pose.pose.position.x -= offset_compensation[0]
    final_target_pose.pose.position.y -= offset_compensation[1]
    final_target_pose.pose.position.z -= offset_compensation[2]
    
    self.get_logger().info(
        f'[baseline_compensation] 当前原点: ({current_tag[0]:.4f}, {current_tag[1]:.4f}, {current_tag[2]:.4f})'
    )
    self.get_logger().info(
        f'[baseline_compensation] 偏移量: ({offset_compensation[0]:.4f}, '
        f'{offset_compensation[1]:.4f}, {offset_compensation[2]:.4f})'
    )
    self.get_logger().info(
        f'[baseline_compensation] 补偿后目标: ({final_target_pose.pose.position.x:.3f}, '
        f'{final_target_pose.pose.position.y:.3f}, {final_target_pose.pose.position.z:.3f})'
    )
```

### 2. 配置文件修改

**需要修改的7个yaml文件**（位于`unitree_dex3/src/unitree_g1_dex3_stack-main/config/`）：
- apriltag_button_close.yaml
- apriltag_button_open.yaml
- apriltag_button_number6.yaml
- apriltag_button_number5.yaml
- apriltag_button_number1.yaml
- apriltag_button_up.yaml
- apriltag_button_down.yaml

**每个文件添加（baseline值待标定实验后填入）**：
```yaml
baseline_compensation_enabled: true
baseline_x: 0.0000  # 待标定
baseline_y: 0.0000  # 待标定
baseline_z: 0.0000  # 待标定
```

## 使用流程

### 阶段1：基准标定实验

**步骤**：
1. 调试好7个按键的offset_xyz（使用对应的yaml文件逐个测试按压准确性）
2. 机器人保持不动
3. 使用`apriltag_button_press.yaml`（offset_xyz全0，表示坐标原点）
4. 按10次'g'键，每次采集一个样本
5. 记录终端输出的10次tag坐标数据

**数据采集说明**：
- 每次按'g'键，v4l2_apriltag_trigger.py第609行会自动发布`/apriltag/tag_pose`
- tag_pose包含tag_avg_x、tag_avg_y、tag_avg_z（第584-595行计算的多帧平均值）
- 终端会输出这些坐标值

### 阶段2：计算基准值

**由AI完成**：
1. 接收10次tag坐标数据
2. 计算baseline：
   ```
   baseline_x = mean(tag_x_1, tag_x_2, ..., tag_x_10)
   baseline_y = mean(tag_y_1, tag_y_2, ..., tag_y_10)
   baseline_z = mean(tag_z_1, tag_z_2, ..., tag_z_10)
   ```
3. 将baseline值更新到7个yaml文件中

### 阶段3：运行时自动补偿

**每次按'g'键时自动执行**：
1. 检测当前AprilTag原点 → tag_avg_x/y/z（第584-595行已计算）
2. 与yaml中的baseline比较 → 计算offset_compensation
3. 自动应用补偿 → final_target_pose减去offset_compensation
4. 发布补偿后的target_pose → apriltag_button_press_node订阅并执行

**完全自动化**：无需手动操作，代码每次按'g'都会自动检测当前原点并计算补偿

## 工作原理验证

**关键代码位置验证**：
- ✅ 第584-607行：多帧平均已实现
- ✅ 第609行：每次按'g'自动发布/apriltag/tag_pose
- ✅ tag_avg_x/y/z：当前AprilTag原点坐标
- ✅ avg_x/y/z：target按键位置坐标

**补偿逻辑验证**：
```
假设：
- baseline = (0.5, 0.3, 0.8)
- 某次运行current_tag = (0.52, 0.28, 0.81)
- offset_xyz导致的target_original = (0.55, 0.35, 0.75)

计算：
- offset_compensation = (0.52-0.5, 0.28-0.3, 0.81-0.8) = (0.02, -0.02, 0.01)
- target_corrected = (0.55-0.02, 0.35-(-0.02), 0.75-0.01) = (0.53, 0.37, 0.74)

结果：成功补偿原点漂移
```

## 待完成任务

- [ ] 完成基准标定实验（调试7个按键 + press.yaml按10次）
- [ ] 提供10次tag坐标数据
- [ ] 计算baseline并更新yaml文件
- [ ] 修改v4l2_apriltag_trigger.py（3处修改）
- [ ] 测试验证补偿效果
