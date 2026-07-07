#ifndef PID_H
#define PID_H

#include <stdint.h>

typedef struct {
    float Kp;
    float Ki;
    float Kd;
    float setpoint;
    float integral;
    float prev_error;
    float out_min;
    float out_max;
    float Ts;
} PID_Controller_t;

void PID_Init(PID_Controller_t *pid, float kp, float ki, float kd, float out_min, float out_max, float ts);
float PID_Compute(PID_Controller_t *pid, float measured_value);
void PID_Reset(PID_Controller_t *pid);
int16_t Dynamics_Compensate_Speed(int16_t target_speed, int8_t steering_error);

#endif
