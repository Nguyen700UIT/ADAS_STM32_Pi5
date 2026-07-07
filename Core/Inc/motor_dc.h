#ifndef MOTOR_DC_H
#define MOTOR_DC_H

#include "stm32f1xx_hal.h"
#include <stdint.h>

void Motor_Init(TIM_HandleTypeDef *htim);
void Motor_Drive(int16_t speed);
void Motor_Stop(void);

#endif
