#include "pid.h"

PID_Controller pid_left  = {2.0f, 0.5f, 0.1f, 0.0f, 0.0f, 0.0f, 500.0f, 999.0f};
PID_Controller pid_right = {2.0f, 0.5f, 0.1f, 0.0f, 0.0f, 0.0f, 500.0f, 999.0f};

float PID_Compute(PID_Controller *pid, float setpoint, float measured)
{
    pid->error = setpoint - measured;

    pid->integral += pid->error;

    if (pid->integral > pid->integral_limit) {
        pid->integral = pid->integral_limit;
    } else if (pid->integral < -pid->integral_limit) {
        pid->integral = -pid->integral_limit;
    }

    float derivative = pid->error - pid->prev_error;

    float output = (pid->Kp * pid->error) + (pid->Ki * pid->integral) + (pid->Kd * derivative);

    pid->prev_error = pid->error;

    if (output > pid->output_limit) {
        output = pid->output_limit;
    } else if (output < -pid->output_limit) {
        output = -pid->output_limit;
    }

    return output;
}
