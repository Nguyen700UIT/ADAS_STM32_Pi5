#ifndef UART_COMM_H_
#define UART_COMM_H_

#include "stm32f1xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint8_t command_id;
    uint8_t target_speed;
    int16_t steering_error;
    bool is_failsafe_active;
} Pi_Command_t;

typedef struct {
    uint8_t sensor_id;
    uint16_t distance_mm;
    int16_t actual_rpm;
} STM32_SensorData_t;

void UART_Comm_Init(UART_HandleTypeDef *huart);
Pi_Command_t UART_Comm_Get_Command(void);
void UART_Comm_Send_Sensor_Data(STM32_SensorData_t *sensor_data);
void UART_Comm_Failsafe_Check(void);
void UART_Comm_Rx_StateMachine(UART_HandleTypeDef *huart);

#endif
