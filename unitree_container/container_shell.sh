#!/usr/bin/env bash
set -e

cat > /tmp/unitree-container-bashrc <<'RC'
if [[ -f /root/.bashrc ]]; then
  source /root/.bashrc
fi
source /opt/ros/humble/setup.bash
source /opt/unitree_ros2/cyclonedds_ws/install/setup.bash
if [[ -f /workspaces/unitree_dex3/install_container/setup.bash ]]; then
  source /workspaces/unitree_dex3/install_container/setup.bash
fi
export LD_LIBRARY_PATH="/usr/local/lib:${LD_LIBRARY_PATH:-}"
RC

cd /workspaces
exec bash --rcfile /tmp/unitree-container-bashrc -i
