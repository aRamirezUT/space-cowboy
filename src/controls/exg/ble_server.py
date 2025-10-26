#!/usr/bin/env python3
"""
BLE EXG server using Nordic UART Service (NUS) and Bleak, based on EXGServerTemplate.

- Connects ONLY by exact device name (no address/identifier needed or used).
- Matches against BOTH device.name AND advertisement local_name to handle platform quirks.
- Subscribes to notifications on NUS_TX and expects CSV lines like: "12345,30122,55210\n".
- Buffers samples and returns all accumulated samples to EXGServerTemplate._process_chunk.
"""

import asyncio
import logging
import threading
import time
from collections import deque
from collections.abc import Sequence

import numpy as np
from pylsl import local_clock
from bleak import BleakScanner, BleakClient, BleakError

from .exg_server_template import EXGServerTemplate

# ====== Nordic UART Service (NUS) UUIDs ======
# Used after connect to subscribe. We do NOT require this for discovery in name-only mode.
NUS_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
# Notifications from device -> host (TX characteristic from peripheral’s perspective)
NUS_TX      = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

# ====== Defaults ======
TARGET_NAME = "EXG-BLE-0"

# Toggle to see everything discovered during the scan window
LOG_DISCOVERED = True

class BLEServer(EXGServerTemplate):
    """
    BLE-backed EXG server. Only _acquire_samples() is required by the template, but
    we additionally manage a background asyncio task for the Bleak client.
    """

    def __init__(
        self,
        *,
        target_name: str = TARGET_NAME,
        nus_service: str = NUS_SERVICE,
        nus_tx_uuid: str = NUS_TX,
        fps: float = 100.0,
        lowpass_fs: float | None = None,
        highpass_fs: float | None = None,
        notch_fs_list: list[float] | None = None,
        scan_timeout_s: float = 20.0,   # generous scan window
    ) -> None:
        super().__init__(
            name="BLEServer",
            fps=fps,
            lsl_raw=False,
            lsl_filtered=True,
            filtered_stream_name=TARGET_NAME,
            lowpass_fs=lowpass_fs,
            highpass_fs=highpass_fs,
            notch_fs_list=notch_fs_list,
            source_id="BLELSL",
            daemon=True,
        )

        # BLE config (name-only selection)
        self.target_name = target_name
        self.nus_service = nus_service.lower()
        self.nus_tx_uuid = nus_tx_uuid.lower()
        self.scan_timeout_s = scan_timeout_s

        # Runtime
        self._client: BleakClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ble_thread: threading.Thread | None = None

        # Buffers for incoming samples
        self._raw_buf: deque[np.ndarray] = deque(maxlen=8192)
        self._ts_buf: deque[float] = deque(maxlen=8192)
        self._lock = threading.Lock()

        # Initial processing configuration (adjust channel_count if needed)
        self._configure_processing(sample_rate=fps, channel_count=2)

    # ------------- Lifecycle overrides to manage BLE worker -------------

    def start(self) -> None:
        """Start BLE worker thread first, then enter EXG acquisition loop."""
        self._start_ble_worker()
        super().start()

    def stop(self) -> None:
        """Signal EXG loop to stop, then shutdown BLE worker and event loop."""
        super().stop()
        self._stop_ble_worker()

    # ------------- BLE worker management -------------

    def _start_ble_worker(self) -> None:
        if self._ble_thread and self._ble_thread.is_alive():
            return
        # Dedicated event loop in a background thread
        self._loop = asyncio.new_event_loop()
        self._ble_thread = threading.Thread(
            target=self._run_loop_forever,
            args=(self._loop,),
            name="ble-worker",
            daemon=True,
        )
        self._ble_thread.start()
        # Schedule the BLE main task
        assert self._loop is not None
        asyncio.run_coroutine_threadsafe(self._ble_main(), self._loop)

    def _run_loop_forever(self, loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        finally:
            pending = asyncio.all_tasks(loop=loop)
            for t in pending:
                t.cancel()
            try:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            finally:
                loop.close()

    def _stop_ble_worker(self) -> None:
        # Best-effort cleanup then stop the loop.
        if self._loop and self._loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(self._ble_cleanup(), self._loop)
            try:
                fut.result(timeout=2.0)
            except Exception:
                pass
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._ble_thread and self._ble_thread.is_alive():
            self._ble_thread.join(timeout=3.0)

    # ------------- BLE coroutines -------------

    async def _ble_main(self) -> None:
        """Scan, connect, and subscribe to notifications until stop is requested."""
        # Windows quirk: prefer SelectorEventLoopPolicy for Bleak (if user is on Windows)
        try:
            import sys
            if sys.platform.startswith("win"):
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[attr-defined]
        except Exception:
            pass

        device = await self._find_device()
        if device is None:
            self.log.error("No device found with exact name=%s.", self.target_name)
            return

        self.log.info("Connecting to %s (%s)…", getattr(device, "name", None), getattr(device, "address", None))
        try:
            async with BleakClient(device) as client:
                self._client = client
                self.log.info("Connected: %s", client.is_connected)

                # Subscribe to notifications (requires NUS on the peripheral)
                await client.start_notify(self.nus_tx_uuid, self._on_notify)
                self.log.info("Subscribed to NUS TX notifications: %s", self.nus_tx_uuid)

                # Keep the task alive while server is running
                while self.running:
                    await asyncio.sleep(0.2)

                # Unsubscribe before leaving context
                try:
                    await client.stop_notify(self.nus_tx_uuid)
                except Exception:
                    pass

        except BleakError as e:
            self.log.exception("BLE error: %s", e)
        finally:
            self._client = None
            self.log.info("BLE worker exiting.")

    async def _ble_cleanup(self) -> None:
        """Best-effort unsubscribe/disconnect if still connected."""
        client = self._client
        if client is None:
            return
        try:
            if client.is_connected:
                try:
                    await client.stop_notify(self.nus_tx_uuid)
                except Exception:
                    pass
                await client.disconnect()
        except Exception:
            pass
        finally:
            self._client = None

    async def _find_device(self):
        """
        Name-only selection with robust matching:

        - Exact match against device.name
        - Exact match against advertisement local_name (adv.local_name)
        - Logs every discovered candidate during the scan window
        """
        self.log.info("Scanning for exact name '%s'…", self.target_name)

        # Preferred path: use return_adv to also check adv.local_name
        try:
            advs = await BleakScanner.discover(return_adv=True, timeout=self.scan_timeout_s)  # type: ignore[arg-type]
            if LOG_DISCOVERED:
                for d, adv in advs.values():
                    self._log_candidate(d, adv)

            # Try exact match on either device.name or adv.local_name
            for d, adv in advs.values():
                dev_name = getattr(d, "name", None)
                adv_name = getattr(adv, "local_name", None)
                if dev_name == self.target_name or adv_name == self.target_name:
                    return d

            return None

        except TypeError:
            # Older Bleak versions: fall back to two-stage discovery
            self.log.warning("Bleak does not support return_adv; using fallback discovery.")
            devices = await BleakScanner.discover(timeout=self.scan_timeout_s)
            if LOG_DISCOVERED:
                for d in devices:
                    self._log_candidate(d, None)

            # Exact match on device.name only (no adv.local_name available here)
            for d in devices:
                if getattr(d, "name", None) == self.target_name:
                    return d

            return None

    def _log_candidate(self, d, adv) -> None:
        try:
            name = getattr(d, "name", None)
            addr = getattr(d, "address", None)
            local_name = getattr(adv, "local_name", None) if adv is not None else None
            suuids = getattr(adv, "service_uuids", None) if adv is not None else None
            self.log.info(
                "Discovered: name=%r local_name=%r addr=%r suuids=%s",
                name, local_name, addr, suuids
            )
        except Exception:
            pass

    # ------------- Notification -> buffer -------------

    def _parse_sample(self, line: bytes) -> list[float] | None:
        """Parse one CSV line → list of floats (raw ADC counts or volts)."""
        if not line:
            return None
        try:
            text = line.decode("utf-8", errors="ignore").strip()
            if not text:
                return None
            return [float(part) for part in text.split(",")]
        except Exception:
            return None

    def _on_notify(self, _handle: int, data: bytes) -> None:
        """
        Bleak notification callback. Parse CSV -> list[float], store with timestamp.
        """
        now = local_clock()
        try:
            sample = self._parse_sample(data)
            if sample is None:
                return
            vals = np.array(sample, dtype=np.float32)
        except Exception:
            return

        with self._lock:
            self._raw_buf.append(vals)
            self._ts_buf.append(now)

    # ------------- EXGServerTemplate required method -------------

    def _acquire_samples(self) -> tuple[np.ndarray, Sequence[float]] | None:
        """
        Called repeatedly by EXGServerTemplate.run().
        Should return (raw_chunk [N,C], ts_chunk [N]) or None if not ready yet.
        """
        with self._lock:
            if not self._raw_buf:
                return None
            buff_size = len(self._raw_buf)
            raw_list = [self._raw_buf.popleft() for _ in range(buff_size)]
            ts_list = [self._ts_buf.popleft() for _ in range(buff_size)]

        raw = np.vstack(raw_list).astype(np.float32, copy=False)
        print(f"Acquired chunk: {raw.shape[0]} samples, {raw.shape[1]} channels")
        return raw, ts_list


# ------------------------- CLI entrypoint -------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    )

    server = BLEServer(
        target_name=TARGET_NAME,      # exact match required
        nus_service=NUS_SERVICE,
        nus_tx_uuid=NUS_TX,
        fps=100.0,
        scan_timeout_s=20.0,          # increase if needed
    )

    try:
        server.start()  # Threaded acquisition loop from EXGServerTemplate
        while server.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping…")
    finally:
        server.stop()
        server.join()


if __name__ == "__main__":
    main()
