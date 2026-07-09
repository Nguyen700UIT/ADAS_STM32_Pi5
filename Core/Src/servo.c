#include "servo.h"

#define SERVO_SLEW_STEP 10

static TIM_HandleTypeDef *servo_htim;
static int8_t current_angle = 0;
static int8_t target_angle = 0;
static uint32_t servo_arr = 0;

void Servo_Init(TIM_HandleTypeDef *htim) {
    servo_htim = htim;
    if (servo_htim != NULL) {
        servo_arr = __HAL_TIM_GET_AUTORELOAD(servo_htim);
        HAL_TIM_PWM_Start(servo_htim, TIM_CHANNEL_1);
        current_angle = 0;
        target_angle = 0;
        Servo_Update_Slew_Rate(); // Init default position
    }
}

void Servo_Set_Target_Angle(int8_t steering_error) {
    if (steering_error < -100) steering_error = -100;
    if (steering_error > 100) steering_error = 100;
    target_angle = steering_error;
}

void Servo_Update_Slew_Rate(void) {
    if (!servo_htim) return;

    if (current_angle < target_angle) {
        current_angle += SERVO_SLEW_STEP;
        if (current_angle > target_angle) current_angle = target_angle;
    } else if (current_angle > target_angle) {
        current_angle -= SERVO_SLEW_STEP;
        if (current_angle < target_angle) current_angle = target_angle;
    }

    uint32_t center_pulse = (servo_arr * 75) / 1000;
    int32_t offset_pulse = (current_angle * (int32_t)servo_arr * 25) / 100000;

    uint32_t pulse = center_pulse + offset_pulse;
    __HAL_TIM_SET_COMPARE(servo_htim, TIM_CHANNEL_1, pulse);
}
