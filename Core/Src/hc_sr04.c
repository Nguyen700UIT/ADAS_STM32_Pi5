#include "hc_sr04.h"
#include "main.h"

static TIM_HandleTypeDef *hc_htim;
static HC_SR04_Sensor_t sensor_left = {0};
static HC_SR04_Sensor_t sensor_right = {0};
static uint8_t sensor_turn = 0; // Thêm cờ trạng thái để đo luân phiên

void HC_SR04_Init(TIM_HandleTypeDef *htim) {
    hc_htim = htim;
    HAL_TIM_IC_Start_IT(hc_htim, TIM_CHANNEL_2);
    HAL_TIM_IC_Start_IT(hc_htim, TIM_CHANNEL_4);
}

void HC_SR04_Trigger_Start(TIM_HandleTypeDef *trigger_htim) {
    __HAL_TIM_SET_COUNTER(trigger_htim, 0);
    __HAL_TIM_CLEAR_IT(trigger_htim, TIM_IT_UPDATE);
    // Luân phiên  mỗi 20ms
    if (sensor_turn == 0) {
        HAL_GPIO_WritePin(TRIG1_GPIO_Port, TRIG1_Pin, GPIO_PIN_SET);
        sensor_turn = 1;
    } else {
        HAL_GPIO_WritePin(TRIG2_GPIO_Port, TRIG2_Pin, GPIO_PIN_SET);
        sensor_turn = 0;
    }

    HAL_TIM_Base_Start_IT(trigger_htim);
}

void HC_SR04_Trigger_IT(TIM_HandleTypeDef *trigger_htim) {
    HAL_GPIO_WritePin(TRIG1_GPIO_Port, TRIG1_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(TRIG2_GPIO_Port, TRIG2_Pin, GPIO_PIN_RESET);
    HAL_TIM_Base_Stop_IT(trigger_htim);
}

void HC_SR04_IC_Callback(TIM_HandleTypeDef *htim) {
    uint32_t timer_period = __HAL_TIM_GET_AUTORELOAD(htim);

    if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_2) {
        if (sensor_left.capture_flag == 0) {
            sensor_left.capture_val1 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_2);
            sensor_left.capture_flag = 1;
            __HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_2, TIM_INPUTCHANNELPOLARITY_FALLING);
        } else if (sensor_left.capture_flag == 1) {
            sensor_left.capture_val2 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_2);

            uint32_t pulse_width = 0;
            if (sensor_left.capture_val2 >= sensor_left.capture_val1) {
                pulse_width = sensor_left.capture_val2 - sensor_left.capture_val1;
            } else {
                pulse_width = (timer_period - sensor_left.capture_val1) + sensor_left.capture_val2 + 1;
            }

            // LỌC BÓNG MA: Nếu độ rộng xung sát ngưỡng tràn (ARR), coi như ngoài tầm đo
            if (pulse_width > 19000) {
                sensor_left.distance_cm = 999;
            } else {
                sensor_left.distance_cm = pulse_width * 10 / 583;
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

            uint32_t pulse_width = 0;
            if (sensor_right.capture_val2 >= sensor_right.capture_val1) {
                pulse_width = sensor_right.capture_val2 - sensor_right.capture_val1;
            } else {
                pulse_width = (timer_period - sensor_right.capture_val1) + sensor_right.capture_val2 + 1;
            }

            if (pulse_width > 19000) {
                sensor_right.distance_cm = 999;
            } else {
                sensor_right.distance_cm = pulse_width * 10 / 583;
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

void HC_SR04_Watchdog_Check(void) {
    if (!hc_htim) return;

    __disable_irq();

    if (sensor_left.capture_flag == 1) {
        sensor_left.capture_flag = 0;
        sensor_left.capture_val1 = 0; // Xóa rác thanh ghi
        sensor_left.distance_cm = 999;
        __HAL_TIM_SET_CAPTUREPOLARITY(hc_htim, TIM_CHANNEL_2, TIM_INPUTCHANNELPOLARITY_RISING);
    }

    if (sensor_right.capture_flag == 1) {
        sensor_right.capture_flag = 0;
        sensor_right.capture_val1 = 0; // Xóa rác thanh ghi
        sensor_right.distance_cm = 999;
        __HAL_TIM_SET_CAPTUREPOLARITY(hc_htim, TIM_CHANNEL_4, TIM_INPUTCHANNELPOLARITY_RISING);
    }

    __enable_irq();
}
