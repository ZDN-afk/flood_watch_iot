"""
sensors/base_sensor.py
Abstract base class untuk semua jenis sensor dalam sistem FloodWatch.
"""

from abc import ABC, abstractmethod
from models.sensor_data import SensorReading, SensorType
import random
import time


class BaseSensor(ABC):
    """
    Interface umum untuk semua sensor IoT.
    Setiap subclass mengimplementasikan cara menghasilkan data bacaan sendiri.
    Ini juga merupakan Component dalam Decorator Pattern.
    """

    def __init__(self, sensor_id: str, location: str):
        self.sensor_id  = sensor_id
        self.location   = location
        self._reading_count = 0

    @property
    @abstractmethod
    def sensor_type(self) -> SensorType:
        """Mengembalikan tipe sensor."""
        pass

    @property
    @abstractmethod
    def unit(self) -> str:
        """Satuan pengukuran sensor."""
        pass

    @abstractmethod
    def _generate_raw_value(self) -> float:
        """Menghasilkan nilai mentah dari sensor (termasuk kemungkinan noise)."""
        pass

    def read(self) -> SensorReading:
        """
        Membaca data dari sensor dan mengembalikan SensorReading.
        Mensimulasikan delay pembacaan hardware (5ms).
        """
        time.sleep(0.005)   # simulasi latensi hardware sensor
        self._reading_count += 1
        raw = self._generate_raw_value()

        return SensorReading(
            sensor_id   = self.sensor_id,
            sensor_type = self.sensor_type,
            location    = self.location,
            raw_value   = raw,
            unit        = self.unit,
        )

    def __str__(self) -> str:
        return f"Sensor[{self.sensor_id}|{self.sensor_type.value}|{self.location}]"
