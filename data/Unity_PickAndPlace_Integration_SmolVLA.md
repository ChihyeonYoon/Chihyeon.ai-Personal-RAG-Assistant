# Unity Pick and Place Integration with SmolVLA

This repository contains the Unity Pick and Place tutorial project from the [Unity Robotics Hub](https://github.com/Unity-Technologies/Unity-Robotics-Hub/tree/main/tutorials/pick_and_place), enhanced with the integration of the **SmolVLA (Visual Language Action)** model within a ROS Docker environment.

The goal of this project is to explore how Unity's robotic simulation tools can be combined with advanced VLA models like SmolVLA for intuitive, language-driven robotic control.

<p align="center"><img src="tutorials/pick_and_place/img/0_pick_place.gif"/></p>

## Project Overview

This project builds upon the Unity Robotics Hub's Pick-and-Place tutorial, which demonstrates integrating Unity with ROS for robotic simulation. We have successfully established the communication pipeline between Unity and a ROS-based SmolVLA inference node.

### Summary of New and Modified Elements:

Based on the work in the `Unity-Robotics-Hub/tutorials/pick_and_place` directory and synchronized with the GitHub repository [Unity_PickAndPlace_Integration_SmolVLA](https://github.com/ChihyeonYoon/Unity_PickAndPlace_Integration_SmolVLA).

#### 1. New C# Scripts (Unity Project `Assets/Scripts`)
*   **`RosImagePublisher.cs`**:
    *   **Role**: Captures frames from 3 separate Unity Cameras (Top, Side, Wrist) simultaneously and publishes them to `/smolvla/camera_image1, 2, 3` ROS topics. It temporarily overrides the render target to stealthily capture images without affecting the main Game view.
    *   **Location**: `Assets/Scripts/RosImagePublisher.cs`
*   **`RosCommandPublisher.cs`**:
    *   **Role**: Extracts the current actual joint angles (6-DOF) of the Niryo robot and publishes them to `/smolvla/current_state`. It then publishes text commands entered in the Unity UI to `/smolvla/command_text`. A small coroutine delay ensures images and states arrive before the text command.
    *   **Location**: `Assets/Scripts/RosCommandPublisher.cs`
*   **`RosActionSubscriber.cs`**:
    *   **Role**: Subscribes to the `/smolvla/joint_action_cmd` topic to receive the 50-step action chunk (300 flattened floats) predicted by the AI. It uses a Coroutine to smoothly execute the entire trajectory frame-by-frame on the Niryo robot's `ArticulationBody` components, including manual scaling (x2.0) to match the robot's physical limits.
    *   **Location**: `Assets/Scripts/RosActionSubscriber.cs`
*   **`SceneResetter.cs`**:
    *   **Role**: Provides the `ResetCurrentScene()` function, which is linked to the `ResetButton` to reload the scene.
    *   **Location**: `Assets/Scripts/SceneResetter.cs`

#### 2. Modified Existing C# Scripts
*   **`TrajectoryPlanner.cs`**: Resolved the `NullReferenceException` by utilizing the fully configured robot model copied from the `DemoScene`. *Note: This legacy MoveIt script must be disabled in the Inspector when using SmolVLA for AI control to prevent service conflicts.*
*   **`PickAndPlaceRosPublisher.cs`**: A core tutorial script assigned to the `Publisher` GameObject to manage the communication of pick and place targets to ROS.

#### 3. New ROS Package and Messages (Host `ROS/src` & Docker Image)
*   **`smolvla_ros` Package**:
    *   **Role**: A custom ROS package created to house SmolVLA-specific nodes, messages, and launch files.
    *   **Location**: `ROS/src/smolvla_ros/`
    *   **Key Files**:
        *   `scripts/smolvla_node.py`: The core AI inference node running on Python 3.12. It waits for 3 camera images, text, and robot state. It utilizes the Hugging Face `AutoTokenizer` and `make_pre_post_processors` (with explicit CPU device overrides) to automatically normalize inputs/outputs. It generates a 50-step continuous trajectory using an Autoregressive loop based on simulated state updates.
        *   `launch/smolvla_launch.launch`: Launch file for the `smolvla_node`.

#### 4. Modified Docker Configuration
*   **`Dockerfile`**:
    *   **Key Changes**:
        *   Compiled Python 3.12.6 from source to satisfy strict LeRobot dependencies on ARM64 Mac hosts.
        *   Cloned the `HuggingFace/LeRobot` repository and installed `smolvla` dependencies, patching `pyproject.toml` to resolve torchvision conflicts.
        *   Uninstalled pip's cmake to force system cmake for ROS Melodic/Noetic compatibility.
    *   **Location**: `tutorials/pick_and_place/docker/Dockerfile`

#### 5. New Docker Image
*   **`unity-robotics:smolvla`**:
    *   **Role**: The updated Docker image built from the modified `Dockerfile`. Contains Python 3.12, PyTorch (CPU optimized), SmolVLA dependencies, the `smolvla_ros` package, and custom startup scripts.

#### 6. New Unity UI & Camera Elements
*   **3 Camera Setup**: `Camera1` (Top/Main), `Camera2` (Side), and `Camera3` (Wrist, attached to `tool_link`). Managed by a `ROS_Bridge_Manager` object.
*   **`CommandInputField`**: A legacy `InputField` for user text commands.
*   **`SendCommandButton`**: A legacy `Button` to publish commands, linked to `RosCommandPublisher`.
*   **`ResetButton`**: A legacy `Button` to reset the simulation, linked to `SceneResetter`.

#### 7. Miscellaneous
*   **`manual_ros_setup_guide.md`**: Provides detailed, step-by-step manual instructions for configuring the ROS Docker environment to ensure reliable networking.
*   **Git Setup**: Established an independent Git repository for the project to track all custom integration work.

---

## Getting Started

To run the integration, follow the steps outlined in the [Manual ROS Setup Guide](manual_ros_setup_guide.md) to initialize the Docker environment and connect Unity.

## Next Steps

1.  **Closed-loop Control Optimization**: Transition from the current Open-loop (generating 50 steps from a single static image) to a real-time Closed-loop system that streams images and infers actions continuously at ~10Hz.
2.  **Dataset Fine-Tuning**: Collect custom teleoperation data using the Niryo One robot in Unity to fine-tune the `smolvla_base` model. This is critical to correct the morphological mismatch (ALOHA 14-DOF vs Niryo 6-DOF) and improve reaching accuracy.
3.  **Camera Viewpoint Calibration**: Further align the Unity camera FOV and transforms with the exact SO-100/ALOHA dataset perspectives to enhance the visual-spatial understanding of the base model.
