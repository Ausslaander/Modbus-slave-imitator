"""Законы изменения измеряемых параметров имитатора ВЧ-генератора GLine.

Все функции принимают время t в секундах от момента запуска имитатора.
Чтобы задать постоянное значение, верните из функции число.
Чтобы задать синусоидальный закон, используйте sinusoid().

Пример постоянного значения:
    return 600.0

Пример синусоидального закона:
    return sinusoid(t, mean=600.0, amplitude=25.0, period=20.0)
"""

from __future__ import annotations

import math


def constant(value: float) -> float:
    """Возвращает постоянное значение (удобно использовать в функциях ниже)."""
    return float(value)


def sinusoid(
    t: float,
    *,
    mean: float,
    amplitude: float,
    period: float,
    phase: float = 0.0,
) -> float:
    """Синусоидальный закон: mean + amplitude * sin(2*pi*t/period + phase).

    period задаётся в секундах, phase — в радианах.
    """
    if period <= 0:
        raise ValueError("Период синусоиды должен быть больше нуля.")
    return mean + amplitude * math.sin(2.0 * math.pi * t / period + phase)


# ---------------------------------------------------------------------------
# Мощность. Единицы измерения — Вт.
# ---------------------------------------------------------------------------

def incident_power_peak(t: float) -> float:
    """Измеренная падающая мощность, пиковая, Вт (регистр 25)."""
    return sinusoid(t, mean=620.0, amplitude=15.0, period=20.0)
    # Для постоянного значения: return constant(620.0)


def incident_power_average(t: float) -> float:
    """Измеренная падающая мощность, средняя, Вт (регистр 26)."""
    return sinusoid(t, mean=600.0, amplitude=10.0, period=20.0)
    # Для постоянного значения: return constant(600.0)


def load_power_peak(t: float) -> float:
    """Измеренная мощность в нагрузке, пиковая, Вт (регистр 27)."""
    return sinusoid(t, mean=575.0, amplitude=14.0, period=20.0, phase=0.2)
    # Для постоянного значения: return constant(575.0)


def load_power_average(t: float) -> float:
    """Измеренная мощность в нагрузке, средняя, Вт (регистр 28)."""
    return sinusoid(t, mean=565.0, amplitude=9.0, period=20.0, phase=0.2)
    # Для постоянного значения: return constant(565.0)


def reflected_power_peak(t: float) -> float:
    """Измеренная отражённая мощность, пиковая, Вт (регистр 29)."""
    return sinusoid(t, mean=45.0, amplitude=4.0, period=16.0)
    # Для постоянного значения: return constant(45.0)


def reflected_power_average(t: float) -> float:
    """Измеренная отражённая мощность, средняя, Вт (регистр 30)."""
    return sinusoid(t, mean=35.0, amplitude=3.0, period=16.0)
    # Для постоянного значения: return constant(35.0)


# ---------------------------------------------------------------------------
# Внешний зонд. Единицы измерения — В.
# ---------------------------------------------------------------------------

def external_probe_voltage_peak(t: float) -> float:
    """Измеренное напряжение внешнего зонда, пиковое, В (регистр 31)."""
    return sinusoid(t, mean=10.0, amplitude=0.5, period=25.0)
    # Для постоянного значения: return constant(10.0)


def external_probe_voltage_average(t: float) -> float:
    """Измеренное напряжение внешнего зонда, среднее, В (регистр 32)."""
    return sinusoid(t, mean=9.5, amplitude=0.3, period=25.0)
    # Для постоянного значения: return constant(9.5)


# ---------------------------------------------------------------------------
# Телеметрия силовых модулей. Значения передаются в младших/старших байтах
# регистров 33–40; для каждого значения используется диапазон 0...255.
# Единицы: температура — °C, напряжения — В.
# ---------------------------------------------------------------------------

def module_1_temperature(t: float) -> float:
    """Температура силового модуля №1, °C (младший байт регистра 33)."""
    return sinusoid(t, mean=38.0, amplitude=1.5, period=90.0)
    # Для постоянного значения: return constant(38.0)


def module_1_supply_voltage(t: float) -> float:
    """Напряжение питания модуля №1, В (старший байт регистра 33)."""
    return sinusoid(t, mean=48.0, amplitude=0.5, period=45.0)
    # Для постоянного значения: return constant(48.0)


def module_1_drain_voltage(t: float) -> float:
    """Напряжение на стоках транзисторов модуля №1, В (старший байт регистра 34)."""
    return sinusoid(t, mean=24.0, amplitude=0.3, period=50.0)
    # Для постоянного значения: return constant(24.0)


def module_1_rf_voltage(t: float) -> float:
    """Напряжение ВЧ модуля №1, В (младший байт регистра 34)."""
    return sinusoid(t, mean=12.0, amplitude=0.4, period=35.0)
    # Для постоянного значения: return constant(12.0)


def module_2_temperature(t: float) -> float:
    """Температура силового модуля №2, °C (младший байт регистра 35)."""
    return sinusoid(t, mean=39.0, amplitude=1.5, period=95.0, phase=0.4)
    # Для постоянного значения: return constant(39.0)


def module_2_supply_voltage(t: float) -> float:
    """Напряжение питания модуля №2, В (старший байт регистра 35)."""
    return sinusoid(t, mean=48.0, amplitude=0.5, period=47.0, phase=0.3)
    # Для постоянного значения: return constant(48.0)


def module_2_drain_voltage(t: float) -> float:
    """Напряжение на стоках транзисторов модуля №2, В (старший байт регистра 36)."""
    return sinusoid(t, mean=24.0, amplitude=0.3, period=52.0, phase=0.2)
    # Для постоянного значения: return constant(24.0)


def module_2_rf_voltage(t: float) -> float:
    """Напряжение ВЧ модуля №2, В (младший байт регистра 36)."""
    return sinusoid(t, mean=12.0, amplitude=0.4, period=37.0, phase=0.5)
    # Для постоянного значения: return constant(12.0)


def module_3_temperature(t: float) -> float:
    """Температура силового модуля №3, °C (младший байт регистра 37)."""
    return sinusoid(t, mean=40.0, amplitude=1.5, period=100.0, phase=0.8)
    # Для постоянного значения: return constant(40.0)


def module_3_supply_voltage(t: float) -> float:
    """Напряжение питания модуля №3, В (старший байт регистра 37)."""
    return sinusoid(t, mean=48.0, amplitude=0.5, period=49.0, phase=0.6)
    # Для постоянного значения: return constant(48.0)


def module_3_drain_voltage(t: float) -> float:
    """Напряжение на стоках транзисторов модуля №3, В (старший байт регистра 38)."""
    return sinusoid(t, mean=24.0, amplitude=0.3, period=54.0, phase=0.4)
    # Для постоянного значения: return constant(24.0)


def module_3_rf_voltage(t: float) -> float:
    """Напряжение ВЧ модуля №3, В (младший байт регистра 38)."""
    return sinusoid(t, mean=12.0, amplitude=0.4, period=39.0, phase=0.7)
    # Для постоянного значения: return constant(12.0)


def module_4_temperature(t: float) -> float:
    """Температура силового модуля №4, °C (младший байт регистра 39)."""
    return sinusoid(t, mean=41.0, amplitude=1.5, period=105.0, phase=1.1)
    # Для постоянного значения: return constant(41.0)


def module_4_supply_voltage(t: float) -> float:
    """Напряжение питания модуля №4, В (старший байт регистра 39)."""
    return sinusoid(t, mean=48.0, amplitude=0.5, period=51.0, phase=0.9)
    # Для постоянного значения: return constant(48.0)


def module_4_drain_voltage(t: float) -> float:
    """Напряжение на стоках транзисторов модуля №4, В (старший байт регистра 40)."""
    return sinusoid(t, mean=24.0, amplitude=0.3, period=56.0, phase=0.6)
    # Для постоянного значения: return constant(24.0)


def module_4_rf_voltage(t: float) -> float:
    """Напряжение ВЧ модуля №4, В (младший байт регистра 40)."""
    return sinusoid(t, mean=12.0, amplitude=0.4, period=41.0, phase=0.9)
    # Для постоянного значения: return constant(12.0)
