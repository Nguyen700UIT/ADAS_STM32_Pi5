#include "uart_comm.h"

static UART_HandleTypeDef *comm_huart;

static Pi_Command_t current_command = {0, 0, 0, true};
static uint32_t last_valid_rx_time = 0;

typedef enum {
    RX_WAIT_H1,
    RX_WAIT_H2,
    RX_GET_PAYLOAD,
    RX_GET_CHECKSUM,
    RX_WAIT_TERM
} RX_State_t;

static RX_State_t rx_state = RX_WAIT_H1;
static uint8_t rx_byte;
static uint8_t rx_payload[4];
static uint8_t rx_idx = 0;

void UART_Comm_Init(UART_HandleTypeDef *huart) {
    comm_huart = huart;
    current_command.is_failsafe_active = true;
    last_valid_rx_time = HAL_GetTick();

    HAL_UART_Receive_IT(comm_huart, &rx_byte, 1);
}

Pi_Command_t UART_Comm_Get_Command(void) {
    return current_command;
}

void UART_Comm_Send_Sensor_Data(STM32_SensorData_t *sensor_data) {
    uint8_t tx_frame[9];

    tx_frame[0] = 0xAA;
    tx_frame[1] = 0x55;

    tx_frame[2] = sensor_data->sensor_id;
    tx_frame[3] = (uint8_t)(sensor_data->distance_mm & 0xFF);
    tx_frame[4] = (uint8_t)((sensor_data->distance_mm >> 8) & 0xFF);
    tx_frame[5] = (uint8_t)(sensor_data->actual_rpm & 0xFF);
    tx_frame[6] = (uint8_t)((sensor_data->actual_rpm >> 8) & 0xFF);

    tx_frame[7] = tx_frame[2] ^ tx_frame[3] ^ tx_frame[4] ^ tx_frame[5] ^ tx_frame[6];
    tx_frame[8] = 0x0A;

    HAL_UART_Transmit_IT(comm_huart, tx_frame, 9);
}

void UART_Comm_Failsafe_Check(void) {
    if ((HAL_GetTick() - last_valid_rx_time) > 500) {
        current_command.target_speed = 0;
        current_command.is_failsafe_active = true;
    } else {
        current_command.is_failsafe_active = false;
    }
}

void UART_Comm_Rx_StateMachine(UART_HandleTypeDef *huart) {
    if (huart->Instance == comm_huart->Instance) {
        switch(rx_state) {
            case RX_WAIT_H1:
                if (rx_byte == 0xAA) rx_state = RX_WAIT_H2;
                break;

            case RX_WAIT_H2:
                if (rx_byte == 0x55) {
                    rx_state = RX_GET_PAYLOAD;
                    rx_idx = 0;
                } else {
                    rx_state = RX_WAIT_H1;
                }
                break;

            case RX_GET_PAYLOAD:
                rx_payload[rx_idx++] = rx_byte;
                if (rx_idx == 4) rx_state = RX_GET_CHECKSUM;
                break;

            case RX_GET_CHECKSUM:
                {
                    uint8_t calc_chk = rx_payload[0] ^ rx_payload[1] ^ rx_payload[2] ^ rx_payload[3];
                    if (rx_byte == calc_chk) {
                        rx_state = RX_WAIT_TERM;
                    } else {
                        rx_state = RX_WAIT_H1;
                    }
                }
                break;

            case RX_WAIT_TERM:
                if (rx_byte == 0x0A) {
                    current_command.command_id = rx_payload[0];
                    current_command.target_speed = rx_payload[1];
                    current_command.steering_error = (int16_t)((rx_payload[3] << 8) | rx_payload[2]);

                    last_valid_rx_time = HAL_GetTick();
                }
                rx_state = RX_WAIT_H1;
                break;
        }
        HAL_UART_Receive_IT(comm_huart, &rx_byte, 1);
    }
}
