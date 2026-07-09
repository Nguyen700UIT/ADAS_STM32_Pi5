#include "hc_sr04.h"

static TIM_HandleTypeDef *hc_htim;
static HC_SR04_Sensor_t sensor_left = {0};
static HC_SR04_Sensor_t sensor_right = {0};

void HC_SR04_Init(TIM_HandleTypeDef *htim) {
    hc_htim = htim;
    HAL_TIM_IC_Start_IT(hc_htim, TIM_CHANNEL_2);
    HAL_TIM_IC_Start_IT(hc_htim, TIM_CHANNEL_4);
}

void HC_SR04_Trigger_IT(TIM_HandleTypeDef *trigger_htim) {
    static uint8_t state = 0;
    if (state == 0) {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8 | GPIO_PIN_5, GPIO_PIN_SET);
        state = 1;
    } else {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8 | GPIO_PIN_5, GPIO_PIN_RESET);
        state = 0;
        HAL_TIM_Base_Stop_IT(trigger_htim);
    }
}

void HC_SR04_IC_Callback(TIM_HandleTypeDef *htim) {
    if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_2) {
        if (sensor_left.capture_flag == 0) {
            sensor_left.capture_val1 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_2);
            sensor_left.capture_flag = 1;
            __HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_2, TIM_INPUTCHANNELPOLARITY_FALLING);
        } else if (sensor_left.capture_flag == 1) {
            sensor_left.capture_val2 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_2);
            if (sensor_left.capture_val2 >= sensor_left.capture_val1) {
                sensor_left.distance_cm = (sensor_left.capture_val2 - sensor_left.capture_val1) * 10 / 583;
            } else {
                sensor_left.distance_cm = ((0xFFFF - sensor_left.capture_val1) + sensor_left.capture_val2) * 10 / 583;
            }
            sensor_left.capture_flag = 0;
            __HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_2, TIM_INPUTCHANNELPOLARITY_RISING);
        }
    }

    if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_4) {
        if (sensor_right.capture_flag == 0) {
            sensor_right.capture_val1 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_4);
            sensor_right.capture_flag = 1;
            __HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_4, TIM_INPUTCHANNELPOLARITY_FALLING);
        } else if (sensor_right.capture_flag == 1) {
            sensor_right.capture_val2 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_4);
            if (sensor_right.capture_val2 >= sensor_right.capture_val1) {
                sensor_right.distance_cm = (sensor_right.capture_val2 - sensor_right.capture_val1) * 10 / 583;
            } else {
                sensor_right.distance_cm = ((0xFFFF - sensor_right.capture_val1) + sensor_right.capture_val2) * 10 / 583;
            }
            sensor_right.capture_flag = 0;
            __HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_4, TIM_INPUTCHANNELPOLARITY_RISING);
        }
    }
}

uint16_t HC_SR04_Get_Distance_Left(void) {
    return (sensor_left.distance_cm == 0) ? 999 : sensor_left.distance_cm;
}

uint16_t HC_SR04_Get_Distance_Right(void) {
    return (sensor_right.distance_cm == 0) ? 999 : sensor_right.distance_cm;
}
