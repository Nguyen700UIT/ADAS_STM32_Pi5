from app.communication.uart import UartConfiguration
from app.communication.protocol import UartProtocol


uart = UartConfiguration(port='/dev/ttyAMA0', baudrate=115200, timeout=0.5)
uart_connected = uart.connect()

if uart_connected:
    print("[PIPELINE] UART connected to STM32")
else:
    print("[PIPELINE] Unable to connect UART")


def process(frame):
    """Read data from the UART, combine it with a frame, and return it."""
    data = {}
    
    if uart_connected:
        packet = uart.read_raw_bytes(UartProtocol.PACKET_SIZE)
        if packet and len(packet) == UartProtocol.PACKET_SIZE:
            result = UartProtocol.unpack_data(packet)
            if result:
                data = result  
    return (frame, data)
