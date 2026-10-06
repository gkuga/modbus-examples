# Hello world Modbus RTU client (master)
# Reads "Hello, Modbus!" from holding registers, then writes and reads back a register.

from pymodbus.client import ModbusSerialClient

PORT = "ttyV1"  # the other end of the virtual cable
BAUDRATE = 9600
DEVICE_ID = 1


def trace_packet(sending: bool, data: bytes) -> bytes:
    print(f"  {'TX' if sending else 'RX'}: {data.hex(' ')}")
    return data


def main():
    client = ModbusSerialClient(
        PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity="N",
        stopbits=1,
        trace_packet=trace_packet,
    )
    client.connect()

    print("Read holding registers 0-6 (function code 0x03)")
    rr = client.read_holding_registers(0, count=7, device_id=DEVICE_ID)
    print(f"  registers: {rr.registers}")
    text = client.convert_from_registers(rr.registers, client.DATATYPE.STRING)
    print(f"  decoded:   {text!r}")

    print("Write 42 to holding register 10 (function code 0x06)")
    client.write_register(10, 42, device_id=DEVICE_ID)

    print("Read holding register 10 (function code 0x03)")
    rr = client.read_holding_registers(10, count=1, device_id=DEVICE_ID)
    print(f"  registers: {rr.registers}")

    client.close()


if __name__ == "__main__":
    main()
