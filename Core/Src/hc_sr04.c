#include "hc_sr04.h"

static TIM_HandleTypeDef *hc_htim;
static HC_SR04_Sensor_t sensor_left = {0};
static HC_SR04_Sensor_t sensor_right = {0};

void HC_SR04_Init(TIM_HandleTypeDef *htim) {
    hc_htim = htim;
    HAL_TIM_IC_Start_IT(hc_htim, TIM_CHANNEL_2);
    HAL_TIM_IC_Start_IT(hc_htim, TIM_CHANNEL_4);
}

// Hàm mới: Gọi trong Scheduler 20ms để bắt đầu kích xung
void HC_SR04_Trigger_Start(TIM_HandleTypeDef *trigger_htim) {
    // Reset counter để đảm bảo luôn đủ 10µs
    __HAL_TIM_SET_COUNTER(trigger_htim, 0);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8 | GPIO_PIN_5, GPIO_PIN_SET);
    HAL_TIM_Base_Start_IT(trigger_htim);
}

// Chỉ xử lý sườn xuống của xung Trigger 10µs
void HC_SR04_Trigger_IT(TIM_HandleTypeDef *trigger_htim) {
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8 | GPIO_PIN_5, GPIO_PIN_RESET);
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

    // Chỉ reset khi state bị treo (đang đợi sườn xuống quá lâu)
    if (sensor_left.capture_flag == 1) {
        sensor_left.capture_flag = 0;
        sensor_left.distance_cm = 999;
        __HAL_TIM_SET_CAPTUREPOLARITY(hc_htim, TIM_CHANNEL_2, TIM_INPUTCHANNELPOLARITY_RISING);
    }

    if (sensor_right.capture_flag == 1) {
        sensor_right.capture_flag = 0;
        sensor_right.distance_cm = 999;
        __HAL_TIM_SET_CAPTUREPOLARITY(hc_htim, TIM_CHANNEL_4, TIM_INPUTCHANNELPOLARITY_RISING);
    }
}
