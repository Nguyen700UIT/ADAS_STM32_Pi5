#ifndef MOTOR_H
#define MOTOR_H

#include "stm32f1xx_hal.h"

#define PWM_MAX_ARR         999
#define MOTOR_PORT          GPIOA
#define AIN1_PIN            GPIO_PIN_2
#define AIN2_PIN            GPIO_PIN_3
#define BIN1_PIN            GPIO_PIN_4
#define BIN2_PIN            GPIO_PIN_5

void Motor_Drive(int16_t speed_left, int16_t speed_right);
void Motor_Stop(void);

#endif
