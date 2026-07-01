#ifndef HC_SR04_H
#define HC_SR04_H

#include "stm32f1xx_hal.h"

#define HCSR04_PORT         GPIOB
#define TRIG_PIN            GPIO_PIN_8
#define ECHO_PIN            GPIO_PIN_9

extern volatile float hc_distance_cm;
extern uint8_t trig_state;
void HCSR04_Trigger_Update(void);

#endif
