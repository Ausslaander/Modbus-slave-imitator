"""Последовательный Modbus RTU-имитатор ВЧ-генератора GLine.

Поддерживаемые функции Modbus:
    0x03 — Read Holding Registers (чтение регистров 0...40);
    0x11 — Read Slave ID (идентификация устройства).

"""

from __future__ import annotations

import time
from typing import Iterable

import gline_parameters as params


# ---------------------------------------------------------------------------
# Настройки последовательного порта.
# ---------------------------------------------------------------------------
PORT = "COM1"
BAUDRATE = 9600
SLAVE_ID = 2
TIMEOUT = 0.2

# Идентификационная строка — ровно 34 байта ASCII.
MODEL_ASCII = b"GLine.L-000K6.13M56.0.4-002.1226  "
if len(MODEL_ASCII) != 34:
    raise ValueError(f"MODEL_ASCII должна содержать 34 байта, сейчас {len(MODEL_ASCII)}")

# ---------------------------------------------------------------------------
# Постоянные параметры и уставки регистров 0...24.
# Карта соответствует разделу 11 руководства GLine, страницы 114–116.
# ---------------------------------------------------------------------------

# Регистр 0: биты состояния.
POWER_ENABLED = True
RF_ENABLED = True
RAMP_STAGE = 2             # 0=выкл., 1=плавное включение, 2=полная мощность,
                           # 3=плавное выключение, 4=ожидание сброса
KSV_TIMER_STATE = 0        # 0=неактивен, 2=счёт, 3=интервал пропуска, 4...=защита
KSV_TIMER_ENABLED = False
CONTROL_SOURCE = 1         # 0=панель, 1=RS-485, 3=А-25

# Регистр 1: индикаторы и аварийные флаги (по умолчанию аварий нет).
STATUS_ALARMS_REGISTER = 0

# Регистр 2: стабилизация мощности включена, режим 01 — по падающей мощности.
POWER_STABILIZATION_ENABLED = True
POWER_STABILIZATION_MODE = 1  # 1=падающая, 2=в нагрузке, 3=внешний зонд

# Регистр 3: параметры конфигурации. Код максимальной мощности 0 соответствует 600 Вт.
MAX_POWER_CODE = 0
REG3_LOW_BYTE_FLAGS = 0

# Уставки (не измеренные значения). Можно менять под конкретный сценарий.
SETPOINT_INCIDENT_POWER_W = 600       # регистр 4
SETPOINT_LOAD_POWER_W = 550           # регистр 5
SETPOINT_PROBE_VOLTAGE_V = 0          # регистр 6
SETPOINT_PAUSE_POWER_W = 0            # регистр 7
SETPOINT_PAUSE_VOLTAGE_V = 0          # регистр 8
PROGRAMMED_MAX_POWER_W = 600          # регистр 9
INTERNAL_PULSE_DURATION_MS = 0        # регистр 10
INTERNAL_PULSE_DUTY_X10 = 0           # регистр 11
INTERNAL_PULSE_FILL_FACTOR = 0        # регистр 12
INTERNAL_PULSE_FREQUENCY_HZ = 0      # регистр 13

# Составные байтовые параметры регистров 14 и 15.
RAMP_UP_TIME_S = 0                    # регистр 14, младший байт
RAMP_DOWN_TIME_S = 0                  # регистр 14, старший байт
KSV_SKIP_TIME_S = 0                   # регистр 15, старший байт
KSV_WORK_TIME_S = 0                   # регистр 15, младший байт
KSV_REFLECTED_POWER_THRESHOLD_W = 0   # регистр 16
PHASE_STEP_CODE = 0                   # регистр 17: бит 15 — шаг, биты 14:0 — код
OPERATING_FREQUENCY_X10_KHZ = 0       # регистр 18, согласно описанию руководства
ARC_SAFE_POWER_W = 0                  # регистр 19
ARC_POWER_DECREMENT_W = 0             # регистр 20
ARC_SUPPRESSION_TIME_US = 0           # регистр 21
ARC_DELAY_ON_START_X10_S = 0          # регистр 22, младший байт
ARC_DELAY_AFTER_SETPOINT_MS = 0       # регистр 22, старший байт

# Текущие значения таймеров/плавного пуска — регистры 23 и 24.
CURRENT_RAMP_UP_TIME_S = 0
CURRENT_RAMP_DOWN_TIME_S = 0
CURRENT_KSV_SKIP_TIME_S = 0
CURRENT_KSV_WORK_TIME_S = 0


START_TIME = time.monotonic()


def calculate_crc(data: bytes) -> bytes:
    """Вычисляет CRC-16/Modbus; младший байт возвращается первым."""
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
    return data + calculate_crc(data)


def is_valid_crc(frame: bytes) -> bool:
    return len(frame) >= 4 and frame[-2:] == calculate_crc(frame[:-2])


def _u16(value: float | int) -> int:
    """Преобразует значение в беззнаковый 16-битный регистр с ограничением диапазона."""
    return max(0, min(0xFFFF, int(round(value))))


def _u8(value: float | int) -> int:
    """Преобразует значение в беззнаковый байт с ограничением диапазона."""
    return max(0, min(0xFF, int(round(value))))


def _pack_bytes(high: float | int, low: float | int) -> int:
    """Упаковывает два значения по схеме старший байт / младший байт."""
    return (_u8(high) << 8) | _u8(low)


def _status_register_0() -> int:
    value = 0
    value |= int(POWER_ENABLED) << 0
    value |= int(RF_ENABLED) << 1
    value |= (RAMP_STAGE & 0b111) << 2
    value |= (KSV_TIMER_STATE & 0b111) << 5
    value |= int(KSV_TIMER_ENABLED) << 8
    value |= (CONTROL_SOURCE & 0b11) << 9
    return value


def _status_register_2() -> int:
    mode = POWER_STABILIZATION_MODE & 0b11
    return int(POWER_STABILIZATION_ENABLED) | (mode << 1)


def _status_register_3() -> int:
    return ((MAX_POWER_CODE & 0xFF) << 8) | (REG3_LOW_BYTE_FLAGS & 0xFF)


def build_holding_registers(t: float) -> list[int]:
    """Формирует полную карту 41 holding-регистра для момента времени t."""
    registers = [0] * 41

    # Регистры 0...3 — статус и конфигурация.
    registers[0] = _status_register_0()
    registers[1] = _u16(STATUS_ALARMS_REGISTER)
    registers[2] = _status_register_2()
    registers[3] = _status_register_3()

    # Регистры 4...24 — уставки и текущие служебные значения.
    registers[4] = _u16(SETPOINT_INCIDENT_POWER_W)
    registers[5] = _u16(SETPOINT_LOAD_POWER_W)
    registers[6] = _u16(SETPOINT_PROBE_VOLTAGE_V)
    registers[7] = _u16(SETPOINT_PAUSE_POWER_W)
    registers[8] = _u16(SETPOINT_PAUSE_VOLTAGE_V)
    registers[9] = _u16(PROGRAMMED_MAX_POWER_W)
    registers[10] = _u16(INTERNAL_PULSE_DURATION_MS)
    registers[11] = _u16(INTERNAL_PULSE_DUTY_X10)
    registers[12] = _u16(INTERNAL_PULSE_FILL_FACTOR)
    registers[13] = _u16(INTERNAL_PULSE_FREQUENCY_HZ)
    registers[14] = _pack_bytes(RAMP_DOWN_TIME_S, RAMP_UP_TIME_S)
    registers[15] = _pack_bytes(KSV_SKIP_TIME_S, KSV_WORK_TIME_S)
    registers[16] = _u16(KSV_REFLECTED_POWER_THRESHOLD_W)
    registers[17] = _u16(PHASE_STEP_CODE)
    registers[18] = _u16(OPERATING_FREQUENCY_X10_KHZ)
    registers[19] = _u16(ARC_SAFE_POWER_W)
    registers[20] = _u16(ARC_POWER_DECREMENT_W)
    registers[21] = _u16(ARC_SUPPRESSION_TIME_US)
    registers[22] = _pack_bytes(ARC_DELAY_AFTER_SETPOINT_MS, ARC_DELAY_ON_START_X10_S)
    registers[23] = _pack_bytes(CURRENT_RAMP_DOWN_TIME_S, CURRENT_RAMP_UP_TIME_S)
    registers[24] = _pack_bytes(CURRENT_KSV_SKIP_TIME_S, CURRENT_KSV_WORK_TIME_S)

    # Регистры 25...32 — измеренные мощности и напряжение внешнего зонда.
    registers[25] = _u16(params.incident_power_peak(t))
    registers[26] = _u16(params.incident_power_average(t))
    registers[27] = _u16(params.load_power_peak(t))
    registers[28] = _u16(params.load_power_average(t))
    registers[29] = _u16(params.reflected_power_peak(t))
    registers[30] = _u16(params.reflected_power_average(t))
    registers[31] = _u16(params.external_probe_voltage_peak(t))
    registers[32] = _u16(params.external_probe_voltage_average(t))

    # Регистры 33...40: старший байт — первый параметр в описании,
    # младший байт — второй параметр.
    registers[33] = _pack_bytes(
        params.module_1_supply_voltage(t), params.module_1_temperature(t)
    )
    registers[34] = _pack_bytes(
        params.module_1_drain_voltage(t), params.module_1_rf_voltage(t)
    )
    registers[35] = _pack_bytes(
        params.module_2_supply_voltage(t), params.module_2_temperature(t)
    )
    registers[36] = _pack_bytes(
        params.module_2_drain_voltage(t), params.module_2_rf_voltage(t)
    )
    registers[37] = _pack_bytes(
        params.module_3_supply_voltage(t), params.module_3_temperature(t)
    )
    registers[38] = _pack_bytes(
        params.module_3_drain_voltage(t), params.module_3_rf_voltage(t)
    )
    registers[39] = _pack_bytes(
        params.module_4_supply_voltage(t), params.module_4_temperature(t)
    )
    registers[40] = _pack_bytes(
        params.module_4_drain_voltage(t), params.module_4_rf_voltage(t)
    )

    return registers


def _exception(slave_id: int, function_code: int, exception_code: int) -> bytes:
    return append_crc(bytes([slave_id, function_code | 0x80, exception_code]))


def handle_request(request: bytes, t: float | None = None) -> bytes | None:
    """Обрабатывает один Modbus RTU-запрос; возвращает ответ или None."""
    if len(request) < 4:
        return None
    if request[0] != SLAVE_ID:
        return None
    if not is_valid_crc(request):
        print("[!] Получен запрос с неверной CRC.")
        return None

    function_code = request[1]
    if t is None:
        t = time.monotonic() - START_TIME

    # 0x11 — Read Slave ID. Сохраняется формат исходного имитатора:
    # 36 байт данных: Run Indicator Status, 0x00, 34 байта MODEL_ASCII.
    if function_code == 0x11:
        if len(request) != 4:
            return None
        run_indicator = 0xFF if (build_holding_registers(t)[0] & 0x0002) else 0x00
        response = bytes([SLAVE_ID, 0x11, 0x24, run_indicator, 0x00]) + MODEL_ASCII
        return append_crc(response)

    # 0x03 — чтение holding-регистров 0...40.
    if function_code == 0x03:
        if len(request) != 8:
            return None

        start_address = int.from_bytes(request[2:4], byteorder="big")
        quantity = int.from_bytes(request[4:6], byteorder="big")

        if quantity < 1 or quantity > 41:
            return _exception(SLAVE_ID, function_code, 0x03)  # Illegal Data Value
        if start_address + quantity > 41:
            return _exception(SLAVE_ID, function_code, 0x02)  # Illegal Data Address

        registers = build_holding_registers(t)
        payload = b"".join(value.to_bytes(2, byteorder="big") for value in registers[start_address:start_address + quantity])
        response = bytes([SLAVE_ID, 0x03, len(payload)]) + payload
        return append_crc(response)

    # Неизвестная функция — Illegal Function.
    return _exception(SLAVE_ID, function_code, 0x01)


def read_request_frame(ser) -> bytes | None:
    """Читает один запрос RTU фиксированной/известной длины из pySerial."""
    first = ser.read(1)
    if not first:
        return None
    second = ser.read(1)
    if not second:
        return None

    function_code = second[0]
    expected_length = 4 if function_code == 0x11 else 8
    remainder = ser.read(expected_length - 2)
    if len(remainder) != expected_length - 2:
        return None
    return first + second + remainder


def main() -> None:
    if not 1 <= SLAVE_ID <= 247:
        raise ValueError("SLAVE_ID должен находиться в диапазоне 1–247.")

    try:
        import serial
    except ImportError as error:
        raise SystemExit("Не установлен pyserial. Выполните: python -m pip install pyserial") from error

    try:
        with serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=TIMEOUT,
        ) as ser:
            print("Имитатор ВЧ-генератора GLine запущен.")
            print(f"Порт: {PORT}; скорость: {BAUDRATE}; Slave ID: {SLAVE_ID}")
            print("Чтение регистров 0...40 (0x03), идентификация (0x11). Ctrl+C — выход.")

            while True:
                request = read_request_frame(ser)
                if request is None:
                    continue

                response = handle_request(request)
                if response is not None:
                    ser.write(response)
                    ser.flush()
                    print(f"RX: {request.hex(' ').upper()} | TX: {response.hex(' ').upper()}")

    except serial.SerialException as error:
        print(f"Ошибка последовательного порта: {error}")
    except KeyboardInterrupt:
        print("\nИмитатор остановлен.")


if __name__ == "__main__":
    main()
