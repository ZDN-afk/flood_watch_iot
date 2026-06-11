# 🌊 FloodWatch IoT — Proof of Concept
**Studi Kasus 6: Banjir Data di Pintu Air Jakarta**
Proyek Akhir — Mata Kuliah Arsitektur Perangkat Lunak

---

## 📋 Deskripsi

Simulasi sistem peringatan dini banjir berbasis IoT untuk Pemerintah Provinsi DKI Jakarta.
PoC ini membuktikan bahwa arsitektur berbasis **Event-Stream + Design Pattern** mampu:

- ✅ Mengatasi overload server (thread starvation) melalui Message Broker non-blocking
- ✅ Menyaring anomali sensor (burung hinggap → lonjakan palsu) sebelum memicu sirine
- ✅ Memisahkan jalur data **Hot Path** (notifikasi real-time) vs **Cold Path** (arsip)
- ✅ Mendukung penggantian aturan threshold secara **dinamis tanpa restart sistem**

---

## 🏗️ Design Patterns yang Diimplementasikan

| # | Pattern | Lokasi File | Fungsi |
|---|---------|------------|--------|
| 1 | **Factory Method** | `sensors/sensor_factory.py` | Memproduksi objek sensor (WaterLevel/Rainfall/FlowSpeed) dari konfigurasi |
| 2 | **Decorator** | `decorators/data_decorators.py` | Pipeline pemrosesan: `NoiseFilterDecorator` + `AverageSmoothingDecorator` |
| 3 | **Observer** | `observers/flood_observers.py` | Push notifikasi otomatis ke Dashboard, Alert System, Cold Storage |
| 4 | **Strategy** *(bonus)* | `strategies/threshold_strategies.py` | Threshold dinamis per pintu air, dapat di-swap runtime |

---

## 📁 Struktur Proyek

```
flood_watch_iot/
├── main.py                          # Entry point simulasi
├── models/
│   └── sensor_data.py               # Data classes: SensorReading, FloodEvent, AlertLevel
├── sensors/
│   ├── base_sensor.py               # Abstract base sensor
│   ├── concrete_sensors.py          # WaterLevelSensor, RainfallSensor, FlowSpeedSensor
│   └── sensor_factory.py            # [PATTERN 1] Factory Method
├── decorators/
│   └── data_decorators.py           # [PATTERN 2] NoiseFilter + AverageSmoothing Decorator
├── observers/
│   └── flood_observers.py           # [PATTERN 3] Subject + Observer (Dashboard, Alert, Storage)
├── strategies/
│   └── threshold_strategies.py      # [PATTERN 4] Strategy: Manggarai, Katulampa, Depok
├── broker/
│   └── message_broker.py            # Simulasi MQTT/Kafka message broker
└── README.md
```

---

## ⚙️ Cara Menjalankan

### Prasyarat
- **Python 3.10+** (gunakan Python 3.12 untuk hasil terbaik)
- Tidak memerlukan library eksternal (hanya Python standard library)

### Langkah

```bash
# 1. Clone / download repositori
git clone <url-repo>
cd flood_watch_iot

# 2. (Opsional) Buat virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
# atau: venv\Scripts\activate  # Windows

# 3. Jalankan simulasi
python main.py
```

### Ekspektasi Output

Program akan menampilkan 3 fase:
1. **FASE 1** — Inisialisasi sensor via Factory Method, pembuatan decorator pipeline, registrasi observer
2. **FASE 2** — 15 ronde simulasi pembacaan sensor (dengan noise, filter, push notifikasi)
3. **FASE 3** — Laporan akhir statistik (anomali difilter, event diterima, arsip cold storage)

**Output penting yang harus terlihat:**
```
[NoiseFilter] 🚫 ANOMALI DIFILTER @ ... Raw: 219.34 mm/jam >> Diganti: ...
[DEMO STRATEGY SWAP] Strategy ditukar: Pintu Air Manggarai → Pintu Air Depok
[Subject:...] 📡 Mempublikasikan event ke 3 observer...
  [Dashboard Pemprov DKI] 🔴 UPDATE STATUS | ...
  [Sistem Notifikasi Warga] 🚨 [MOCK SIRINE + SMS + BPBD API] ...
  [Cold Storage / Data Warehouse] 💾 Event diarsipkan ...
```

---

## 🔍 Cara Membaca Kode

### Factory Method (sensors/sensor_factory.py)
```python
# Kode klien hanya perlu dict konfigurasi — tidak perlu tahu kelas konkretnya
sensor = SensorFactory.create_sensor({
    "type":       SensorType.WATER_LEVEL,
    "sensor_id":  "KTL-WL-001",
    "location":   "Bendung Katulampa",
    "base_level": 0.8,
})
```

### Decorator (decorators/data_decorators.py)
```python
# Lapisan dapat ditambah/dilepas tanpa ubah kelas sensor
adapter  = SensorReadingAdapter(raw_sensor)
filtered = NoiseFilterDecorator(adapter, spike_threshold=3.5)
smoothed = AverageSmoothingDecorator(filtered, window_size=4)
reading  = smoothed.read()   # melewati semua lapisan otomatis
```

### Observer (observers/flood_observers.py)
```python
# Subject tidak tahu detail observer — hanya memanggil on_flood_event()
subject.register(DashboardObserver())
subject.register(AlertNotificationObserver())
subject.register(ColdStorageObserver())
# Ketika level berubah → ketiga observer otomatis menerima push event
```

### Strategy (strategies/threshold_strategies.py)
```python
# Swap strategi di runtime tanpa restart
subject.set_strategy(DepokThresholdStrategy())
```

---

## 🧪 Kustomisasi Simulasi

Edit konstanta di `main.py`:
```python
SIMULATION_ROUNDS = 15    # jumlah siklus pembacaan
SENSOR_READ_DELAY = 0.3   # detik antar ronde
```

Ubah probabilitas anomali di `sensors/concrete_sensors.py`:
```python
ANOMALY_PROBABILITY = 0.15   # WaterLevelSensor: 15% kemungkinan spike
```

---

## 👥 Tim Pengembang
| Nama | NIM | Kontribusi |
|------|-----|-----------|
| Aprilia Candra Puspita | 24051130025 | Perancangan data model dan orkestrasi simulasi utama |
| Jeremy Joe Steven Pasaribu | 24051130100 | Implementasi layer sensor dan Factory Method Pattern |
| Vivien Silvany | 24051130208 | Implementasi Observer Pattern dan sistem distribusi peringatan |
| Muhammad Zaidaan | 24051130110 | Implementasi Strategy Pattern, Decorator Pattern, Message Broker, pengelolaan repositori GitHub, dan penyusunan dokumentasi README |
| Muhammad Fachry Ardiakusuma | 24051130111 | Implementasi pipeline pemrosesan data dan Decorator Pattern |

