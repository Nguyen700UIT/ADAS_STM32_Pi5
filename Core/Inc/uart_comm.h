#ifndef UART_COMM_H
#define UART_COMM_H

#include "stm32f1xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

#define UART_HEADER1         0xAA
#define UART_HEADER2         0x55
#define DANGER_THRESHOLD_CM  20
#define RX_BUF_SIZE          64

#pragma pack(push, 1)

typedef struct {
    uint8_t  header1;
    uint8_t  header2;
    uint8_t  cmd_id;
    int16_t  target_speed;
    int8_t   steering_error;
    uint8_t  brake_command;
    uint8_t  checksum;
} UART_RX_Packet_t;

typedef struct {
    uint8_t  header1;
    uint8_t  header2;
    uint16_t distance_left;
    uint16_t distance_right;
    int16_t  actual_rpm;
    uint8_t  checksum;
} UART_TX_Packet_t;

#pragma pack(pop)

typedef enum {
    SYS_STATE_NORMAL = 0,
    SYS_STATE_ALERT_LEFT,
    SYS_STATE_ALERT_RIGHT,
    SYS_STATE_EMERGENCY_STOP
} System_State_t;

void UART_Comm_Init(UART_HandleTypeDef *huart);
void UART_Comm_Process(UART_HandleTypeDef *huart);
void FSM_Update(uint16_t dist_left, uint16_t dist_right);
void FSM_Get_Control_Signals(int16_t *out_speed, int8_t *out_steering, bool *out_brake);
void UART_Comm_Send(UART_HandleTypeDef *huart, uint16_t dist_left, uint16_t dist_right, int16_t rpm);

#endif
