"""
decorators/data_decorators.py
═══════════════════════════════════════════════════════════════════
DESIGN PATTERN #2 — DECORATOR PATTERN
═══════════════════════════════════════════════════════════════════

Masalah yang diselesaikan:
  Data mentah dari sensor sering kotor: ada lonjakan anomali (noise)
  akibat gangguan fisik (burung, sampah, interferensi elektromagnetik).
  Jika logika filtering di-hardcode langsung ke sensor atau ke processor,
  kita melanggar Single Responsibility Principle dan susah dikombinasikan.

Solusi Decorator:
  Setiap lapisan pemrosesan dibungkus sebagai Decorator yang membungkus
  objek sensor asli. Dekorator bisa ditumpuk (chained) secara fleksibel:

      raw_sensor
      → AverageSmoothingDecorator(raw_sensor)
      → NoiseFilterDecorator(AverageSmoothingDecorator(raw_sensor))

  Urutan bisa diubah tanpa mengubah kelas mana pun.

Komponen:
  - DataProcessorBase    : interface / abstract component
  - SensorReadingAdapter : adapter agar BaseSensor bisa dipakai sebagai DataProcessorBase
  - NoiseFilterDecorator : membuang lonjakan anomali (IQR-based spike detection)
  - AverageSmoothingDecorator : merata-rata N bacaan terakhir (sliding window)
"""

from abc import ABC, abstractmethod
from collections import deque
from typing import Optional
from models.sensor_data import SensorReading
from sensors.base_sensor import BaseSensor


# ─────────────────────────────────────────────────────────────
# ABSTRACT COMPONENT
# ─────────────────────────────────────────────────────────────

class DataProcessorBase(ABC):
    """
    Interface yang harus diimplementasikan oleh sensor asli maupun dekorator.
    Memastikan semua lapisan memiliki kontrak yang sama: bisa di-read().
    """

    @abstractmethod
    def read(self) -> SensorReading:
        pass

    @property
    @abstractmethod
    def location(self) -> str:
        pass

    @property
    @abstractmethod
    def sensor_id(self) -> str:
        pass


# ─────────────────────────────────────────────────────────────
# CONCRETE COMPONENT (Adapter: BaseSensor → DataProcessorBase)
# ─────────────────────────────────────────────────────────────

class SensorReadingAdapter(DataProcessorBase):
    """
    Membungkus BaseSensor agar kompatibel dengan interface DataProcessorBase.
    Ini adalah titik masuk terbawah dari rantai dekorator.
    """

    def __init__(self, sensor: BaseSensor):
        self._sensor = sensor

    def read(self) -> SensorReading:
        return self._sensor.read()

    @property
    def location(self) -> str:
        return self._sensor.location

    @property
    def sensor_id(self) -> str:
        return self._sensor.sensor_id


# ─────────────────────────────────────────────────────────────
# BASE DECORATOR
# ─────────────────────────────────────────────────────────────

class BaseDecorator(DataProcessorBase):
    """
    Abstract base untuk semua dekorator.
    Menyimpan referensi ke komponen yang dibungkus (wrapped).
    """

    def __init__(self, wrapped: DataProcessorBase):
        self._wrapped = wrapped

    @property
    def location(self) -> str:
        return self._wrapped.location

    @property
    def sensor_id(self) -> str:
        return self._wrapped.sensor_id

    def read(self) -> SensorReading:
        return self._wrapped.read()


# ─────────────────────────────────────────────────────────────
# CONCRETE DECORATOR 1: NOISE FILTER
# ─────────────────────────────────────────────────────────────

class NoiseFilterDecorator(BaseDecorator):
    """
    Decorator yang mendeteksi dan menandai bacaan anomali.

    Algoritma:
      Menyimpan N bacaan valid terakhir sebagai referensi baseline.
      Jika bacaan baru menyimpang lebih dari (THRESHOLD × baseline_mean),
      data ditandai sebagai anomali dan diganti dengan nilai terakhir yang valid.

    Contoh:
      Baseline: [1.8, 1.9, 2.0, 1.85, 1.95] → mean ≈ 1.91 m
      Bacaan baru: 10.5 m
      10.5 > 1.91 × 3.0 → ANOMALI → gunakan 1.95 (nilai valid terakhir)

    Ini mencegah False Alarm sirine berbahaya akibat gangguan fisik sensor.
    """

    DEFAULT_SPIKE_THRESHOLD  = 3.0   # kelipatan mean baseline yang dianggap spike
    BASELINE_WINDOW_SIZE     = 5     # jumlah bacaan valid untuk membangun baseline

    def __init__(self, wrapped: DataProcessorBase, spike_threshold: float = None):
        super().__init__(wrapped)
        self._threshold     = spike_threshold or self.DEFAULT_SPIKE_THRESHOLD
        self._baseline      : deque = deque(maxlen=self.BASELINE_WINDOW_SIZE)
        self._last_valid    : Optional[float] = None
        self._filter_count  = 0

    def read(self) -> SensorReading:
        reading = self._wrapped.read()
        value   = reading.raw_value

        # Belum punya baseline — terima saja nilai apapun untuk membangun window
        if len(self._baseline) < 2:
            self._baseline.append(value)
            self._last_valid = value
            reading.processed_value = value
            return reading

        baseline_mean = sum(self._baseline) / len(self._baseline)
        upper_limit   = baseline_mean * self._threshold

        # Deteksi spike — nilai yang jauh melebihi baseline dianggap anomali
        if value > upper_limit and baseline_mean > 0:
            reading.is_anomaly      = True
            reading.processed_value = self._last_valid  # ganti dengan nilai valid terakhir
            self._filter_count     += 1
            print(
                f"  [NoiseFilter] 🚫 ANOMALI DIFILTER @ {reading.location} | "
                f"Raw: {value:.2f} {reading.unit} >> "
                f"Diganti: {self._last_valid:.2f} {reading.unit} "
                f"(baseline mean: {baseline_mean:.2f}, batas: {upper_limit:.2f})"
            )
        else:
            reading.processed_value = value
            self._baseline.append(value)
            self._last_valid = value

        return reading

    @property
    def filter_count(self) -> int:
        return self._filter_count


# ─────────────────────────────────────────────────────────────
# CONCRETE DECORATOR 2: AVERAGE SMOOTHING
# ─────────────────────────────────────────────────────────────

class AverageSmoothingDecorator(BaseDecorator):
    """
    Decorator yang menghaluskan fluktuasi data dengan moving average.

    Algoritma:
      Menyimpan N bacaan terakhir dalam sliding window.
      Mengembalikan rata-rata window sebagai processed_value.
      Mengurangi jitter sensor akibat turbulensi air, angin kecil, dll.

    Decorator ini biasanya dipasang SETELAH NoiseFilterDecorator
    sehingga moving average tidak terkontaminasi nilai anomali.
    """

    DEFAULT_WINDOW_SIZE = 5

    def __init__(self, wrapped: DataProcessorBase, window_size: int = None):
        super().__init__(wrapped)
        self._window_size = window_size or self.DEFAULT_WINDOW_SIZE
        self._window: deque = deque(maxlen=self._window_size)

    def read(self) -> SensorReading:
        reading = self._wrapped.read()

        # Gunakan processed_value jika sudah ada (dari dekorator sebelumnya)
        value_to_smooth = (
            reading.processed_value
            if reading.processed_value is not None
            else reading.raw_value
        )

        self._window.append(value_to_smooth)
        smoothed = round(sum(self._window) / len(self._window), 3)

        reading.processed_value = smoothed
        return reading
