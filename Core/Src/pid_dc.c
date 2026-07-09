#include "pid_dc.h"
#include <stdlib.h>

void PID_DC_Init(PID_DC_Controller_t *pid, int32_t kp, int32_t ki, int32_t kd, int32_t out_min, int32_t out_max, int32_t scale) {
    pid->Kp = kp;
    pid->Ki = ki;
    pid->Kd = kd;
    pid->out_min = out_min;
    pid->out_max = out_max;
    pid->scaling_factor = scale;
    pid->setpoint = 0;
    pid->integral = 0;
    pid->prev_error = 0;
}

int32_t PID_DC_Compute(PID_DC_Controller_t *pid, int32_t measured_value) {
    int32_t error = pid->setpoint - measured_value;

    pid->integral += error;

    int32_t max_integral = (pid->out_max * pid->scaling_factor) / (pid->Ki > 0 ? pid->Ki : 1);
    int32_t min_integral = (pid->out_min * pid->scaling_factor) / (pid->Ki > 0 ? pid->Ki : 1);

    if (pid->integral > max_integral) pid->integral = max_integral;
    else if (pid->integral < min_integral) pid->integral = min_integral;

    int32_t derivative = error - pid->prev_error;

    int32_t output = (pid->Kp * error) + (pid->Ki * pid->integral) + (pid->Kd * derivative);
    output /= pid->scaling_factor;

    if (output > pid->out_max) output = pid->out_max;
    else if (output < pid->out_min) output = pid->out_min;

    pid->prev_error = error;

    return output;
}

void PID_DC_Reset(PID_DC_Controller_t *pid) {
    pid->integral = 0;
    pid->prev_error = 0;
}

int16_t Dynamics_Compensate_Speed(int16_t target_speed, int8_t steering_error) {
    int32_t abs_steering = abs(steering_error);
    if (abs_steering > 100) abs_steering = 100;

    int32_t reduction_percent = 100 - (abs_steering / 2);

    return (int16_t)((target_speed * reduction_percent) / 100);
}
