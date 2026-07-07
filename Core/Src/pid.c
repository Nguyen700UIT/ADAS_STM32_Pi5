#include "pid.h"
#include <stdlib.h>

void PID_Init(PID_Controller_t *pid, float kp, float ki, float kd, float out_min, float out_max, float ts) {
    pid->Kp = kp;
    pid->Ki = ki;
    pid->Kd = kd;
    pid->out_min = out_min;
    pid->out_max = out_max;
    pid->Ts = ts;
    pid->setpoint = 0.0f;
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
}

float PID_Compute(PID_Controller_t *pid, float measured_value) {
    float error = pid->setpoint - measured_value;

    pid->integral += error * pid->Ts;

    float max_integral = pid->out_max / (pid->Ki > 0.0001f ? pid->Ki : 1.0f);
    float min_integral = pid->out_min / (pid->Ki > 0.0001f ? pid->Ki : 1.0f);

    if (pid->integral > max_integral) pid->integral = max_integral;
    else if (pid->integral < min_integral) pid->integral = min_integral;

    float derivative = (error - pid->prev_error) / pid->Ts;

    float output = (pid->Kp * error) + (pid->Ki * pid->integral) + (pid->Kd * derivative);

    if (output > pid->out_max) output = pid->out_max;
    else if (output < pid->out_min) output = pid->out_min;

    pid->prev_error = error;

    return output;
}

void PID_Reset(PID_Controller_t *pid) {
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
}

int16_t Dynamics_Compensate_Speed(int16_t target_speed, int8_t steering_error) {
    float abs_steering = (float)abs(steering_error);
    if (abs_steering > 100.0f) abs_steering = 100.0f;

    float reduction_factor = 1.0f - (abs_steering / 100.0f) * 0.5f;

    return (int16_t)(target_speed * reduction_factor);
}
