#include "motor_dc.h"

static TIM_HandleTypeDef *motor_htim;

void Motor_Init(TIM_HandleTypeDef *htim) {
    motor_htim = htim;
    HAL_TIM_PWM_Start(motor_htim, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(motor_htim, TIM_CHANNEL_2);
}

void Motor_Drive(int16_t speed) {
    if (!motor_htim) return;

    if (speed > 999) speed = 999;
    if (speed < -999) speed = -999;

    if (speed > 0) {
        __HAL_TIM_SET_COMPARE(motor_htim, TIM_CHANNEL_1, speed);
        __HAL_TIM_SET_COMPARE(motor_htim, TIM_CHANNEL_2, 0);
    } else if (speed < 0) {
        __HAL_TIM_SET_COMPARE(motor_htim, TIM_CHANNEL_1, 0);
        __HAL_TIM_SET_COMPARE(motor_htim, TIM_CHANNEL_2, (uint16_t)(-speed));
    } else {
        __HAL_TIM_SET_COMPARE(motor_htim, TIM_CHANNEL_1, 0);
        __HAL_TIM_SET_COMPARE(motor_htim, TIM_CHANNEL_2, 0);
    }
}

void Motor_Stop(void) {
    if (!motor_htim) return;
    __HAL_TIM_SET_COMPARE(motor_htim, TIM_CHANNEL_1, 0);
    __HAL_TIM_SET_COMPARE(motor_htim, TIM_CHANNEL_2, 0);
}
