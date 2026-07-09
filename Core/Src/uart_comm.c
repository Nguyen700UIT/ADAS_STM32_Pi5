#include "uart_comm.h"
#include <string.h>

static UART_RX_Packet_t current_rx_packet = {0};
static UART_TX_Packet_t current_tx_packet = {0};
static uint8_t rx_dma_buffer[RX_BUF_SIZE];
static uint16_t rd_ptr = 0;
static System_State_t current_system_state = SYS_STATE_NORMAL;
static bool rpi_brake_request = false;

void UART_Comm_Init(UART_HandleTypeDef *huart) {
    memset(&current_rx_packet, 0, sizeof(UART_RX_Packet_t));
    memset(&current_tx_packet, 0, sizeof(UART_TX_Packet_t));
    rd_ptr = 0;
    current_system_state = SYS_STATE_NORMAL;
    rpi_brake_request = false;
    HAL_UART_Receive_DMA(huart, rx_dma_buffer, RX_BUF_SIZE);
}

void UART_Comm_Process(UART_HandleTypeDef *huart) {
    uint16_t wr_ptr = RX_BUF_SIZE - __HAL_DMA_GET_COUNTER(huart->hdmarx);

    while (rd_ptr != wr_ptr) {
        uint16_t next_ptr = (rd_ptr + 1) % RX_BUF_SIZE;
        uint16_t bytes_available = (wr_ptr >= rd_ptr) ? (wr_ptr - rd_ptr) : (RX_BUF_SIZE - rd_ptr + wr_ptr);

        if (bytes_available >= sizeof(UART_RX_Packet_t)) {
            if (rx_dma_buffer[rd_ptr] == UART_HEADER1 && rx_dma_buffer[next_ptr] == UART_HEADER2) {

                uint8_t temp_buf[sizeof(UART_RX_Packet_t)];
                uint8_t calc_checksum = 0;

                for (uint16_t i = 0; i < sizeof(UART_RX_Packet_t); i++) {
                    temp_buf[i] = rx_dma_buffer[(rd_ptr + i) % RX_BUF_SIZE];
                    if (i >= 2 && i < (sizeof(UART_RX_Packet_t) - 1)) {
                        calc_checksum += temp_buf[i];
                    }
                }

                UART_RX_Packet_t *parsed_packet = (UART_RX_Packet_t *)temp_buf;

                if (parsed_packet->checksum == calc_checksum) {
                    current_rx_packet = *parsed_packet;
                    rpi_brake_request = (current_rx_packet.brake_command != 0);
                                        rd_ptr = (rd_ptr + sizeof(UART_RX_Packet_t)) % RX_BUF_SIZE;
                    continue;
                }
            }
        }
        rd_ptr = next_ptr;
    }
}

void FSM_Update(uint16_t dist_left, uint16_t dist_right) {
    bool left_danger = (dist_left > 0 && dist_left <= DANGER_THRESHOLD_CM);
    bool right_danger = (dist_right > 0 && dist_right <= DANGER_THRESHOLD_CM);

    if (rpi_brake_request || (left_danger && right_danger)) {
        current_system_state = SYS_STATE_EMERGENCY_STOP;
    } else if (left_danger) {
        current_system_state = SYS_STATE_ALERT_LEFT;
    } else if (right_danger) {
        current_system_state = SYS_STATE_ALERT_RIGHT;
    } else {
        current_system_state = SYS_STATE_NORMAL;
    }
}

void FSM_Get_Control_Signals(int16_t *out_speed, int8_t *out_steering, bool *out_brake) {
    switch (current_system_state) {
        case SYS_STATE_EMERGENCY_STOP:
            *out_speed = 0;
            *out_steering = 0;
            *out_brake = true;
            break;

        case SYS_STATE_ALERT_LEFT:
            *out_speed = current_rx_packet.target_speed / 2;
            *out_steering = (current_rx_packet.steering_error < 0) ? 0 : current_rx_packet.steering_error;
            *out_brake = false;
            break;

        case SYS_STATE_ALERT_RIGHT:
            *out_speed = current_rx_packet.target_speed / 2;
            *out_steering = (current_rx_packet.steering_error > 0) ? 0 : current_rx_packet.steering_error;
            *out_brake = false;
            break;

        case SYS_STATE_NORMAL:
        default:
            *out_speed = current_rx_packet.target_speed;
            *out_steering = current_rx_packet.steering_error;
            *out_brake = false;
            break;
    }
}

void UART_Comm_Send(UART_HandleTypeDef *huart, uint16_t dist_left, uint16_t dist_right, int16_t rpm) {
    if (huart->gState != HAL_UART_STATE_READY) {
        return;
    }

    current_tx_packet.header1 = UART_HEADER1;
    current_tx_packet.header2 = UART_HEADER2;
    current_tx_packet.distance_left = dist_left;
    current_tx_packet.distance_right = dist_right;
    current_tx_packet.actual_rpm = rpm;

    uint8_t *raw_bytes = (uint8_t *)&current_tx_packet;
    uint8_t calc_checksum = 0;

    for (uint16_t i = 2; i < sizeof(UART_TX_Packet_t) - 1; i++) {
        calc_checksum += raw_bytes[i];
    }
    current_tx_packet.checksum = calc_checksum;

    HAL_UART_Transmit_IT(huart, (uint8_t*)&current_tx_packet, sizeof(UART_TX_Packet_t));
}
