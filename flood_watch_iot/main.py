"""
main.py — FloodWatch IoT: Simulasi Sistem Peringatan Dini Banjir Jakarta
═══════════════════════════════════════════════════════════════════════════
Proof of Concept (PoC) — Proyek Akhir Arsitektur Perangkat Lunak

Design Patterns yang diimplementasikan:
  1. FACTORY METHOD  → sensors/sensor_factory.py
  2. DECORATOR       → decorators/data_decorators.py
  3. OBSERVER        → observers/flood_observers.py
  4. STRATEGY        → strategies/threshold_strategies.py  [BONUS]

Arsitektur simulasi:
  Sensor (produksi data) ──► Message Broker (buffer)
                              │
                              ▼
                     Stream Processor
                     (Decorator Pipeline)
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
               HOT PATH              COLD PATH
        (FloodMonitoringSubject)  (ColdStorageObserver)
                    │
              ┌─────┴──────┐
              ▼            ▼
         Dashboard    Notifikasi
          Observer      Observer
"""

import time
import sys
import random
from datetime import datetime

# ── Import semua modul ────────────────────────────────────────
from models.sensor_data import SensorType, AlertLevel
from sensors.sensor_factory import SensorFactory
from decorators.data_decorators import (
    SensorReadingAdapter, NoiseFilterDecorator, AverageSmoothingDecorator
)
from observers.flood_observers import (
    FloodMonitoringSubject, DashboardObserver,
    AlertNotificationObserver, ColdStorageObserver
)
from strategies.threshold_strategies import (
    ManggaraiThresholdStrategy, KatulampaThresholdStrategy, DepokThresholdStrategy
)
from broker.message_broker import MessageBroker


# ═══════════════════════════════════════════════════════════════
# KONSTANTA SIMULASI
# ═══════════════════════════════════════════════════════════════

SIMULATION_ROUNDS   = 15   # jumlah siklus pembacaan sensor
SENSOR_READ_DELAY   = 0.3  # detik antar siklus (mensimulasikan interval 5 detik)
SEPARATOR = "═" * 70


def print_header():
    print(f"""
{SEPARATOR}
   🌊  FLOODWATCH IoT — SIMULASI SISTEM PERINGATAN DINI BANJIR
       Pemerintah Provinsi DKI Jakarta
       Simulasi PoC — {datetime.now().strftime('%d %B %Y, %H:%M:%S')}
{SEPARATOR}
""")


def print_section(title: str):
    print(f"\n{'─'*70}")
    print(f"  {title}")
    print(f"{'─'*70}")


# ═══════════════════════════════════════════════════════════════
# FASE 1 — INISIALISASI KOMPONEN
# ═══════════════════════════════════════════════════════════════

def initialize_sensors() -> dict:
    """
    Menggunakan FACTORY METHOD untuk membuat sensor di setiap lokasi.
    Konfigurasi bisa dibaca dari file / database di production.
    """
    print_section("FASE 1 — FACTORY METHOD: Inisialisasi Sensor")

    sensor_configs = [
        # Katulampa (hulu) — mulai dari kondisi normal
        {
            "type":       SensorType.WATER_LEVEL,
            "sensor_id":  "KTL-WL-001",
            "location":   "Bendung Katulampa",
            "base_level": 0.8,
        },
        {
            "type":          SensorType.RAINFALL,
            "sensor_id":     "KTL-RF-001",
            "location":      "Bendung Katulampa",
            "rain_intensity": 15.0,
        },
        # Manggarai (hilir) — ketinggian lebih rendah karena kanal lebih lebar
        {
            "type":       SensorType.WATER_LEVEL,
            "sensor_id":  "MGR-WL-001",
            "location":   "Pintu Air Manggarai",
            "base_level": 7.2,    # baseline tinggi karena sudah di hilir
        },
        {
            "type":       SensorType.FLOW_SPEED,
            "sensor_id":  "MGR-FS-001",
            "location":   "Pintu Air Manggarai",
            "base_speed": 0.6,
        },
    ]

    print()
    raw_sensors = SensorFactory.create_sensor_cluster(sensor_configs)

    # Return sebagai dict: sensor_id → sensor object
    return {s.sensor_id: s for s in raw_sensors}


def build_decorator_pipelines(raw_sensors: dict) -> dict:
    """
    Membungkus sensor mentah dengan DECORATOR PIPELINE.

    Pipeline:
      raw_sensor
        → SensorReadingAdapter     (bridge ke interface Decorator)
        → NoiseFilterDecorator     (buang anomali spike)
        → AverageSmoothingDecorator (haluskan dengan moving average)
    """
    print_section("FASE 1B — DECORATOR PATTERN: Membangun Pipeline Pemrosesan Data")

    pipelines = {}
    for sensor_id, sensor in raw_sensors.items():
        adapter   = SensorReadingAdapter(sensor)
        filtered  = NoiseFilterDecorator(adapter, spike_threshold=3.5)
        smoothed  = AverageSmoothingDecorator(filtered, window_size=4)
        pipelines[sensor_id] = smoothed
        print(f"  Pipeline [{sensor_id}]: "
              f"Raw → NoiseFilter(×3.5) → MovingAvg(n=4)")

    return pipelines


def setup_monitoring_centers() -> dict:
    """
    Menyiapkan FloodMonitoringSubject + Observer untuk setiap lokasi.
    Subject menggunakan STRATEGY PATTERN untuk evaluasi threshold.
    Observer terdaftar menggunakan OBSERVER PATTERN.
    """
    print_section("FASE 1C — OBSERVER + STRATEGY: Setup Pusat Monitoring")

    # Inisialisasi strategy per lokasi
    strategy_katulampa = KatulampaThresholdStrategy()
    strategy_manggarai = ManggaraiThresholdStrategy()

    # Inisialisasi Observer (bersama / di-share antar lokasi)
    dashboard   = DashboardObserver()
    notif_sys   = AlertNotificationObserver()
    cold_store  = ColdStorageObserver()

    # Buat Subject per lokasi dan daftarkan Observer
    print()
    centers = {}
    for loc, strategy in [("Bendung Katulampa",    strategy_katulampa),
                           ("Pintu Air Manggarai",  strategy_manggarai)]:
        subject = FloodMonitoringSubject(location=loc, strategy=strategy)
        print(f"\n  📍 Pusat Monitoring: {loc}")
        print(f"     Menggunakan Strategy: {strategy.name}")
        subject.register(dashboard)
        subject.register(notif_sys)
        subject.register(cold_store)
        centers[loc] = subject

    return centers, dashboard, notif_sys, cold_store


# ═══════════════════════════════════════════════════════════════
# FASE 2 — SIMULASI INGESTION VIA MESSAGE BROKER
# ═══════════════════════════════════════════════════════════════

def run_simulation(pipelines: dict, centers: dict, broker: MessageBroker):
    """
    Loop utama simulasi:
    Setiap ronde = satu siklus pembacaan semua sensor (mewakili interval 5 detik).

    Alur:
    1. Sensor baca data (mentah, mungkin ada noise)
    2. Pipeline decorator memproses data (filter + smooth)
    3. Publish ke Message Broker (simulasi MQTT → Kafka)
    4. Consume dari Broker → forward ke Monitoring Subject
    5. Subject evaluasi dengan Strategy → notify Observer jika berubah
    """
    print_section("FASE 2 — SIMULASI DATA INGESTION & STREAM PROCESSING")

    # Peta: sensor_id → nama lokasi monitoring center
    sensor_to_center = {
        "KTL-WL-001": "Bendung Katulampa",
        "KTL-RF-001": "Bendung Katulampa",
        "MGR-WL-001": "Pintu Air Manggarai",
        "MGR-FS-001": "Pintu Air Manggarai",
    }

    # Buat topic di broker
    broker.create_topic("sensor.katulampa")
    broker.create_topic("sensor.manggarai")
    print()

    for ronde in range(1, SIMULATION_ROUNDS + 1):
        print(f"\n{'┄'*70}")
        print(f"  🔄 RONDE {ronde:02d}/{SIMULATION_ROUNDS} — "
              f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        print(f"{'┄'*70}")

        # ── Demo Strategy Swap di ronde tertentu ─────────────
        if ronde == 8:
            print(f"\n  [DEMO STRATEGY SWAP] Mensimulasikan perubahan standar "
                  f"threshold karena perluasan kanal Manggarai...")
            new_strategy = DepokThresholdStrategy()
            centers["Pintu Air Manggarai"].set_strategy(new_strategy)
            print(f"  [INFO] Strategy Pintu Air Manggarai sekarang: {new_strategy.name}")

        # ── Baca semua sensor & proses ────────────────────────
        for sensor_id, pipeline in pipelines.items():
            location = sensor_to_center[sensor_id]
            topic    = ("sensor.katulampa" if "KTL" in sensor_id
                        else "sensor.manggarai")

            # 1. Baca data melalui decorator pipeline
            reading = pipeline.read()

            # 2. Tampilkan bacaan sensor
            print(f"\n  {reading}")

            # 3. Publish ke Message Broker (non-blocking)
            broker.publish(topic, reading)

            # 4. Consume dari broker & proses oleh monitoring center
            msg = broker.consume(topic, timeout=0.1)
            if msg is not None:
                level = centers[location].process_reading(msg)
                if level == AlertLevel.NORMAL:
                    pass  # tidak perlu print — sudah dihandle observer jika berubah
            else:
                print(f"  [Broker] ⚠️  Timeout consume dari '{topic}'")

        time.sleep(SENSOR_READ_DELAY)


# ═══════════════════════════════════════════════════════════════
# FASE 3 — LAPORAN AKHIR
# ═══════════════════════════════════════════════════════════════

def print_final_report(dashboard, notif_sys, cold_store, broker, pipelines):
    print_section("FASE 3 — LAPORAN AKHIR SIMULASI")

    # Statistik Message Broker
    stats = broker.stats
    print(f"\n  📊 Statistik Message Broker:")
    print(f"     Total pesan dipublish : {stats['published']}")
    print(f"     Total pesan di-drop   : {stats['dropped']} (backpressure)")

    # Statistik NoiseFilter
    noise_filters = {sid: p._wrapped for sid, p in pipelines.items()}
    total_filtered = 0
    print(f"\n  📊 Statistik NoiseFilter (anomali yang dicegah):")
    for sid, nf in noise_filters.items():
        if hasattr(nf, 'filter_count'):
            print(f"     {sid}: {nf.filter_count} anomali difilter")
            total_filtered += nf.filter_count
    print(f"     ► Total False Alarm yang DICEGAH: {total_filtered}")

    # Ringkasan dashboard
    dash_summary = dashboard.get_summary()
    print(f"\n  📊 Ringkasan Dashboard Observer:")
    print(f"     Total event diterima : {dash_summary['total_events']}")
    print(f"     Distribusi per level :")
    for lvl, cnt in dash_summary['by_level'].items():
        print(f"       - {lvl}: {cnt}x")

    # Log notifikasi
    print(f"\n  📊 Log Notifikasi Warga (5 terakhir):")
    for log in notif_sys.notification_log[-5:]:
        print(f"     {log}")

    # Cold storage
    cold_summary = cold_store.get_monthly_report()
    print(f"\n  📊 Statistik Cold Storage:")
    print(f"     Total event diarsipkan: {cold_summary['total_archived_events']}")
    for loc, cnt in cold_summary['events_per_location'].items():
        print(f"       {loc}: {cnt} event")

    print(f"\n{SEPARATOR}")
    print(f"  ✅ Simulasi FloodWatch IoT selesai.")
    print(f"     Design Patterns digunakan:")
    print(f"       1. Factory Method  — Inisialisasi {len(pipelines)} sensor")
    print(f"       2. Decorator       — Pipeline NoiseFilter + MovingAvg per sensor")
    print(f"       3. Observer        — 3 observer menerima push event perubahan siaga")
    print(f"       4. Strategy        — Threshold dinamis, di-swap saat ronde 8")
    print(f"{SEPARATOR}\n")


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    random.seed(42)   # reproducible output untuk demo
    print_header()

    # ── Inisialisasi ──────────────────────────────────────────
    raw_sensors = initialize_sensors()
    pipelines   = build_decorator_pipelines(raw_sensors)
    centers, dashboard, notif_sys, cold_store = setup_monitoring_centers()
    broker      = MessageBroker(queue_maxsize=100)

    print(f"\n  [INFO] Semua komponen berhasil diinisialisasi.")
    print(f"  [INFO] Memulai simulasi {SIMULATION_ROUNDS} ronde pembacaan sensor...")
    time.sleep(0.5)

    # ── Simulasi Utama ────────────────────────────────────────
    run_simulation(pipelines, centers, broker)

    # ── Laporan ───────────────────────────────────────────────
    print_final_report(dashboard, notif_sys, cold_store, broker, pipelines)


if __name__ == "__main__":
    main()
