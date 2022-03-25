from __future__ import annotations
from typing import Any, List, Generator

import sys
import wave
from threading import Condition

from epics import PV

FREQ = 10000


def sample(f: wave.Wave_read) -> float:
    mean = 0.0
    bytes = f.readframes(1)
    width = f.getsampwidth()
    channel_count = f.getnchannels()
    assert len(bytes) == channel_count * width
    for i in range(channel_count):
        num = int.from_bytes(bytes[(i * width):((i + 1) * width)], "little", signed=True)
        mean += num / 2**(8 * width - 1)
    mean /= channel_count
    return mean


def waveform_reader(f: wave.Wave_read) -> Generator[List[float], None, None]:
    fps = f.getframerate()
    ratio = fps / FREQ
    output: List[float] = []
    mean = 0.0
    counter = 0.0
    for _ in range(f.getnframes()):
        value = sample(f)
        counter += 1.0
        if counter < ratio:
            mean += value
        else:
            part = counter - ratio
            mean += (1.0 - part) * value
            output.append(mean / ratio)
            if len(output) >= FREQ:
                yield output
                output.clear()
            counter -= ratio
            mean = part * value
    if counter >= 1.0:
        output.append(mean / counter)
    yield output


class DacReadyMonitor:

    def _callback(self, value: Any, **kw: Any) -> None:
        if value:
            with self.cond:
                self.cond.notify()

    def __init__(self) -> None:
        self.cond = Condition()
        self.pv = PV("aao0_request", auto_monitor=True, callback=self._callback)
        self.pv.run_callbacks()

    def wait(self) -> None:
        with self.cond:
            self.cond.wait()


def main(path: str) -> None:
    reader = waveform_reader(wave.open(path, "rb"))

    PV("aao0_cyclic").put(True, wait=True)
    dac = PV("aao0")
    ready = DacReadyMonitor()

    for i, waveform in enumerate(reader):
        ready.wait()
        print(f"Sending waveform {i} of {len(waveform)} points")
        dac.put(waveform, wait=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
