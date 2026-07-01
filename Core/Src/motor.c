#include "motor.h"

extern TIM_HandleTypeDef htim2;

void Motor_Drive(int16_t speed_left, int16_t speed_right)
{
    if (speed_left >= 0) {
        HAL_GPIO_WritePin(MOTOR_PORT, AIN1_PIN, GPIO_PIN_SET);
        HAL_GPIO_WritePin(MOTOR_PORT, AIN2_PIN, GPIO_PIN_RESET);
    } else {
        HAL_GPIO_WritePin(MOTOR_PORT, AIN1_PIN, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(MOTOR_PORT, AIN2_PIN, GPIO_PIN_SET);
        speed_left = -speed_left;
    }

    if (speed_left > PWM_MAX_ARR) speed_left = PWM_MAX_ARR;
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, speed_left);

    if (speed_right >= 0) {
        HAL_GPIO_WritePin(MOTOR_PORT, BIN1_PIN, GPIO_PIN_SET);
        HAL_GPIO_WritePin(MOTOR_PORT, BIN2_PIN, GPIO_PIN_RESET);
    } else {
        HAL_GPIO_WritePin(MOTOR_PORT, BIN1_PIN, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(MOTOR_PORT, BIN2_PIN, GPIO_PIN_SET);
        speed_right = -speed_right;
    }

    if (speed_right > PWM_MAX_ARR) speed_right = PWM_MAX_ARR;
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_2, speed_right);
}

void Motor_Stop(void)
{
    HAL_GPIO_WritePin(MOTOR_PORT, AIN1_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MOTOR_PORT, AIN2_PIN, GPIO_PIN_RESET);
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, 0);

    HAL_GPIO_WritePin(MOTOR_PORT, BIN1_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MOTOR_PORT, BIN2_PIN, GPIO_PIN_RESET);
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_2, 0);
}
