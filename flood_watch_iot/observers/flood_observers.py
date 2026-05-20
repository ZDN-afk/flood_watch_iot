"""
observers/flood_observers.py
═══════════════════════════════════════════════════════════════════
DESIGN PATTERN #1 — OBSERVER PATTERN
═══════════════════════════════════════════════════════════════════

Masalah yang diselesaikan:
  Dashboard Pemprov DKI dan sistem notifikasi warga sebelumnya
  menggunakan polling (loop terus-menerus query ke database) untuk
  mendapatkan update terbaru. Ini menyebabkan bottleneck karena
  database dibombardir query bahkan saat tidak ada perubahan.

Solusi Observer (Push Model):
  DataProcessingCenter (Subject/Observable) menyimpan daftar Observer.
  Ketika level siaga berubah, Subject otomatis MENDORONG (push) event
  ke semua Observer yang terdaftar — tanpa Observer perlu bertanya.

Manfaat:
  - Loose coupling: Subject tidak tahu detail implementasi Observer.
  - Scalable: menambah Observer baru (misal: SMS Gateway, BPBD API)
    cukup dengan register() tanpa ubah kode Subject.
  - Real-time: latensi notifikasi hanya dibatasi oleh kecepatan proses,
    bukan frekuensi polling.
"""

from abc import ABC, abstractmethod
from typing import List, Dict
from collections import defaultdict
from models.sensor_data import FloodEvent, AlertLevel
import time


# ─────────────────────────────────────────────────────────────
# OBSERVER INTERFACE
# ─────────────────────────────────────────────────────────────

class FloodObserver(ABC):
    """Interface untuk semua penerima notifikasi flood event."""

    @abstractmethod
    def on_flood_event(self, event: FloodEvent) -> None:
        """
        Dipanggil oleh Subject saat ada perubahan level siaga.

        Args:
            event: FloodEvent berisi lokasi, level, nilai trigger, dll.
        """
        pass

    @property
    @abstractmethod
    def observer_name(self) -> str:
        pass


# ─────────────────────────────────────────────────────────────
# SUBJECT (Observable)
# ─────────────────────────────────────────────────────────────

class FloodMonitoringSubject:
    """
    Pusat pengolahan data yang berfungsi sebagai Subject dalam Observer Pattern.

    Bertanggung jawab untuk:
    1. Menerima SensorReading yang sudah diproses
    2. Mengevaluasi level siaga menggunakan ThresholdStrategy yang aktif
    3. Jika level siaga berubah, membuat FloodEvent dan mempublikasikannya
       ke semua Observer yang terdaftar
    """

    def __init__(self, location: str, strategy):
        self._location        = location
        self._strategy        = strategy
        self._observers       : List[FloodObserver] = []
        self._current_level   : AlertLevel = AlertLevel.NORMAL
        self._event_history   : List[FloodEvent] = []   # Cold Path: arsip sederhana

    # ── Observer Management ──────────────────────────────────

    def register(self, observer: FloodObserver) -> None:
        self._observers.append(observer)
        print(f"  [Subject:{self._location}] ✅ Observer terdaftar: {observer.observer_name}")

    def unregister(self, observer: FloodObserver) -> None:
        self._observers.remove(observer)
        print(f"  [Subject:{self._location}] ❌ Observer dihapus: {observer.observer_name}")

    def _notify_all(self, event: FloodEvent) -> None:
        """Kirim (push) event ke semua observer yang terdaftar."""
        print(f"\n  [Subject:{self._location}] 📡 Mempublikasikan event ke "
              f"{len(self._observers)} observer...")
        for obs in self._observers:
            obs.on_flood_event(event)

    # ── Strategy Swap ────────────────────────────────────────

    def set_strategy(self, strategy) -> None:
        """
        Mengganti ThresholdStrategy secara runtime (Strategy Pattern).
        Berguna saat kondisi musim berubah atau topologi sungai diperbarui.
        """
        old_name = self._strategy.name
        self._strategy = strategy
        print(f"  [Subject:{self._location}] 🔄 Strategy ditukar: "
              f"{old_name} → {strategy.name}")

    # ── Core Processing ──────────────────────────────────────

    def process_reading(self, reading) -> AlertLevel:
        """
        Menerima satu SensorReading, mengevaluasi, dan jika level berubah
        memicu notifikasi ke semua Observer.

        Returns:
            AlertLevel hasil evaluasi saat ini.
        """
        value_to_check = (
            reading.processed_value
            if reading.processed_value is not None
            else reading.raw_value
        )

        new_level = self._strategy.evaluate(value_to_check, reading.sensor_type)

        # Hanya publish event jika level siaga BERUBAH (tidak spam notifikasi)
        if new_level != self._current_level:
            event = FloodEvent(
                location      = self._location,
                alert_level   = new_level,
                trigger_value = value_to_check,
                unit          = reading.unit,
                sensor_type   = reading.sensor_type,
            )
            self._current_level = new_level
            self._event_history.append(event)   # simpan ke Cold Path (in-memory)
            self._notify_all(event)

        return new_level

    @property
    def event_history(self) -> List[FloodEvent]:
        return list(self._event_history)

    @property
    def current_level(self) -> AlertLevel:
        return self._current_level


# ─────────────────────────────────────────────────────────────
# CONCRETE OBSERVER 1: DASHBOARD PEMPROV DKI
# ─────────────────────────────────────────────────────────────

class DashboardObserver(FloodObserver):
    """
    Mensimulasikan Dashboard monitoring Pemprov DKI Jakarta.
    Menampilkan update status di terminal (Hot Path — real-time display).
    Menyimpan riwayat event dalam memori (meniru state management dashboard).
    """

    LEVEL_COLORS = {
        AlertLevel.NORMAL:  "🟢",
        AlertLevel.SIAGA_3: "🟡",
        AlertLevel.SIAGA_2: "🟠",
        AlertLevel.SIAGA_1: "🔴",
    }

    def __init__(self):
        self._received_events: List[FloodEvent] = []

    @property
    def observer_name(self) -> str:
        return "Dashboard Pemprov DKI"

    def on_flood_event(self, event: FloodEvent) -> None:
        self._received_events.append(event)
        icon = self.LEVEL_COLORS.get(event.alert_level, "⚪")
        print(
            f"    [{self.observer_name}] {icon} UPDATE STATUS | "
            f"{event.location}: {event.alert_level.value} | "
            f"Nilai: {event.trigger_value:.2f} {event.unit}"
        )
        # Simulasi delay rendering dashboard (network + render time)
        time.sleep(0.02)

    def get_summary(self) -> Dict:
        """Menghasilkan ringkasan statistik untuk laporan akhir."""
        level_counts: Dict[str, int] = defaultdict(int)
        for e in self._received_events:
            level_counts[e.alert_level.value] += 1
        return {
            "observer":     self.observer_name,
            "total_events": len(self._received_events),
            "by_level":     dict(level_counts),
        }


# ─────────────────────────────────────────────────────────────
# CONCRETE OBSERVER 2: SISTEM NOTIFIKASI WARGA
# ─────────────────────────────────────────────────────────────

class AlertNotificationObserver(FloodObserver):
    """
    Mensimulasikan sistem notifikasi warga:
    - Level SIAGA 3 → Push notification ke aplikasi warga
    - Level SIAGA 2 → SMS broadcast ke area terdampak
    - Level SIAGA 1 → Sirine + SMS + notifikasi BPBD

    Menggunakan Mock Functions (tidak ada integrasi API nyata).
    """

    def __init__(self):
        self._notification_log: List[str] = []
        self._siren_activated = False

    @property
    def observer_name(self) -> str:
        return "Sistem Notifikasi Warga"

    def on_flood_event(self, event: FloodEvent) -> None:
        level = event.alert_level

        if level == AlertLevel.NORMAL:
            msg = self._mock_send_clear_notification(event)
        elif level == AlertLevel.SIAGA_3:
            msg = self._mock_send_push_notification(event)
        elif level == AlertLevel.SIAGA_2:
            msg = self._mock_send_sms_broadcast(event)
        elif level == AlertLevel.SIAGA_1:
            msg = self._mock_activate_emergency(event)

        self._notification_log.append(msg)
        print(f"    [{self.observer_name}] {msg}")
        time.sleep(0.03)  # simulasi latency pengiriman notifikasi

    def _mock_send_push_notification(self, event: FloodEvent) -> str:
        return (f"📱 [MOCK Push Notif] → Warga {event.location}: "
                f"Waspada! Level air meningkat ke {event.alert_level.value}")

    def _mock_send_sms_broadcast(self, event: FloodEvent) -> str:
        return (f"📨 [MOCK SMS Broadcast] → Area {event.location}: "
                f"PERHATIAN! {event.alert_level.value}. Siapkan evakuasi.")

    def _mock_activate_emergency(self, event: FloodEvent) -> str:
        self._siren_activated = True
        return (f"🚨 [MOCK SIRINE + SMS + BPBD API] → {event.location}: "
                f"BAHAYA! {event.alert_level.value} — Evakuasi segera!")

    def _mock_send_clear_notification(self, event: FloodEvent) -> str:
        if self._siren_activated:
            self._siren_activated = False
            return f"✅ [MOCK] Sirine dimatikan @ {event.location} — Status kembali NORMAL"
        return f"✅ [MOCK] Status {event.location}: NORMAL"

    @property
    def notification_log(self) -> List[str]:
        return list(self._notification_log)


# ─────────────────────────────────────────────────────────────
# CONCRETE OBSERVER 3: COLD PATH STORAGE (Data Warehouse)
# ─────────────────────────────────────────────────────────────

class ColdStorageObserver(FloodObserver):
    """
    Mensimulasikan Cold Path — penyimpanan ke data warehouse untuk analitik historis.
    Dalam simulasi ini, data disimpan di in-memory list (pengganti database).

    Di arsitektur nyata, ini akan menulis ke:
    - Apache Kafka → batch consumer → PostgreSQL / ClickHouse
    """

    def __init__(self):
        self._archive: List[FloodEvent] = []

    @property
    def observer_name(self) -> str:
        return "Cold Storage / Data Warehouse"

    def on_flood_event(self, event: FloodEvent) -> None:
        self._archive.append(event)
        # Simulasi delay batch write ke database (lebih lambat dari Hot Path)
        time.sleep(0.05)
        print(
            f"    [{self.observer_name}] 💾 Event diarsipkan "
            f"(total arsip: {len(self._archive)} record)"
        )

    def get_monthly_report(self) -> Dict:
        """Mengembalikan ringkasan data arsip (simulasi query analytics)."""
        by_location: Dict[str, int] = defaultdict(int)

        for e in self._archive:
            by_location[e.location] += 1

        return {
            "total_archived_events": len(self._archive),
            "events_per_location":   dict(by_location),
        }
