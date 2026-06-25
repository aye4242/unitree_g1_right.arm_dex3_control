# 标定采集数据

robot_point  = tf2_echo 输出的 Translation [x, y, z]
robot_quat   = tf2_echo 输出的 Rotation (Quaternion) [qx, qy, qz, qw]
camera_point = v4l2_apriltag_trigger 日志的 tag=(x, y, z)

格式：tag=(cx,cy,cz)  Translation:[rx,ry,rz]  Rotation:[qx,qy,qz,qw]

---
1.detect_only accepted=4/4 tag=(0.060, -0.019, 0.274),Translation: [0.205, -0.048, 0.271],Rotation: in Quaternion (xyzw) [-0.636, -0.467, -0.222, 0.573]
2.detect_only accepted=4/4 tag=(0.094, -0.068, 0.330),Translation: [0.255, -0.069, 0.260],Rotation: in Quaternion (xyzw) [-0.652, -0.412, -0.299, 0.562]
3.detect_only accepted=4/4 tag=(0.116, -0.044, 0.300),Translation: [0.227, -0.088, 0.263],Rotation: in Quaternion (xyzw) [-0.651, -0.412, -0.320, 0.552]
4.detect_only accepted=4/4 tag=(0.026, -0.041, 0.299),Translation: [0.228, -0.021, 0.269],Rotation: in Quaternion (xyzw) [-0.620, -0.464, -0.253, 0.579]
5.detect_only accepted=4/4 tag=(0.062, -0.052, 0.317),Translation: [0.241, -0.049, 0.264],Rotation: in Quaternion (xyzw) [-0.665, -0.435, -0.279, 0.539]
6.detect_only accepted=4/4 tag=(0.111, -0.067, 0.332),Translation: [0.253, -0.087, 0.263],Rotation: in Quaternion (xyzw) [0.723, 0.401, 0.307, -0.470]
7.detect_only accepted=4/4 tag=(0.087, -0.057, 0.256),Translation: [0.215, -0.066, 0.292],Rotation: in Quaternion (xyzw) [-0.584, -0.446, -0.418, 0.534]
8.detect_only accepted=4/4 tag=(0.051, -0.059, 0.220),Translation: [0.202, -0.040, 0.318],Rotation: in Quaternion (xyzw) [-0.562, -0.503, -0.423, 0.502]
9.detect_only accepted=4/4 tag=(0.012, 0.017, 0.249),Translation: [0.166, -0.005, 0.265],Rotation: in Quaternion (xyzw) [0.584, 0.473, 0.531, -0.392]
10.detect_only accepted=4/4 tag=(0.004, -0.044, 0.286),Translation: [0.219, 0.000, 0.275],Rotation: in Quaternion (xyzw) [0.607, 0.457, 0.470, -0.449]
11.detect_only accepted=4/4 tag=(-0.001, -0.098, 0.311),Translation: [0.267, 0.002, 0.290],Rotation: in Quaternion (xyzw) [0.573, 0.517, 0.405, -0.491]
12.detect_only accepted=4/4 tag=(0.093, 0.002, 0.282),Translation: [0.177, -0.072, 0.254],Rotation: in Quaternion (xyzw) [0.521, 0.560, 0.443, -0.468]
13.detect_only accepted=4/4 tag=(0.071, -0.027, 0.288),Translation: [0.209, -0.054, 0.263],Rotation: in Quaternion (xyzw) [0.527, 0.532, 0.439, -0.495]
14.detect_only accepted=4/4 tag=(0.053, -0.095, 0.361),Translation: [0.278, -0.041, 0.262],Rotation: in Quaternion (xyzw) [0.605, 0.512, 0.424, -0.438]
15.detect_only accepted=4/4 tag=(0.037, -0.015, 0.350),Translation: [0.228, -0.029, 0.234],Rotation: in Quaternion (xyzw) [0.630, 0.516, 0.315, -0.488]
16.detect_only accepted=4/4 tag=(0.079, 0.013, 0.254),Translation: [0.166, -0.061, 0.266],Rotation: in Quaternion (xyzw) [0.591, 0.528, 0.393, -0.467]
17.detect_only accepted=4/4 tag=(0.138, -0.044, 0.319),Translation: [0.221, -0.103, 0.260],Rotation: in Quaternion (xyzw) [0.689, 0.408, 0.403, -0.443]
18.detect_only accepted=4/4 tag=(-0.000, -0.076, 0.283),Translation: [0.226, 0.008, 0.289],Rotation: in Quaternion (xyzw) [0.595, 0.425, 0.507, -0.456]
19.detect_only accepted=4/4 tag=(0.043, -0.107, 0.371),Translation: [0.298, -0.030, 0.253],Rotation: in Quaternion (xyzw) [-0.531, -0.473, -0.415, 0.568]
20.detect_only accepted=1/4 tag=(0.038, -0.163, 0.445),Translation: [0.351, -0.020, 0.244],Rotation: in Quaternion (xyzw) [-0.593, -0.348, -0.396, 0.609]
21.detect_only accepted=3/4 tag=(0.111, -0.133, 0.375),Translation: [0.305, -0.079, 0.263],Rotation: in Quaternion (xyzw) [-0.586, -0.383, -0.488, 0.521]
22.detect_only accepted=4/4 tag=(0.012, -0.067, 0.303),Translation: [0.232, -0.006, 0.279],Rotation: in Quaternion (xyzw) [0.573, 0.520, 0.438, -0.457]
23.detect_only accepted=4/4 tag=(-0.014, -0.032, 0.337),Translation: [0.226, 0.017, 0.246],Rotation: in Quaternion (xyzw) [0.614, 0.551, 0.439, -0.357]
24.detect_only accepted=4/4 tag=(0.054, -0.055, 0.270),Translation: [0.213, -0.040, 0.296],Rotation: in Quaternion (xyzw) [0.562, 0.615, 0.380, -0.401]
25.detect_only accepted=4/4 tag=(0.072, -0.117, 0.353),Translation: [0.300, -0.053, 0.271],Rotation: in Quaternion (xyzw) [-0.617, -0.457, -0.333, 0.547]