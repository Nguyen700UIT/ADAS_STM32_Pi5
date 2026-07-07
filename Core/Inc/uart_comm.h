#ifndef UART_COMM_H
#define UART_COMM_H

#include "stm32f1xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

// ---------------------------------------------------------
// ĐỊNH NGHĨA CẤU TRÚC DỮ LIỆU (PACKETS)
// ---------------------------------------------------------
#pragma pack(push, 1)

/* Packet Nhận từ RPi (RX) - Kích thước: 4 Bytes */
typedef struct {
    uint8_t  cmd_id;          // Command ID (VD: 0x01 = Chạy, 0x02 = Dừng)
    int16_t  target_speed;    // Tốc độ mong muốn (Target Speed)
    int8_t   steering_error;  // Lỗi góc lái (-100 đến 100)
} UART_RX_Packet_t;

/* Packet Gửi lên RPi (TX) - Kích thước: 4 Bytes */
typedef struct {
    uint16_t distance_cm;     // Khoảng cách từ HC-SR04 nhỏ nhất (cm)
    int16_t  actual_rpm;      // Tốc độ thực tế từ Encoder
} UART_TX_Packet_t;

#pragma pack(pop)

// ---------------------------------------------------------
// ĐỊNH NGHĨA TRẠNG THÁI FSM (FAILSAFE)
// ---------------------------------------------------------
typedef enum {
    SYS_STATE_NORMAL = 0,
    SYS_STATE_EMERGENCY_STOP,
    SYS_STATE_AVOID_REVERSE
} System_State_t;

// ---------------------------------------------------------
// KHAI BÁO HÀM (PROTOTYPES)
// ---------------------------------------------------------

/* Khởi tạo UART & FSM. Bắt đầu luồng nhận DMA (Circular mode) */
void UART_Comm_Init(UART_HandleTypeDef *huart);

/* Cập nhật FSM dựa trên dữ liệu siêu âm, tự động ghi đè tín hiệu nếu cần */
void FSM_Update(uint16_t current_distance_cm);

/* Lấy giá trị điều khiển cuối cùng sau khi đã qua FSM kiểm duyệt */
void FSM_Get_Control_Signals(int16_t *out_speed, int8_t *out_steering);

/* Đóng gói và gửi TX Packet lên RPi (Non-blocking qua IT hoặc DMA) */
void UART_Comm_Send(UART_HandleTypeDef *huart, uint16_t distance, int16_t rpm);

#endif /* UART_COMM_H */
