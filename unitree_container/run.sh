#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-unitree-dex3:humble-tf}"
CONTAINER_NAME="${CONTAINER_NAME:-unitree-dex3-dev}"
UNITREE_NET_IF="${UNITREE_NET_IF:-enP8p1s0}"
UNITREE_DEX3_DIR="${UNITREE_DEX3_DIR:-/home/unitree/Desktop/unitree_dex3}"
UNITREE_DEX3_CPP_DIR="${UNITREE_DEX3_CPP_DIR:-/home/unitree/Desktop/unitree_dex3_cpp}"
YOLONAS_OCR_DIR="${YOLONAS_OCR_DIR:-/home/unitree/Desktop/yolonas_ocr}"
XR_TELEOPERATE_DIR="${XR_TELEOPERATE_DIR:-/home/unitree/Desktop/xr_teleoperate}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_SHELL_SCRIPT="${SCRIPT_DIR}/container_shell.sh"
CONTAINER_COMMAND_SCRIPT="${SCRIPT_DIR}/container_command.sh"
CONTAINER_TOOLS_DIR="${SCRIPT_DIR}/python_shims"
RIGHT_ARM_MODE_SCRIPT="${SCRIPT_DIR}/right-arm-mode"

EXTRA_MOUNTS=()
if [[ -d "${XR_TELEOPERATE_DIR}" ]]; then
  EXTRA_MOUNTS+=("-v" "${XR_TELEOPERATE_DIR}:/workspaces/xr_teleoperate")
fi
if [[ -d /home/unitree/unitree_sdk2_python ]]; then
  EXTRA_MOUNTS+=("-v" "/home/unitree/unitree_sdk2_python:/workspaces/unitree_sdk2_python")
fi

DISPLAY_ARGS=()
if [[ -n "${DISPLAY:-}" ]]; then
  DISPLAY_ARGS+=("-e" "DISPLAY=${DISPLAY}" "-v" "/tmp/.X11-unix:/tmp/.X11-unix:rw")
fi

PYTHONPATH_VALUE="/opt/unitree_dex3_tools:/workspaces/xr_teleoperate/teleop:/workspaces/unitree_dex3:/workspaces/unitree_dex3_cpp/build:/workspaces/unitree_sdk2_python:${PYTHONPATH:-}"
CYCLONEDDS_URI_VALUE="<CycloneDDS><Domain><General><Interfaces><NetworkInterface name=\"${UNITREE_NET_IF}\" priority=\"default\" multicast=\"default\" /></Interfaces></General></Domain></CycloneDDS>"

if docker ps --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
  if [[ "$#" -eq 0 ]]; then
    docker exec -it \
      -e "UNITREE_NET_IF=${UNITREE_NET_IF}" \
      -e "RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" \
      -e "CYCLONEDDS_URI=${CYCLONEDDS_URI_VALUE}" \
      -e "PYTHONPATH=${PYTHONPATH_VALUE}" \
      "${CONTAINER_NAME}" \
      bash -lc 'printf "%s\n" "if [[ -f /root/.bashrc ]]; then source /root/.bashrc; fi" "source /opt/ros/humble/setup.bash" "source /opt/unitree_ros2/cyclonedds_ws/install/setup.bash" "if [[ -f /workspaces/unitree_dex3/install_container/setup.bash ]]; then source /workspaces/unitree_dex3/install_container/setup.bash; fi" "export LD_LIBRARY_PATH=\"/usr/local/lib:\${LD_LIBRARY_PATH:-}\"" > /tmp/unitree-container-bashrc; cd /workspaces; exec bash --rcfile /tmp/unitree-container-bashrc -i'
  else
    docker exec -it \
      -e "UNITREE_NET_IF=${UNITREE_NET_IF}" \
      -e "RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" \
      -e "CYCLONEDDS_URI=${CYCLONEDDS_URI_VALUE}" \
      -e "PYTHONPATH=${PYTHONPATH_VALUE}" \
      "${CONTAINER_NAME}" \
      bash -lc 'source /opt/ros/humble/setup.bash; source /opt/unitree_ros2/cyclonedds_ws/install/setup.bash; if [[ -f /workspaces/unitree_dex3/install_container/setup.bash ]]; then source /workspaces/unitree_dex3/install_container/setup.bash; fi; export LD_LIBRARY_PATH="/usr/local/lib:${LD_LIBRARY_PATH:-}"; exec "$@"' bash "$@"
  fi
  exit 0
fi

DOCKER_RUN_ARGS=(
  --rm -it
  --name "${CONTAINER_NAME}"
  --network host
  --privileged
  -e "UNITREE_NET_IF=${UNITREE_NET_IF}"
  -e "RMW_IMPLEMENTATION=rmw_cyclonedds_cpp"
  -e "CYCLONEDDS_URI=${CYCLONEDDS_URI_VALUE}"
  -e "LD_LIBRARY_PATH=/usr/local/lib:${LD_LIBRARY_PATH:-}"
  -e "PYTHONPATH=${PYTHONPATH_VALUE}"
  "${DISPLAY_ARGS[@]}"
  -v /dev:/dev
  -v "${YOLONAS_OCR_DIR}:/workspaces/yolonas_ocr"
  -v "${UNITREE_DEX3_DIR}:/workspaces/unitree_dex3"
  -v "${UNITREE_DEX3_CPP_DIR}:/workspaces/unitree_dex3_cpp"
  -v "${CONTAINER_TOOLS_DIR}:/opt/unitree_dex3_tools:ro"
  -v "${RIGHT_ARM_MODE_SCRIPT}:/usr/local/bin/right-arm-mode:ro"
  -v "${CONTAINER_SHELL_SCRIPT}:/usr/local/bin/unitree-container-shell:ro"
  -v "${CONTAINER_COMMAND_SCRIPT}:/usr/local/bin/unitree-container-command:ro"
  "${EXTRA_MOUNTS[@]}"
  -w /workspaces
  "${IMAGE_NAME}"
)

if [[ "$#" -eq 0 ]]; then
  DOCKER_RUN_DETACHED_ARGS=()
  for arg in "${DOCKER_RUN_ARGS[@]}"; do
    if [[ "${arg}" != "-it" ]]; then
      DOCKER_RUN_DETACHED_ARGS+=("${arg}")
    fi
  done
  docker run -d "${DOCKER_RUN_DETACHED_ARGS[@]}" sleep infinity >/dev/null
  exec bash "${SCRIPT_DIR}/run.sh"
else
  docker run "${DOCKER_RUN_ARGS[@]}" bash /usr/local/bin/unitree-container-command "$@"
fi
