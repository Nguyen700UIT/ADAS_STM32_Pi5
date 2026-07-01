#include "hc_sr04.h"

extern TIM_HandleTypeDef htim1;
volatile float hc_distance_cm = 0.0f;
uint8_t trig_state = 0;

static volatile uint16_t hc_start_time = 0;
static volatile uint16_t hc_end_time = 0;
static volatile uint8_t hc_echo_state = 0;
static uint32_t trig_start_tick = 0;

void HCSR04_Trigger_Update(void)
{
    if(trig_state == 0)
    {
        HAL_GPIO_WritePin(HCSR04_PORT, TRIG_PIN, GPIO_PIN_SET);
        trig_start_tick = __HAL_TIM_GET_COUNTER(&htim1);
        trig_state = 1;
    }
    else if (trig_state == 1)
    {
        uint16_t current = __HAL_TIM_GET_COUNTER(&htim1);
        uint16_t elapsed = (current >= trig_start_tick) ?
                           (current - trig_start_tick) :
                           ((65535 - trig_start_tick) + current);
        if(elapsed >= 10)
        {
            HAL_GPIO_WritePin(HCSR04_PORT, TRIG_PIN, GPIO_PIN_RESET);
            trig_state = 2;
        }
    }
}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if(GPIO_Pin == ECHO_PIN)
    {
        if(HAL_GPIO_ReadPin(HCSR04_PORT, ECHO_PIN) == GPIO_PIN_SET)
        {
            hc_start_time = __HAL_TIM_GET_COUNTER(&htim1);
            hc_echo_state = 1;
        }
        else if (hc_echo_state == 1)
        {
            hc_end_time = __HAL_TIM_GET_COUNTER(&htim1);
            uint16_t echo_time = 0;
            if(hc_end_time >= hc_start_time)
                echo_time = hc_end_time - hc_start_time;
            else
                echo_time = (65535 - hc_start_time) + hc_end_time;
            hc_distance_cm = (float)echo_time * 0.01715f;
            hc_echo_state = 0;
        }
    }
}
