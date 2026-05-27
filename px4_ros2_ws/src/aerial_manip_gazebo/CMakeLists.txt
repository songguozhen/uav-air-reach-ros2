cmake_minimum_required(VERSION 3.8)
project(aerial_manip_gazebo)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch models worlds
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/smoke_load_x500_arm_2dof.sh
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
