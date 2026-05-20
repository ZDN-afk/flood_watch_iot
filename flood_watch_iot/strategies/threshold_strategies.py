"""
strategies/threshold_strategies.py
═══════════════════════════════════════════════════════════════════
DESIGN PATTERN #3 — STRATEGY PATTERN
═══════════════════════════════════════════════════════════════════

Masalah yang diselesaikan:
  Setiap pintu air memiliki karakteristik topologi sungai yang berbeda.
  Pintu Air Manggarai (di hilir, dekat laut) memiliki batas aman lebih rendah
  daripada Katulampa (di hulu, pegunungan). Jika batas threshold di-hardcode
  dalam satu kelas, kita tidak bisa mengganti aturan secara dinamis
  (misal: setelah perluasan kanal, batas aman berubah).

Solusi Strategy:
  Buat interface ThresholdStrategy dengan method evaluate(value).
  Setiap pintu air punya Strategy-nya sendiri yang bisa di-swap
  secara runtime tanpa mengubah kelas DataProcessor.

Trade-off:
  Menambah jumlah kelas (satu per konfigurasi pintu air),
  tapi mendapat fleksibilitas penuh tanpa conditional if/else yang panjang.
"""

from abc import ABC, abstractmethod
from models.sensor_data import AlertLevel, SensorType


# ─────────────────────────────────────────────────────────────
# STRATEGY INTERFACE
# ─────────────────────────────────────────────────────────────

class ThresholdStrategy(ABC):
    """
    Interface untuk menentukan level siaga berdasarkan nilai sensor.
    Setiap implementasi mewakili aturan threshold satu pintu air / area.
    """

    @abstractmethod
    def evaluate(self, value: float, sensor_type: SensorType) -> AlertLevel:
        """
        Mengevaluasi nilai sensor dan mengembalikan level siaga.

        Args:
            value       : nilai processed (sudah difilter dan dihaluskan)
            sensor_type : tipe sensor untuk memilih threshold yang tepat

        Returns:
            AlertLevel enum
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nama pintu air / area yang ditangani strategy ini."""
        pass

    def describe(self) -> str:
        return f"[Strategy: {self.name}]"


# ─────────────────────────────────────────────────────────────
# CONCRETE STRATEGY 1: PINTU AIR MANGGARAI
# ─────────────────────────────────────────────────────────────

class ManggaraiThresholdStrategy(ThresholdStrategy):
    """
    Threshold untuk Pintu Air Manggarai (Jakarta Selatan).
    Berlokasi di hilir — kapasitas kanal lebih kecil, batas aman lebih ketat.

    Threshold Ketinggian Air (meter):
      < 8.0  → NORMAL
      8.0–9.0 → SIAGA 3
      9.0–9.5 → SIAGA 2
      ≥ 9.5  → SIAGA 1

    Threshold Curah Hujan (mm/jam):
      < 50   → NORMAL
      50–80  → SIAGA 3
      80–100 → SIAGA 2
      ≥ 100  → SIAGA 1
    """

    @property
    def name(self) -> str:
        return "Pintu Air Manggarai"

    def evaluate(self, value: float, sensor_type: SensorType) -> AlertLevel:
        if sensor_type == SensorType.WATER_LEVEL:
            return self._eval_water_level(value)
        elif sensor_type == SensorType.RAINFALL:
            return self._eval_rainfall(value)
        elif sensor_type == SensorType.FLOW_SPEED:
            return self._eval_flow_speed(value)
        return AlertLevel.NORMAL

    def _eval_water_level(self, v: float) -> AlertLevel:
        if v >= 9.5:  return AlertLevel.SIAGA_1
        if v >= 9.0:  return AlertLevel.SIAGA_2
        if v >= 8.0:  return AlertLevel.SIAGA_3
        return AlertLevel.NORMAL

    def _eval_rainfall(self, v: float) -> AlertLevel:
        if v >= 100: return AlertLevel.SIAGA_1
        if v >= 80:  return AlertLevel.SIAGA_2
        if v >= 50:  return AlertLevel.SIAGA_3
        return AlertLevel.NORMAL

    def _eval_flow_speed(self, v: float) -> AlertLevel:
        if v >= 3.5:  return AlertLevel.SIAGA_1
        if v >= 2.5:  return AlertLevel.SIAGA_2
        if v >= 1.5:  return AlertLevel.SIAGA_3
        return AlertLevel.NORMAL


# ─────────────────────────────────────────────────────────────
# CONCRETE STRATEGY 2: PINTU AIR KATULAMPA
# ─────────────────────────────────────────────────────────────

class KatulampaThresholdStrategy(ThresholdStrategy):
    """
    Threshold untuk Bendung Katulampa (Bogor, hulu Sungai Ciliwung).
    Berlokasi di hulu pegunungan — debit air lebih besar, sistem peringatan
    lebih dini diperlukan dengan threshold yang lebih rendah.

    Threshold Ketinggian Air (meter):
      < 1.5  → NORMAL
      1.5–2.0 → SIAGA 3
      2.0–2.5 → SIAGA 2
      ≥ 2.5  → SIAGA 1

    Threshold Curah Hujan (mm/jam):
      < 30   → NORMAL
      30–60  → SIAGA 3
      60–90  → SIAGA 2
      ≥ 90   → SIAGA 1
    """

    @property
    def name(self) -> str:
        return "Bendung Katulampa"

    def evaluate(self, value: float, sensor_type: SensorType) -> AlertLevel:
        if sensor_type == SensorType.WATER_LEVEL:
            return self._eval_water_level(value)
        elif sensor_type == SensorType.RAINFALL:
            return self._eval_rainfall(value)
        elif sensor_type == SensorType.FLOW_SPEED:
            return self._eval_flow_speed(value)
        return AlertLevel.NORMAL

    def _eval_water_level(self, v: float) -> AlertLevel:
        if v >= 2.5:  return AlertLevel.SIAGA_1
        if v >= 2.0:  return AlertLevel.SIAGA_2
        if v >= 1.5:  return AlertLevel.SIAGA_3
        return AlertLevel.NORMAL

    def _eval_rainfall(self, v: float) -> AlertLevel:
        if v >= 90:  return AlertLevel.SIAGA_1
        if v >= 60:  return AlertLevel.SIAGA_2
        if v >= 30:  return AlertLevel.SIAGA_3
        return AlertLevel.NORMAL

    def _eval_flow_speed(self, v: float) -> AlertLevel:
        if v >= 3.0:  return AlertLevel.SIAGA_1
        if v >= 2.0:  return AlertLevel.SIAGA_2
        if v >= 1.0:  return AlertLevel.SIAGA_3
        return AlertLevel.NORMAL


# ─────────────────────────────────────────────────────────────
# CONCRETE STRATEGY 3: PINTU AIR DEPOK (untuk demo strategy swap)
# ─────────────────────────────────────────────────────────────

class DepokThresholdStrategy(ThresholdStrategy):
    """
    Threshold untuk Pintu Air Depok (tengah aliran Ciliwung).
    Digunakan untuk mendemonstrasikan dynamic strategy swap di runtime.
    """

    @property
    def name(self) -> str:
        return "Pintu Air Depok"

    def evaluate(self, value: float, sensor_type: SensorType) -> AlertLevel:
        if sensor_type == SensorType.WATER_LEVEL:
            if value >= 4.5:  return AlertLevel.SIAGA_1
            if value >= 3.5:  return AlertLevel.SIAGA_2
            if value >= 2.5:  return AlertLevel.SIAGA_3
        elif sensor_type == SensorType.RAINFALL:
            if value >= 95:   return AlertLevel.SIAGA_1
            if value >= 70:   return AlertLevel.SIAGA_2
            if value >= 40:   return AlertLevel.SIAGA_3
        return AlertLevel.NORMAL
