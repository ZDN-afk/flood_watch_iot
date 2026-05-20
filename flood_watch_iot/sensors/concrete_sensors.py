"""
sensors/concrete_sensors.py
Implementasi konkret untuk tiga jenis sensor:
  - WaterLevelSensor  (ketinggian air, satuan: meter)
  - RainfallSensor    (curah hujan, satuan: mm/jam)
  - FlowSpeedSensor   (kecepatan arus, satuan: m/s)

Setiap sensor mensimulasikan:
  - Data normal sesuai kondisi cuaca
  - Lonjakan anomali acak (noise) untuk menguji NoiseFilterDecorator
"""

import random
from models.sensor_data import SensorType
from sensors.base_sensor import BaseSensor


class WaterLevelSensor(BaseSensor):
    """
    Sensor ketinggian air menggunakan gelombang ultrasonik.
    Baseline normal: 0.5–2.5 meter.
    Ada kemungkinan 15% membaca anomali (mis: burung hinggap → lonjakan 8–12 m).
    """

    ANOMALY_PROBABILITY = 0.15
    NORMAL_BASE         = 1.2    # meter
    NORMAL_NOISE_STD    = 0.10   # fluktuasi normal

    def __init__(self, sensor_id: str, location: str, base_level: float = None):
        super().__init__(sensor_id, location)
        self._base_level = base_level if base_level is not None else self.NORMAL_BASE

    @property
    def sensor_type(self) -> SensorType:
        return SensorType.WATER_LEVEL

    @property
    def unit(self) -> str:
        return "m"

    def _generate_raw_value(self) -> float:
        if random.random() < self.ANOMALY_PROBABILITY:
            # Simulasi burung hinggap / interferensi objek asing
            return round(random.uniform(8.0, 12.0), 2)
        # Data normal: base level + sedikit fluktuasi Gaussian
        value = self._base_level + random.gauss(0, self.NORMAL_NOISE_STD)
        # Simulasi kenaikan perlahan karena hujan (setiap 3 pembacaan naik 0.05m)
        if self._reading_count % 3 == 0:
            self._base_level = min(self._base_level + 0.05, 9.0)
        return round(max(0.1, value), 2)


class RainfallSensor(BaseSensor):
    """
    Sensor curah hujan menggunakan tipping-bucket rain gauge.
    Satuan: mm/jam. Nilai normal: 0–80 mm/jam.
    Ada kemungkinan 10% spike karena angin kencang memukul sensor.
    """

    ANOMALY_PROBABILITY = 0.10

    def __init__(self, sensor_id: str, location: str, rain_intensity: float = 20.0):
        super().__init__(sensor_id, location)
        self._rain_intensity = rain_intensity   # mm/jam

    @property
    def sensor_type(self) -> SensorType:
        return SensorType.RAINFALL

    @property
    def unit(self) -> str:
        return "mm/jam"

    def _generate_raw_value(self) -> float:
        if random.random() < self.ANOMALY_PROBABILITY:
            # Spike angin / getaran mekanis
            return round(random.uniform(200.0, 400.0), 2)
        value = self._rain_intensity + random.gauss(0, 5.0)
        # Intensitas naik secara gradual (simulasi badai yang datang)
        if self._reading_count % 4 == 0:
            self._rain_intensity = min(self._rain_intensity + 3.0, 150.0)
        return round(max(0.0, value), 2)


class FlowSpeedSensor(BaseSensor):
    """
    Sensor kecepatan arus menggunakan acoustic Doppler.
    Satuan: m/s. Nilai normal: 0.2–3.0 m/s.
    Ada kemungkinan 8% spike karena sampah melewati sensor.
    """

    ANOMALY_PROBABILITY = 0.08

    def __init__(self, sensor_id: str, location: str, base_speed: float = 0.8):
        super().__init__(sensor_id, location)
        self._base_speed = base_speed

    @property
    def sensor_type(self) -> SensorType:
        return SensorType.FLOW_SPEED

    @property
    def unit(self) -> str:
        return "m/s"

    def _generate_raw_value(self) -> float:
        if random.random() < self.ANOMALY_PROBABILITY:
            # Sampah / benda besar menghalangi sensor
            return round(random.uniform(15.0, 25.0), 2)
        value = self._base_speed + random.gauss(0, 0.15)
        if self._reading_count % 5 == 0:
            self._base_speed = min(self._base_speed + 0.08, 6.0)
        return round(max(0.0, value), 2)
