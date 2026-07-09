#ifndef HC_SR04_H
#define HC_SR04_H

#include "stm32f1xx_hal.h"
#include <stdint.h>

typedef struct {
    volatile uint32_t capture_val1;
    volatile uint32_t capture_val2;
    volatile uint16_t distance_cm;
    volatile uint8_t  capture_flag;
} HC_SR04_Sensor_t;

void HC_SR04_Init(TIM_HandleTypeDef *htim);
void HC_SR04_Trigger_Start(TIM_HandleTypeDef *trigger_htim);
void HC_SR04_Trigger_IT(TIM_HandleTypeDef *trigger_htim);
void HC_SR04_IC_Callback(TIM_HandleTypeDef *htim);
uint16_t HC_SR04_Get_Distance_Left(void);
uint16_t HC_SR04_Get_Distance_Right(void);
void HC_SR04_Watchdog_Check(void);

#endif
