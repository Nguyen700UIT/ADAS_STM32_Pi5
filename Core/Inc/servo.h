#ifndef SERVO_H
#define SERVO_H

#include "stm32f1xx_hal.h"
#include <stdint.h>

void Servo_Init(TIM_HandleTypeDef *htim);
void Servo_Set_Angle(int8_t steering_error);

#endif
