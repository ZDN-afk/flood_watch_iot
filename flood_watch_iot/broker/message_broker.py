"""
broker/message_broker.py
Simulasi Message Broker ringan (meniru perilaku MQTT + Apache Kafka).

Menggantikan protokol HTTP REST yang menyebabkan Thread Starvation
dengan model publish/subscribe yang asinkron dan non-blocking.

Di production, komponen ini akan digantikan oleh:
  - Sensor → MQTT Broker (Mosquitto / AWS IoT Core)
  - MQTT Broker → Apache Kafka (event streaming)
  - Kafka Consumer → Stream Processing (Apache Flink / Spark Streaming)

Dalam simulasi PoC ini, semua komponen berjalan in-process
menggunakan queue Python sebagai pengganti jaringan.
"""

import queue
import threading
import time
from typing import Callable, Dict, List
from models.sensor_data import SensorReading


class MessageBroker:
    """
    In-memory message broker yang mensimulasikan perilaku MQTT/Kafka.

    Fitur yang disimulasikan:
    - Topic-based publish/subscribe
    - In-memory queue sebagai pengganti jaringan TCP
    - Non-blocking publish (sensor tidak tunggu konfirmasi)
    - Backpressure simulation (queue maxsize terbatas)
    """

    def __init__(self, queue_maxsize: int = 200):
        self._topics: Dict[str, queue.Queue] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._queue_maxsize = queue_maxsize
        self._published_count = 0
        self._dropped_count   = 0

    def create_topic(self, topic_name: str) -> None:
        if topic_name not in self._topics:
            self._topics[topic_name] = queue.Queue(maxsize=self._queue_maxsize)
            self._subscribers[topic_name] = []
            print(f"  [Broker] 📌 Topic dibuat: '{topic_name}'")

    def subscribe(self, topic_name: str, callback: Callable) -> None:
        if topic_name not in self._topics:
            self.create_topic(topic_name)
        self._subscribers[topic_name].append(callback)

    def publish(self, topic_name: str, reading: SensorReading) -> bool:
        """
        Non-blocking publish. Jika queue penuh (backpressure),
        data di-drop dan di-log (simulasi data loss pada overload).
        Ini jauh lebih baik daripada HTTP yang akan block/timeout thread server.
        """
        if topic_name not in self._topics:
            self.create_topic(topic_name)

        try:
            self._topics[topic_name].put_nowait(reading)
            self._published_count += 1
            return True
        except queue.Full:
            self._dropped_count += 1
            print(f"  [Broker] ⚠️  BACKPRESSURE! Topic '{topic_name}' penuh. "
                  f"Data dropped (total dropped: {self._dropped_count})")
            return False

    def consume(self, topic_name: str, timeout: float = 0.1) -> SensorReading | None:
        """Ambil satu pesan dari topic (blocking dengan timeout)."""
        try:
            return self._topics[topic_name].get(timeout=timeout)
        except queue.Empty:
            return None

    def get_queue_size(self, topic_name: str) -> int:
        return self._topics[topic_name].qsize() if topic_name in self._topics else 0

    @property
    def stats(self) -> dict:
        return {
            "published": self._published_count,
            "dropped":   self._dropped_count,
            "topics":    list(self._topics.keys()),
        }
