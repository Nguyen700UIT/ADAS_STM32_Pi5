#ifndef PID_DC_H
#define PID_DC_H

#include <stdint.h>

typedef struct {
    int32_t Kp;
    int32_t Ki;
    int32_t Kd;
    int32_t setpoint;
    int32_t integral;
    int32_t prev_error;
    int32_t out_min;
    int32_t out_max;
    int32_t scaling_factor;
} PID_DC_Controller_t;

void PID_DC_Init(PID_DC_Controller_t *pid, int32_t kp, int32_t ki, int32_t kd, int32_t out_min, int32_t out_max, int32_t scale);
int32_t PID_DC_Compute(PID_DC_Controller_t *pid, int32_t measured_value);
void PID_DC_Reset(PID_DC_Controller_t *pid);
int16_t Dynamics_Compensate_Speed(int16_t target_speed, int8_t steering_error);

#endif
