std_msgs/Header header

# Local PX4 NED frame state. Positive altitude is represented by negative z.
geometry_msgs/Point position_ned
geometry_msgs/Vector3 velocity_ned
geometry_msgs/Quaternion attitude
float32 yaw_rad

bool armed
string nav_state
