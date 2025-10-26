import numpy as np
from pylsl import StreamInlet, resolve_byprop
from time import sleep
from typing import Tuple
from .filtering.ema import EMA

from .ble_server import TARGET_NAME

# TODO: Instantiate a client in main.py
# TODO: Implement a mock numpy tuple
class EXGClient:
    """A PyQt widget that visualizes an LSL stream in real time using pyqtgraph."""

    def __init__(
        self,
        stream_name: str = TARGET_NAME,
    ) -> None:
        self.stream_name = stream_name

        streams = resolve_byprop("name", stream_name, timeout=5)
        if not streams:
            raise RuntimeError(f"No LSL stream named '{stream_name}' found.")

        self.inlet: StreamInlet = StreamInlet(streams[0])
        info = self.inlet.info()
        self.sampling_rate = info.nominal_srate() or 250.0
        self.num_channels = info.channel_count()
        self.channel_labels = self._resolve_channel_labels(info)
        
        self.ema = EMA(num_channels=self.num_channels, 
                       fs=self.sampling_rate,
                       window_intervals_ms=[250], 
                       methods=['mean']
                       )

    # INFO: Each channel is a different player.
    def get_data(self, seconds=0.0) -> Tuple[np.ndarray | None, np.ndarray | None]:
        chunk, _ = self.inlet.pull_chunk(timeout=0.0)
        if not chunk:
            return None, None
        if seconds > 0.0:
            target_length = int(self.sampling_rate * seconds)
            chunk = chunk[-target_length:] if len(chunk) > target_length else chunk
        chunk = self.ema.process(chunk)['mean'].T
        channel_0 = chunk[0] if len(chunk) > 0 else []
        channel_1 = chunk[1] if len(chunk) > 1 else []

        return channel_0, channel_1

    def _resolve_channel_labels(self, info) -> list[str]:
        """Extract readable channel labels from an LSL stream info."""
        labels: list[str] = []
        channels = info.desc().child("channels")
        channel = channels.child("channel")
        while not channel.empty():
            label = channel.child_value("label")
            labels.append(label if label else f"Ch {len(labels) + 1}")
            channel = channel.next_sibling()

        if not labels:
            labels = [f"Ch {idx + 1}" for idx in range(info.channel_count())]

        if len(labels) < info.channel_count():
            labels.extend(
                f"Ch {idx + 1}" for idx in range(len(labels), info.channel_count())
            )

        return labels
    
def main():
    client = EXGClient()
    while True:
        ch0, ch1 = client.get_data()
        if ch0 is not None:
            print(f"Channel 0 data: {ch0}")
        if ch1 is not None:
            print(f"Channel 1 data: {ch1}")
        sleep((1 / client.sampling_rate) * 4)  # Sleep for a short duration to avoid busy waiting
    
if __name__ == "__main__":
    main()