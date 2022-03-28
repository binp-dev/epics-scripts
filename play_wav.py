from __future__ import annotations
from typing import List, Generator

import sys
import wave
import asyncio

from pyepics_asyncio import Pv


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


def waveform_reader(f: wave.Wave_read, nelm: int, freq: float = 1e4) -> Generator[List[float], None, None]:
    fps = f.getframerate()
    ratio = fps / freq
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
            if len(output) >= nelm:
                yield output
                output.clear()
            counter -= ratio
            mean = part * value
    if counter >= 1.0:
        output.append(mean / counter)
    yield output


async def main(path: str) -> None:
    reader = waveform_reader(wave.open(path, "rb"), 10000)

    dac = await Pv.connect("aao0")
    ready = await Pv.connect("aao0_request")
    await (await Pv.connect("aao0_cyclic")).put(True)

    async with ready.monitor(current=True) as ready_mon:
        for i, waveform in enumerate(reader):
            async for flag in ready_mon:
                if flag:
                    break
            print(f"Sending waveform {i} of {len(waveform)} points")
            await dac.put(waveform)


if __name__ == "__main__":
    asyncio.run(main(*sys.argv[1:]))
