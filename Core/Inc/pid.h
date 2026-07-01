#ifndef PID_H
#define PID_H

#include <stdint.h>

typedef struct {
    float Kp;
    float Ki;
    float Kd;
    float error;
    float prev_error;
    float integral;
    float integral_limit;
    float output_limit;
} PID_Controller;

extern PID_Controller pid_left;
extern PID_Controller pid_right;

float PID_Compute(PID_Controller *pid, float setpoint, float measured);

#endif
