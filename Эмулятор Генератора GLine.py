
import serial


PORT = "COM10"
BAUDRATE = 9600
SLAVE_ID = 2

TIMEOUT = 0.2


def calculate_crc(data: bytes) -> bytes:
    """Вычисляет CRC-16/Modbus и возвращает два байта в нужном порядке."""
    crc = 0xFFFF

    for byte in data:
        crc ^= byte

        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1

    return crc.to_bytes(2, byteorder="little")


def append_crc(data: bytes) -> bytes:
    """Добавляет CRC в конец сообщения."""
    return data + calculate_crc(data)


def is_valid_crc(frame: bytes) -> bool:
    """Проверяет CRC принятого Modbus RTU сообщения."""
    if len(frame) < 4:
        return False

    return frame[-2:] == calculate_crc(frame[:-2])


# Идентификационная строка генератора — ровно 34 байта ASCII.
MODEL_ASCII = b"GLine.L-000K6.13M56.0.4-002.1226  "

if len(MODEL_ASCII) != 34:
    raise ValueError(
        f"Длина MODEL_ASCII должна быть 34 байта, "
        f"сейчас: {len(MODEL_ASCII)}"
    )


# Данные holding-регистров 0–16.
HOLDING_REGISTERS = [
    3, 0, 2, 0,
    600, 550, 0, 0,
    0, 0, 0, 0,
    0, 0, 0, 0, 0,
]


def handle_request(request: bytes) -> bytes | None:
    """Обрабатывает запрос и возвращает ответ либо None."""

    if len(request) < 4:
        return None

    # Игнорируем запросы к другим адресам.
    if request[0] != SLAVE_ID:
        return None

    # Игнорируем запросы с некорректной CRC.
    if not is_valid_crc(request):
        print("[!] Получен запрос с неверной CRC.")
        return None

    function_code = request[1]

    # Команда 0x11 — Read Slave ID / идентификация устройства.
    if function_code == 0x11:
        if len(request) != 4:
            return None

        print("[->] Получен запрос идентификации (0x11).")

        # 01: адрес, 11: функция, 24: 36 байт данных.
        # Данные: статус ВЧ-выхода, служебный байт, 34 байта модели.
        response = (
            bytes([SLAVE_ID, 0x11, 0x24, 0x00, 0x00])
            + MODEL_ASCII
        )

        return append_crc(response)

    # Команда 0x03 — Read Holding Registers.
    if function_code == 0x03:
        if len(request) != 8:
            return None

        start_address = int.from_bytes(request[2:4], "big")
        quantity = int.from_bytes(request[4:6], "big")

        if quantity < 1 or quantity > 125:
            return None

        end_address = start_address + quantity

        # В эмуляторе доступны регистры с адресами 0–16.
        if start_address >= len(HOLDING_REGISTERS):
            values = []
        else:
            values = HOLDING_REGISTERS[
                start_address:min(end_address, len(HOLDING_REGISTERS))
            ]

        # Если запрос выходит за пределы доступных регистров,
        # возвращаем Modbus exception: Illegal Data Address.
        if len(values) != quantity:
            response = bytes([SLAVE_ID, function_code | 0x80, 0x02])
            return append_crc(response)

        register_bytes = b"".join(
            value.to_bytes(2, byteorder="big")
            for value in values
        )

        response = (
            bytes([SLAVE_ID, 0x03, len(register_bytes)])
            + register_bytes
        )

        print(
            f"[->] Запрос регистров 0x03: "
            f"адрес {start_address}, количество {quantity}."
        )

        return append_crc(response)

    # Неизвестная функция: стандартный ответ Modbus exception.
    response = bytes([SLAVE_ID, function_code | 0x80, 0x01])
    return append_crc(response)


def main():
    if not 1 <= SLAVE_ID <= 247:
        raise ValueError("SLAVE_ID должен находиться в диапазоне 1–247.")

    try:
        with serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=TIMEOUT,
        ) as ser:

            print(f"Эмулятор генератора GLine запущен.")
            print(f"Порт: {PORT}")
            print(f"Скорость: {BAUDRATE}")
            print(f"Slave ID: {SLAVE_ID}")
            print("Ожидание запросов...")

            while True:
                # Читаем поступившие данные после короткого тайм-аута.
                request = ser.read(1024)

                if not request:
                    continue

                # Эмулятор отвечает только на запросы своего адреса.
                if request[0] != SLAVE_ID:
                    continue

                response = handle_request(request)

                if response is not None:
                    ser.write(response)
                    ser.flush()
                    print(
                        f"[<-] Отправлен ответ: "
                        f"{response.hex(' ').upper()}"
                    )

    except serial.SerialException as error:
        print(f"Ошибка последовательного порта: {error}")
    except KeyboardInterrupt:
        print("\nЭмулятор остановлен.")


if __name__ == "__main__":
    main()

