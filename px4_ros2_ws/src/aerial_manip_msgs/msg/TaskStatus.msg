std_msgs/Header header

uint8 STATUS_UNKNOWN=0
uint8 STATUS_RUNNING=1
uint8 STATUS_SUCCEEDED=2
uint8 STATUS_FAILED=3
uint8 STATUS_ABORTED=4

string task_id
uint8 status
string message
float32 progress
