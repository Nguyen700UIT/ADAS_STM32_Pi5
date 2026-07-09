#include "motor_dc.h"

static TIM_HandleTypeDef *motor_pwm_htim;
static TIM_HandleTypeDef *motor_enc_htim;
static uint32_t motor_arr = 0;

void Motor_Init(TIM_HandleTypeDef *pwm_htim, TIM_HandleTypeDef *enc_htim) {
    motor_pwm_htim = pwm_htim;
    motor_enc_htim = enc_htim;

    if (motor_pwm_htim != NULL) {
        motor_arr = __HAL_TIM_GET_AUTORELOAD(motor_pwm_htim);
        HAL_TIM_PWM_Start(motor_pwm_htim, TIM_CHANNEL_1);
        HAL_TIM_PWM_Start(motor_pwm_htim, TIM_CHANNEL_2);
    }

    if (motor_enc_htim != NULL) {
        HAL_TIM_Encoder_Start(motor_enc_htim, TIM_CHANNEL_ALL);
    }
}

void Motor_Drive(int16_t speed, bool brake_flag) {
    if (!motor_pwm_htim) return;

    if (brake_flag) {
        __HAL_TIM_SET_COMPARE(motor_pwm_htim, TIM_CHANNEL_1, motor_arr);
        __HAL_TIM_SET_COMPARE(motor_pwm_htim, TIM_CHANNEL_2, motor_arr);
        return;
    }

    if (speed > (int16_t)motor_arr) speed = (int16_t)motor_arr;
    if (speed < -(int16_t)motor_arr) speed = -(int16_t)motor_arr;

    if (speed > 0) {
        __HAL_TIM_SET_COMPARE(motor_pwm_htim, TIM_CHANNEL_1, speed);
        __HAL_TIM_SET_COMPARE(motor_pwm_htim, TIM_CHANNEL_2, 0);
    } else if (speed < 0) {
        __HAL_TIM_SET_COMPARE(motor_pwm_htim, TIM_CHANNEL_1, 0);
        __HAL_TIM_SET_COMPARE(motor_pwm_htim, TIM_CHANNEL_2, (uint16_t)(-speed));
    } else {
        __HAL_TIM_SET_COMPARE(motor_pwm_htim, TIM_CHANNEL_1, 0);
        __HAL_TIM_SET_COMPARE(motor_pwm_htim, TIM_CHANNEL_2, 0);
    }
}

int16_t Motor_Read_Encoder(void) {
    if (!motor_enc_htim) return 0;

    int16_t count = (int16_t)__HAL_TIM_GET_COUNTER(motor_enc_htim);
    __HAL_TIM_SET_COUNTER(motor_enc_htim, 0);

    return count;
}
