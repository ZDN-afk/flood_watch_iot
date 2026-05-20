"""
sensors/sensor_factory.py
═══════════════════════════════════════════════════════════════════
DESIGN PATTERN #1 — FACTORY METHOD
═══════════════════════════════════════════════════════════════════

Masalah yang diselesaikan:
  Sistem memiliki banyak jenis sensor dengan parameter inisialisasi
  yang berbeda-beda. Jika kode klien (main.py) langsung memanggil
  konstruktor masing-masing sensor (WaterLevelSensor(...), RainfallSensor(...)),
  kode menjadi tightly coupled dan sulit diperluas.

Solusi Factory Method:
  SensorFactory menyediakan satu titik masuk tunggal (create_sensor())
  yang menerima konfigurasi berupa dict dan mengembalikan objek sensor
  yang tepat tanpa klien perlu tahu kelas konkretnya.

Manfaat:
  - Open/Closed Principle: tambah jenis sensor baru cukup dengan
    mendaftarkannya di registry, tanpa ubah kode klien.
  - Single Responsibility: logika pembuatan objek terpusat di satu tempat.
"""

from typing import Dict, Any
from sensors.base_sensor import BaseSensor
from sensors.concrete_sensors import WaterLevelSensor, RainfallSensor, FlowSpeedSensor
from models.sensor_data import SensorType


class SensorFactory:
    """
    Factory class yang memproduksi objek sensor berdasarkan konfigurasi.

    Mendukung konfigurasi berbasis dict sehingga bisa dimuat dari
    file JSON / database konfigurasi di production.
    """

    # Registry: mapping tipe sensor → kelas konkret
    _SENSOR_REGISTRY: Dict[SensorType, type] = {
        SensorType.WATER_LEVEL: WaterLevelSensor,
        SensorType.RAINFALL:    RainfallSensor,
        SensorType.FLOW_SPEED:  FlowSpeedSensor,
    }

    @classmethod
    def create_sensor(cls, config: Dict[str, Any]) -> BaseSensor:
        """
        Membuat dan mengembalikan instance sensor berdasarkan konfigurasi.

        Args:
            config: dict dengan field wajib:
                - "type"      : SensorType (enum)
                - "sensor_id" : str, identifikasi unik sensor
                - "location"  : str, nama lokasi pemasangan

                Field opsional per jenis sensor:
                - "base_level"     : float (WaterLevelSensor)
                - "rain_intensity" : float (RainfallSensor)
                - "base_speed"     : float (FlowSpeedSensor)

        Returns:
            Instance dari subclass BaseSensor yang sesuai.

        Raises:
            ValueError: jika tipe sensor tidak dikenali.
        """
        sensor_type: SensorType = config.get("type")
        sensor_id:   str        = config.get("sensor_id")
        location:    str        = config.get("location")

        if sensor_type not in cls._SENSOR_REGISTRY:
            raise ValueError(
                f"[SensorFactory] ❌ Tipe sensor tidak dikenal: {sensor_type}. "
                f"Tipe yang tersedia: {list(cls._SENSOR_REGISTRY.keys())}"
            )

        SensorClass = cls._SENSOR_REGISTRY[sensor_type]
        print(f"[SensorFactory] ✅ Membuat {SensorClass.__name__} "
              f"(id={sensor_id}, lokasi={location})")

        # Setiap kelas konkret menerima parameter berbeda — Factory yang mengurus ini
        if sensor_type == SensorType.WATER_LEVEL:
            return SensorClass(
                sensor_id  = sensor_id,
                location   = location,
                base_level = config.get("base_level", 1.2),
            )
        elif sensor_type == SensorType.RAINFALL:
            return SensorClass(
                sensor_id      = sensor_id,
                location       = location,
                rain_intensity = config.get("rain_intensity", 20.0),
            )
        elif sensor_type == SensorType.FLOW_SPEED:
            return SensorClass(
                sensor_id  = sensor_id,
                location   = location,
                base_speed = config.get("base_speed", 0.8),
            )

    @classmethod
    def create_sensor_cluster(cls, configs: list) -> list:
        """
        Membuat sekelompok sensor sekaligus dari daftar konfigurasi.
        Berguna untuk inisialisasi seluruh sensor di satu pintu air.
        """
        sensors = []
        for cfg in configs:
            sensors.append(cls.create_sensor(cfg))
        return sensors

    @classmethod
    def register_sensor_type(cls, sensor_type: SensorType, sensor_class: type):
        """
        Mendaftarkan jenis sensor baru ke dalam registry.
        Implementasi Open/Closed Principle — tidak perlu modifikasi kelas Factory.
        """
        cls._SENSOR_REGISTRY[sensor_type] = sensor_class
        print(f"[SensorFactory] 📋 Sensor baru terdaftar: {sensor_type.value} → {sensor_class.__name__}")
