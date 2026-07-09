#ifndef MOTOR_DC_H
#define MOTOR_DC_H

#include "stm32f1xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

void Motor_Init(TIM_HandleTypeDef *pwm_htim, TIM_HandleTypeDef *enc_htim);
void Motor_Drive(int16_t speed, bool brake_flag);
int16_t Motor_Read_Encoder(void);

#endif
