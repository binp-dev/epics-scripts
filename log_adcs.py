from __future__ import annotations
from typing import List, TextIO, Generator

from pathlib import Path
from dataclasses import dataclass
from contextlib import AsyncExitStack, contextmanager
from datetime import datetime
import argparse

import numpy as np
from numpy.typing import NDArray

import asyncio
from aioitertools.builtins import zip as azip, enumerate as aenumerate

from pyepics_asyncio import Pv

from utils import tornado

Waveform = NDArray[np.float64]


@dataclass
class Storage:
    file: TextIO
    start_time: datetime

    @staticmethod
    @contextmanager
    def open(path: Path) -> Generator[Storage, None, None]:
        with open(path, "w") as file:
            yield Storage(file)

    def __init__(self, file: TextIO) -> None:
        self.file = file
        self.start_time = datetime.now()
        # writerow(["time, s"] + [f"aai{i}, V" for i in range(tornado.ADC_CHANNEL_COUNT)])

    def write(self, waveforms: List[Waveform]) -> float:
        now = (datetime.now() - self.start_time).total_seconds()
        time = now + np.arange(len(waveforms[0]), dtype=np.float64) * tornado.ADC_PERIOD_S
        content: NDArray[np.float64] = np.stack([time, *waveforms], axis=-1)
        np.savetxt(self.file, content, fmt="%.6f", delimiter=",")
        self.file.flush()
        return now


async def store(path: Path) -> None:
    with Storage.open(path) as storage:
        pvs = [await Pv.connect(f"aai{i}") for i in range(tornado.ADC_CHANNEL_COUNT)]
        async with AsyncExitStack() as stack:
            monitors = [await stack.enter_async_context(pv.monitor()) for pv in pvs]
            async for i, wfs in aenumerate(azip(*monitors)):
                now = storage.write(list(wfs))
                print(f"Writing waveforms #{i} at {now} secs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log ADC channels to file.")
    parser.add_argument(
        "-o",
        "--out-dir",
        metavar="PATH",
        type=Path,
        default=Path.cwd(),
        help="Path to the directory where to create output file",
    )
    args = parser.parse_args()
    date_fmt = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = args.out_dir / f"log_adcs_{date_fmt}.csv"

    print(f"Logging ADC measurements to file '{out_path}'")
    asyncio.run(store(out_path))
