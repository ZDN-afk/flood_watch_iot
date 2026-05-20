"""
models/sensor_data.py
Data classes dan enums yang mewakili entitas inti sistem FloodWatch IoT.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AlertLevel(Enum):
    """Level siaga banjir berdasarkan ketinggian air."""
    NORMAL  = "NORMAL"
    SIAGA_3 = "SIAGA 3"
    SIAGA_2 = "SIAGA 2"
    SIAGA_1 = "SIAGA 1 (BAHAYA)"


class SensorType(Enum):
    """Jenis sensor yang didukung sistem."""
    WATER_LEVEL = "WATER_LEVEL"   # satuan: meter
    RAINFALL    = "RAINFALL"       # satuan: mm/jam
    FLOW_SPEED  = "FLOW_SPEED"     # satuan: m/s


@dataclass
class SensorReading:
    """
    Merepresentasikan satu bacaan data dari sebuah sensor.
    Berisi nilai mentah (raw) dan nilai setelah diproses (processed).
    """
    sensor_id:       str
    sensor_type:     SensorType
    location:        str
    raw_value:       float
    unit:            str
    timestamp:       datetime = field(default_factory=datetime.now)
    processed_value: Optional[float] = None
    is_anomaly:      bool = False

    def __str__(self) -> str:
        processed_str = (
            f"{self.processed_value:.2f}" if self.processed_value is not None else "N/A"
        )
        anomaly_tag = " ⚠️  [ANOMALI TERDETEKSI – DIFILTER]" if self.is_anomaly else ""
        return (
            f"[{self.timestamp.strftime('%H:%M:%S')}] "
            f"Sensor {self.sensor_id} @ {self.location} | "
            f"Tipe: {self.sensor_type.value:12s} | "
            f"Raw: {self.raw_value:6.2f} {self.unit} | "
            f"Processed: {processed_str:6s} {self.unit}"
            f"{anomaly_tag}"
        )


@dataclass
class FloodEvent:
    """
    Event yang dipublikasikan ke semua Observer ketika level siaga berubah.
    """
    location:       str
    alert_level:    AlertLevel
    trigger_value:  float
    unit:           str
    sensor_type:    SensorType
    timestamp:      datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return (
            f"[{self.timestamp.strftime('%H:%M:%S')}] "
            f"🚨 FLOOD EVENT @ {self.location} — "
            f"Level: {self.alert_level.value:20s} | "
            f"Trigger: {self.trigger_value:.2f} {self.unit}"
        )
