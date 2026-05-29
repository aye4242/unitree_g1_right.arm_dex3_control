#!/usr/bin/env bash
set -e

source /opt/ros/humble/setup.bash

if [[ -f /opt/unitree_ros2/cyclonedds_ws/install/setup.bash ]]; then
  source /opt/unitree_ros2/cyclonedds_ws/install/setup.bash
fi

if [[ -f /workspaces/unitree_dex3/install_container/setup.bash ]]; then
  source /workspaces/unitree_dex3/install_container/setup.bash
fi

export RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}
export LD_LIBRARY_PATH="/usr/local/lib:${LD_LIBRARY_PATH:-}"

if [[ -n "${UNITREE_NET_IF:-}" ]]; then
  export CYCLONEDDS_URI="<CycloneDDS><Domain><General><Interfaces><NetworkInterface name=\"${UNITREE_NET_IF}\" priority=\"default\" multicast=\"default\" /></Interfaces></General></Domain></CycloneDDS>"
fi

exec "$@"
