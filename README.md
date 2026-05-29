# Unitree G1 Right Arm + Dex-3 Control Deployment Bundle

This repository contains the source files needed to deploy the Unitree G1 right-arm + Dex-3 control stack on a new machine.

## Directory layout

```text
unitree_container/                           # Docker image, container launcher, DDS/runtime wrappers
unitree_dex3/src/fcl/                        # FCL source dependency built by colcon
unitree_dex3/src/trac_ik/                    # TRAC-IK source dependency built by colcon
unitree_dex3/src/unitree_g1_dex3_stack-main/ # Main ROS 2 package
unitree_dex3_cpp/                            # Dex-3 Python/C++ binding and control scripts
```

## New machine setup

Copy or clone this repository, then either keep this layout and adapt paths, or copy the three runtime directories to `/home/unitree/Desktop/`:

```bash
cp -a unitree_container /home/unitree/Desktop/
cp -a unitree_dex3 /home/unitree/Desktop/
cp -a unitree_dex3_cpp /home/unitree/Desktop/
```

Then follow:

```text
unitree_dex3/src/unitree_g1_dex3_stack-main/README.md
```

Start at section `1.1 新机器从零部署`.

## Notes

Generated build outputs are intentionally not included:

```text
build/
install/
log/
build_container/
install_container/
log_container/
```

They must be regenerated on the target machine.
