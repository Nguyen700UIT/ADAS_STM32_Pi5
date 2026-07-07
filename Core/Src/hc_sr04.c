#include "hc_sr04.h"

static TIM_HandleTypeDef *hc_htim;
static HC_SR04_Sensor_t sensor1 = {0};
static HC_SR04_Sensor_t sensor2 = {0};

void HC_SR04_Init(TIM_HandleTypeDef *htim) {
    hc_htim = htim;
    HAL_TIM_IC_Start_IT(hc_htim, TIM_CHANNEL_2);
    HAL_TIM_IC_Start_IT(hc_htim, TIM_CHANNEL_4);
}

void HC_SR04_Trigger(void) {
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8 | GPIO_PIN_5, GPIO_PIN_SET);
    for(volatile uint32_t i = 0; i < 720; i++) {}
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8 | GPIO_PIN_5, GPIO_PIN_RESET);
}

void HC_SR04_IC_Callback(TIM_HandleTypeDef *htim) {
    if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_2) {
        if (sensor1.capture_flag == 0) {
            sensor1.capture_val1 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_2);
            sensor1.capture_flag = 1;
            __HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_2, TIM_INPUTCHANNELPOLARITY_FALLING);
        } else if (sensor1.capture_flag == 1) {
            sensor1.capture_val2 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_2);
            if (sensor1.capture_val2 >= sensor1.capture_val1) {
                sensor1.distance_cm = (sensor1.capture_val2 - sensor1.capture_val1) / 58;
            } else {
                sensor1.distance_cm = ((0xFFFF - sensor1.capture_val1) + sensor1.capture_val2) / 58;
            }
            sensor1.capture_flag = 0;
            __HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_2, TIM_INPUTCHANNELPOLARITY_RISING);
        }
    }

    if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_4) {
        if (sensor2.capture_flag == 0) {
            sensor2.capture_val1 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_4);
            sensor2.capture_flag = 1;
            __HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_4, TIM_INPUTCHANNELPOLARITY_FALLING);
        } else if (sensor2.capture_flag == 1) {
            sensor2.capture_val2 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_4);
            if (sensor2.capture_val2 >= sensor2.capture_val1) {
                sensor2.distance_cm = (sensor2.capture_val2 - sensor2.capture_val1) / 58;
            } else {
                sensor2.distance_cm = ((0xFFFF - sensor2.capture_val1) + sensor2.capture_val2) / 58;
            }
            sensor2.capture_flag = 0;
            __HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_4, TIM_INPUTCHANNELPOLARITY_RISING);
        }
    }
}

uint16_t HC_SR04_Get_Min_Distance(void) {
    uint16_t d1 = (sensor1.distance_cm == 0) ? 999 : sensor1.distance_cm;
    uint16_t d2 = (sensor2.distance_cm == 0) ? 999 : sensor2.distance_cm;
    return (d1 < d2) ? d1 : d2;
}
