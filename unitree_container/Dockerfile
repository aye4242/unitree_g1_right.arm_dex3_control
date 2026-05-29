FROM ros:humble-ros-base-jammy

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    ROS_DISTRO=humble \
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG UNITREE_SDK2_REPO=https://github.com/unitreerobotics/unitree_sdk2.git
ARG UNITREE_ROS2_REPO=https://github.com/unitreerobotics/unitree_ros2.git
ARG UNITREE_SDK2_PYTHON_REPO=https://github.com/unitreerobotics/unitree_sdk2_python.git
ARG INSTALL_PINOCCHIO_PIP=1
ARG INSTALL_UNITREE_SDK2_PYTHON=1
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG http_proxy
ARG https_proxy
ARG no_proxy

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash-completion \
    build-essential \
    ca-certificates \
    cmake \
    curl \
    git \
    iproute2 \
    iputils-ping \
    less \
    libboost-all-dev \
    libccd-dev \
    libeigen3-dev \
    libgl1 \
    libnlopt-dev \
    libnlopt-cxx-dev \
    liboctomap-dev \
    libopencv-dev \
    libpcl-dev \
    libtinyxml2-dev \
    libusb-1.0-0-dev \
    libyaml-cpp-dev \
    net-tools \
    pkg-config \
    python3-colcon-common-extensions \
    python3-dev \
    python3-empy \
    python3-lark \
    python3-numpy \
    python3-opencv \
    python3-pip \
    python3-pykdl \
    python3-rosdep \
    python3-scipy \
    python3-setuptools \
    python3-venv \
    python3-yaml \
    udev \
    ros-humble-ament-cmake \
    ros-humble-cv-bridge \
    ros-humble-geometric-shapes \
    ros-humble-geometry-msgs \
    ros-humble-image-transport \
    ros-humble-kdl-parser \
    ros-humble-message-filters \
    ros-humble-ompl \
    ros-humble-pcl-conversions \
    ros-humble-realsense2-camera \
    ros-humble-resource-retriever \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-robot-state-publisher \
    ros-humble-rosidl-default-generators \
    ros-humble-rosidl-default-runtime \
    ros-humble-rosidl-generator-dds-idl \
    ros-humble-sensor-msgs \
    ros-humble-std-msgs \
    ros-humble-tf2 \
    ros-humble-tf2-geometry-msgs \
    ros-humble-tf2-ros \
    ros-humble-trajectory-msgs \
    ros-humble-urdf \
    ros-humble-urdfdom-py \
    ros-humble-vision-msgs \
    sudo \
    usbutils \
    v4l-utils \
    vim \
  && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --upgrade pip "setuptools<80" wheel \
  && python3 -m pip install --no-cache-dir "numpy<2" pupil-apriltags pydantic pybind11 scikit-build-core casadi meshcat \
  && if [[ "${INSTALL_PINOCCHIO_PIP}" == "1" ]]; then \
       python3 -m pip install --no-cache-dir pin && python3 -m pip install --no-cache-dir "numpy<2"; \
     fi

RUN git clone --depth 1 "${UNITREE_SDK2_REPO}" /opt/src/unitree_sdk2 \
  && cmake -S /opt/src/unitree_sdk2 -B /opt/src/unitree_sdk2/build \
       -DBUILD_EXAMPLES=OFF \
       -DCMAKE_BUILD_TYPE=Release \
       -DCMAKE_INSTALL_PREFIX=/usr/local \
  && cmake --build /opt/src/unitree_sdk2/build -j"$(nproc)" \
  && cmake --install /opt/src/unitree_sdk2/build \
  && ldconfig

RUN git clone --depth 1 "${UNITREE_ROS2_REPO}" /opt/unitree_ros2 \
  && source /opt/ros/humble/setup.bash \
  && cd /opt/unitree_ros2/cyclonedds_ws \
  && colcon build --packages-select unitree_api unitree_go unitree_hg

RUN if [[ "${INSTALL_UNITREE_SDK2_PYTHON}" == "1" ]]; then \
      git clone --depth 1 "${UNITREE_SDK2_PYTHON_REPO}" /opt/src/unitree_sdk2_python \
      && test -f /usr/local/include/dds/dds.h \
      && test -e /usr/local/lib/libddsc.so \
      && CYCLONEDDS_HOME=/usr/local CMAKE_PREFIX_PATH=/usr/local:${CMAKE_PREFIX_PATH:-} python3 -m pip install --no-cache-dir "cyclonedds==0.10.2" \
      && python3 -m pip install --no-cache-dir --no-deps /opt/src/unitree_sdk2_python \
      && python3 -m pip install --no-cache-dir "numpy<2"; \
    fi

COPY python_shims/ /opt/unitree_dex3_tools/
COPY right-arm-mode /usr/local/bin/right-arm-mode
COPY entrypoint.sh /usr/local/bin/unitree-container-entrypoint
RUN chmod +x /usr/local/bin/unitree-container-entrypoint /usr/local/bin/right-arm-mode

WORKDIR /workspaces
ENTRYPOINT ["/usr/local/bin/unitree-container-entrypoint"]
CMD ["bash"]
