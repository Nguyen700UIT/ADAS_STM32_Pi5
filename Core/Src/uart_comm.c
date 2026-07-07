#include "uart_comm.h"
#include <string.h>

// ---------------------------------------------------------
// BIẾN TOÀN CỤC & TĨNH (STATIC)
// ---------------------------------------------------------
#define DANGER_THRESHOLD_CM 20

static UART_RX_Packet_t current_rx_packet = {0, 0, 0};
static UART_TX_Packet_t current_tx_packet = {0, 0};

/* Buffer nhận DMA thô */
static uint8_t rx_dma_buffer[sizeof(UART_RX_Packet_t)];

/* Quản lý trạng thái hệ thống */
static System_State_t current_system_state = SYS_STATE_NORMAL;

// ---------------------------------------------------------
// TRIỂN KHAI HÀM CHỨC NĂNG
// ---------------------------------------------------------

void UART_Comm_Init(UART_HandleTypeDef *huart) {
    // Xóa bộ đệm
    memset(&current_rx_packet, 0, sizeof(UART_RX_Packet_t));
    memset(rx_dma_buffer, 0, sizeof(rx_dma_buffer));

    // Kích hoạt ngắt nhận UART qua DMA.
    // Yêu cầu: Đã cấu hình DMA Circular mode trong CubeMX cho luồng RX.
    HAL_UART_Receive_DMA(huart, rx_dma_buffer, sizeof(rx_dma_buffer));
}

/* Callback ngắt DMA RX Cplt - Tự động được gọi bởi HAL khi nhận đủ số byte */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART1) {
        // Parse dữ liệu từ buffer thô vào struct an toàn
        memcpy(&current_rx_packet, rx_dma_buffer, sizeof(UART_RX_Packet_t));
    }
}

void FSM_Update(uint16_t current_distance_cm) {
    // Điều kiện an toàn: Bỏ qua các giá trị nhiễu bằng 0 của cảm biến siêu âm
    if (current_distance_cm > 0 && current_distance_cm <= DANGER_THRESHOLD_CM) {
        // Chuyển sang trạng thái khẩn cấp
        current_system_state = SYS_STATE_EMERGENCY_STOP;
    } else {
        // Khôi phục trạng thái hoạt động bình thường
        current_system_state = SYS_STATE_NORMAL;
    }
}

void FSM_Get_Control_Signals(int16_t *out_speed, int8_t *out_steering) {
    switch (current_system_state) {
        case SYS_STATE_EMERGENCY_STOP:
            *out_speed = 0; // Force dừng khẩn cấp
            *out_steering = current_rx_packet.steering_error; // Giữ nguyên góc lái hoặc trả thẳng
            break;

        case SYS_STATE_AVOID_REVERSE:
            *out_speed = -30; // Force lùi với PWM/RPM an toàn
            *out_steering = -current_rx_packet.steering_error; // Lùi đánh lái ngược lại (tùy logic)
            break;

        case SYS_STATE_NORMAL:
        default:
            // Bypass tín hiệu gốc từ RPi xuống khối PID/Servo
            *out_speed = current_rx_packet.target_speed;
            *out_steering = current_rx_packet.steering_error;
            break;
    }
}

void UART_Comm_Send(UART_HandleTypeDef *huart, uint16_t distance, int16_t rpm) {
    // Cập nhật dữ liệu vào struct
    current_tx_packet.distance_cm = distance;
    current_tx_packet.actual_rpm = rpm;

    // Gửi Non-blocking qua DMA hoặc IT. Ở đây dùng IT để tiết kiệm kênh DMA nếu CubeMX chưa setup DMA TX.
    // Nếu có DMA TX, thay thế bằng HAL_UART_Transmit_DMA.
    HAL_UART_Transmit_IT(huart, (uint8_t*)&current_tx_packet, sizeof(UART_TX_Packet_t));
}
