# 机器人部署文件上传清单

**优化内容：** 深度中值滤波  
**上传日期：** 2026-06-17

---

## ✅ 必须上传的文件

```bash
# 核心检测节点（已优化深度滤波）
unitree_dex3/elevator_vision/scripts/button_detector_node.py
```

### 上传命令

```bash
scp unitree_dex3/elevator_vision/scripts/button_detector_node.py \
    unitree@192.168.100.30:/home/unitree/Desktop/unitree_dex3/elevator_vision/scripts/
# 密码: 123
```

---

## 📋 上传后验证

```bash
# 1. SSH 连接
ssh unitree@192.168.100.30

# 2. 检查文件
ls -lh /home/unitree/Desktop/unitree_dex3/elevator_vision/scripts/button_detector_node.py

# 3. 快速测试
cd /home/unitree/Desktop/unitree_container
./run.sh bash -c "cd /workspaces/unitree_dex3/elevator_vision/scripts && \
python3 button_detector_node.py --ros-args \
  -p input_backend:=v4l2 \
  -p frozen_model_dir:=/workspaces/yolonas_ocr/frozen_model \
  -p target_floor:=0 \
  -p det_threshold:=0.3"
```

---

## 📝 完整测试流程

参考 `ELEVATOR_BUTTON_TEST_GUIDE.md` 进行完整测试。

**上传记录：**
- [ ] 文件已上传
- [ ] 验证通过
- [ ] 测试通过
