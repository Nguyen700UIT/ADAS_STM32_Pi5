import struct

class UartProtocol:
    FRAME_HEADER_1 = 0xAA
    FRAME_HEADER_2 = 0x55
    
    _HEADER_BYTES = bytes([0xAA, 0x55])
    
    _TX_STRUCT = struct.Struct('<BhbB')
    TX_PACKET_SIZE = 8
    
    _RX_STRUCT = struct.Struct('<HHh')
    RX_PACKET_SIZE = 9

    @staticmethod
    def _calculate_checksum(payload_bytes: bytes) -> int:
        return sum(payload_bytes) & 0xFF

    @classmethod
    def pack_data(cls, cmd_id: int, target_speed: int, steering_error: int, brake_command: int) -> bytes:
        try:
            payload_bytes = cls._TX_STRUCT.pack(
                int(cmd_id), 
                int(target_speed), 
                int(steering_error), 
                int(brake_command)
            )
            checksum = cls._calculate_checksum(payload_bytes)
            return cls._HEADER_BYTES + payload_bytes + bytes([checksum])
        except struct.error:
            return b""

    @classmethod
    def unpack_data(cls, packet_bytes: bytes) -> dict:
        if not packet_bytes or len(packet_bytes) != cls.RX_PACKET_SIZE:
            return None
        
        if packet_bytes[0] != cls.FRAME_HEADER_1 or packet_bytes[1] != cls.FRAME_HEADER_2:
            return None
            
        payload_bytes = packet_bytes[2:8]
        rx_checksum = packet_bytes[8]
        
        if cls._calculate_checksum(payload_bytes) != rx_checksum:
            return None
            
        try:
            dist_left, dist_right, actual_rpm = cls._RX_STRUCT.unpack(payload_bytes)
            return {
                "distance_left": dist_left,
                "distance_right": dist_right,
                "actual_rpm": actual_rpm
            }
        except struct.error:
            return None