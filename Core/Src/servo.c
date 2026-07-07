#include "servo.h"

static TIM_HandleTypeDef *servo_htim;

void Servo_Init(TIM_HandleTypeDef *htim) {
    servo_htim = htim;
    HAL_TIM_PWM_Start(servo_htim, TIM_CHANNEL_1);
}

void Servo_Set_Angle(int8_t steering_error) {
    if (!servo_htim) return;

    if (steering_error < -100) steering_error = -100;
    if (steering_error > 100) steering_error = 100;

    uint16_t pulse = 1500 + (steering_error * 5);
    __HAL_TIM_SET_COMPARE(servo_htim, TIM_CHANNEL_1, pulse);
}
