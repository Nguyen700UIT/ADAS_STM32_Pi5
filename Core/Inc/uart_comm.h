#ifndef UART_COMM_H
#define UART_COMM_H

#include "stm32f1xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

#pragma pack(push, 1)

typedef struct {
    uint8_t  cmd_id;
    int16_t  target_speed;
    int8_t   steering_error;
} UART_RX_Packet_t;

typedef struct {
    uint16_t distance_cm;
    int16_t  actual_rpm;
} UART_TX_Packet_t;

#pragma pack(pop)

typedef enum {
    SYS_STATE_NORMAL = 0,
    SYS_STATE_EMERGENCY_STOP,
    SYS_STATE_AVOID_REVERSE
} System_State_t;

void UART_Comm_Init(UART_HandleTypeDef *huart);
void FSM_Update(uint16_t current_distance_cm);
void FSM_Get_Control_Signals(int16_t *out_speed, int8_t *out_steering);
void UART_Comm_Send(UART_HandleTypeDef *huart, uint16_t distance, int16_t rpm);

#endif
