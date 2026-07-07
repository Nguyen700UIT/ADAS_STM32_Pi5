#include "uart_comm.h"
#include <string.h>
#define DANGER_THRESHOLD_CM 20

static UART_RX_Packet_t current_rx_packet = {0, 0, 0};
static UART_TX_Packet_t current_tx_packet = {0, 0};
static uint8_t rx_dma_buffer[sizeof(UART_RX_Packet_t)];
static System_State_t current_system_state = SYS_STATE_NORMAL;

void UART_Comm_Init(UART_HandleTypeDef *huart) {
    memset(&current_rx_packet, 0, sizeof(UART_RX_Packet_t));
    memset(rx_dma_buffer, 0, sizeof(rx_dma_buffer));
    HAL_UART_Receive_DMA(huart, rx_dma_buffer, sizeof(rx_dma_buffer));
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART1) {
        memcpy(&current_rx_packet, rx_dma_buffer, sizeof(UART_RX_Packet_t));
    }
}

void FSM_Update(uint16_t current_distance_cm) {
    if (current_distance_cm > 0 && current_distance_cm <= DANGER_THRESHOLD_CM) {
        current_system_state = SYS_STATE_EMERGENCY_STOP;
    } else {
        current_system_state = SYS_STATE_NORMAL;
    }
}

void FSM_Get_Control_Signals(int16_t *out_speed, int8_t *out_steering) {
    switch (current_system_state) {
        case SYS_STATE_EMERGENCY_STOP:
            *out_speed = 0;
            *out_steering = current_rx_packet.steering_error;
            break;
        case SYS_STATE_AVOID_REVERSE:
            *out_speed = -30;
            *out_steering = -current_rx_packet.steering_error;
            break;
        case SYS_STATE_NORMAL:
        default:
            *out_speed = current_rx_packet.target_speed;
            *out_steering = current_rx_packet.steering_error;
            break;
    }
}

void UART_Comm_Send(UART_HandleTypeDef *huart, uint16_t distance, int16_t rpm) {
    current_tx_packet.distance_cm = distance;
    current_tx_packet.actual_rpm = rpm;
    HAL_UART_Transmit_IT(huart, (uint8_t*)&current_tx_packet, sizeof(UART_TX_Packet_t));
}
