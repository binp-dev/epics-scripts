from __future__ import annotations
from typing import AsyncIterator, List

import os
from pathlib import Path
from dataclasses import dataclass
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import datetime
import argparse

import asyncio
from aioitertools.builtins import zip as azip
import aiofiles
from aiocsv import AsyncWriter # type: ignore

from pyepics_asyncio import Pv

from utils import tornado

AsyncTextIO = aiofiles.threadpool.text.AsyncTextIOWrapper

Waveform = List[float]


@dataclass
class Storage:
    file: AsyncTextIO
    writer: AsyncWriter
    start_time: datetime

    @staticmethod
    @asynccontextmanager
    async def open(path: Path) -> AsyncIterator[Storage]:
        async with aiofiles.open(path, mode="w", encoding="utf-8", newline="") as file:
            yield await Storage.__ainit__(file)

    @staticmethod
    async def __ainit__(file: AsyncTextIO) -> Storage:
        writer = AsyncWriter(file)

        await writer.writerow(["time, s"] + [f"aai{i}, V" for i in range(tornado.ADC_CHANNEL_COUNT)])
        await file.flush()

        return Storage(file, writer, datetime.now())

    async def write(self, waveforms: List[Waveform]) -> None:
        now = (datetime.now() - self.start_time).total_seconds()
        for i, values in enumerate(zip(*waveforms)):
            time = now + i * tornado.ADC_PERIOD_S
            await self.writer.writerow([f"{time:.3f}"] + [f"{v:.6f}" for v in values])

        self.file.flush()


async def store(path: Path) -> None:
    async with Storage.open(path) as storage:
        pvs = [await Pv.connect(f"aai{i}") for i in range(tornado.ADC_CHANNEL_COUNT)]
        async with AsyncExitStack() as stack:
            monitors = [await stack.enter_async_context(pv.monitor()) for pv in pvs]
            async for wfs in azip(*monitors):
                print(f"Write waveforms")
                await storage.write(list(wfs))


def main() -> None:
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
    asyncio.run(store(out_path), debug=True)


if __name__ == "__main__":
    main()
