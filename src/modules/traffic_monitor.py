"""
Inspector Rabbit - Traffic Monitor
Counter-Surveillance Feature #2

Real-time network I/O sampling with anomaly detection.
Maintains a rolling window of bandwidth metrics and alerts when
traffic spikes suggest unexpected data exfiltration or surveillance.
"""

import time
from collections import deque
from datetime import datetime

import psutil
from PyQt6.QtCore import QThread, pyqtSignal


HISTORY_LEN = 120       # samples kept (~2 minutes at 1Hz)
SPIKE_MULTIPLIER = 4.0  # N× baseline = anomaly alert
MIN_BASELINE_SAMPLES = 10


class TrafficMonitor(QThread):
    """
    Counter-Surveillance Feature #2 — Real-time Traffic Monitor

    Samples psutil.net_io_counters() every second, computes per-second
    byte/packet rates, maintains a rolling history for graphing, and
    raises anomaly alerts when traffic significantly exceeds the baseline.
    """

    sample_ready  = pyqtSignal(dict)   # {ts, bytes_in, bytes_out, pkts_in, pkts_out}
    anomaly       = pyqtSignal(dict)   # {ts, direction, rate, baseline, detail}
    log_event     = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._bytes_in_hist:  deque = deque(maxlen=HISTORY_LEN)
        self._bytes_out_hist: deque = deque(maxlen=HISTORY_LEN)
        self._timestamps:     deque = deque(maxlen=HISTORY_LEN)
        self._prev_counters = None
        self._alerted_in = False
        self._alerted_out = False

    def run(self):
        self._running = True
        self.log_event.emit("📊  Traffic Monitor active — sampling I/O every second")
        self._prev_counters = psutil.net_io_counters()
        self._prev_time = time.time()

        while self._running:
            self.msleep(1000)
            try:
                self._sample()
            except Exception as exc:
                self.log_event.emit(f"⚠️  Traffic sample error: {exc}")

    def stop_monitor(self):
        self._running = False
        self.quit()
        self.wait(2000)

    # ── Sampling ──────────────────────────────────────────────────────────

    def _sample(self):
        now = time.time()
        cur = psutil.net_io_counters()
        elapsed = max(now - self._prev_time, 0.001)

        bytes_in  = (cur.bytes_recv  - self._prev_counters.bytes_recv)  / elapsed
        bytes_out = (cur.bytes_sent  - self._prev_counters.bytes_sent)  / elapsed
        pkts_in   = (cur.packets_recv - self._prev_counters.packets_recv) / elapsed
        pkts_out  = (cur.packets_sent - self._prev_counters.packets_sent) / elapsed

        # Clamp negatives (counter wrap or NIC reset)
        bytes_in  = max(0.0, bytes_in)
        bytes_out = max(0.0, bytes_out)

        ts = datetime.now().strftime('%H:%M:%S')
        self._timestamps.append(ts)
        self._bytes_in_hist.append(bytes_in)
        self._bytes_out_hist.append(bytes_out)

        self._prev_counters = cur
        self._prev_time = now

        sample = {
            'ts': ts,
            'bytes_in':  bytes_in,
            'bytes_out': bytes_out,
            'pkts_in':   pkts_in,
            'pkts_out':  pkts_out,
            'history_in':  list(self._bytes_in_hist),
            'history_out': list(self._bytes_out_hist),
            'timestamps':  list(self._timestamps),
        }
        self.sample_ready.emit(sample)
        self._check_anomaly(bytes_in, bytes_out, ts)

    def _check_anomaly(self, bytes_in: float, bytes_out: float, ts: str):
        if len(self._bytes_in_hist) < MIN_BASELINE_SAMPLES:
            return

        # Exclude current sample from baseline calculation
        past_in  = list(self._bytes_in_hist)[:-1]
        past_out = list(self._bytes_out_hist)[:-1]

        baseline_in  = sum(past_in)  / len(past_in)
        baseline_out = sum(past_out) / len(past_out)

        # Inbound spike
        if baseline_in > 512 and bytes_in > baseline_in * SPIKE_MULTIPLIER:
            if not self._alerted_in:
                self._alerted_in = True
                self.anomaly.emit({
                    'ts': ts,
                    'direction': 'INBOUND',
                    'rate': bytes_in,
                    'baseline': baseline_in,
                    'detail': (f'Inbound spike: {self._fmt(bytes_in)}/s '
                               f'vs baseline {self._fmt(baseline_in)}/s '
                               f'({bytes_in/max(baseline_in,1):.1f}× normal)'),
                })
                self.log_event.emit(
                    f"⚠️  TRAFFIC SPIKE ↓ {self._fmt(bytes_in)}/s inbound "
                    f"({bytes_in/max(baseline_in,1):.1f}× baseline)"
                )
        elif bytes_in < baseline_in * 2:
            self._alerted_in = False

        # Outbound spike
        if baseline_out > 256 and bytes_out > baseline_out * SPIKE_MULTIPLIER:
            if not self._alerted_out:
                self._alerted_out = True
                self.anomaly.emit({
                    'ts': ts,
                    'direction': 'OUTBOUND',
                    'rate': bytes_out,
                    'baseline': baseline_out,
                    'detail': (f'Outbound spike: {self._fmt(bytes_out)}/s '
                               f'vs baseline {self._fmt(baseline_out)}/s — '
                               f'possible data exfiltration'),
                })
                self.log_event.emit(
                    f"🔴 OUTBOUND SPIKE ↑ {self._fmt(bytes_out)}/s "
                    f"({bytes_out/max(baseline_out,1):.1f}× baseline) — possible exfil"
                )
        elif bytes_out < baseline_out * 2:
            self._alerted_out = False

    @staticmethod
    def _fmt(bps: float) -> str:
        if bps >= 1_000_000:
            return f"{bps/1_000_000:.1f} MB"
        if bps >= 1_000:
            return f"{bps/1_000:.1f} KB"
        return f"{bps:.0f} B"

    # ── Accessors for graph ────────────────────────────────────────────────

    def get_history(self) -> dict:
        return {
            'timestamps': list(self._timestamps),
            'bytes_in':   list(self._bytes_in_hist),
            'bytes_out':  list(self._bytes_out_hist),
        }
