import struct

class UartProtocol:
    FRAME_HEADER_1 = 0xAA
    FRAME_HEADER_2 = 0xBB
    STRUCT_FORMAT = '<Bff' 
    PACKET_SIZE = 12

    @staticmethod
    def _calculate_checksum(payload_bytes: bytes) -> int:
        checksum = 0
        for byte in payload_bytes:
            checksum ^= byte
        return checksum

    @classmethod
    def pack_data(cls, status: int, speed: float, angle: float) -> bytes:
        try:
            payload_bytes = struct.pack(cls.STRUCT_FORMAT, status, speed, angle)
            checksum = cls._calculate_checksum(payload_bytes)
            return bytes([cls.FRAME_HEADER_1, cls.FRAME_HEADER_2]) + payload_bytes + bytes([checksum])
        except Exception:
            return b""

    @classmethod
    def unpack_data(cls, packet_bytes: bytes) -> dict:
        if len(packet_bytes) != cls.PACKET_SIZE:
            return None
        
        if packet_bytes[0] != cls.FRAME_HEADER_1 or packet_bytes[1] != cls.FRAME_HEADER_2:
            return None
            
        payload_bytes = packet_bytes[2:11]
        if cls._calculate_checksum(payload_bytes) != packet_bytes[11]:
            return None
            
        try:
            status, speed, angle = struct.unpack(cls.STRUCT_FORMAT, payload_bytes)
            return {"status": status, "speed": round(speed, 4), "angle": round(angle, 4)}
        except Exception:
            return None