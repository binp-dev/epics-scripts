from __future__ import annotations
from typing import Any, Iterable, List, Protocol, TextIO

from time import sleep
from pathlib import Path
from dataclasses import dataclass
from datetime import date, datetime
import argparse
import csv
from epics import PV


class CsvWriter(Protocol):

    def writerow(self, row: Iterable[Any]) -> Any:
        ...

    def writerows(self, rows: Iterable[Iterable[Any]]) -> None:
        ...


class Database:

    def __init__(self, channel_count: int, now: datetime, file: TextIO, writer: CsvWriter) -> None:

        self.channel_count = channel_count
        self.file = file
        self.writer = writer

        self.values: List[float | None] = [None] * self.channel_count
        self.time: float | None = None

        epoch = datetime.fromtimestamp(0)
        self.start_time = (now - epoch).total_seconds()

    def _write(self) -> None:
        if self.time is not None:
            time_fmt = f"{self.time:.3f}"
        else:
            time_fmt = "<unknown>"
        values_fmt = [f"{v:.6f}" for v in self.values]

        self.writer.writerow([time_fmt] + values_fmt)
        self.file.flush()

        #print(f"{time_fmt}: [{', '.join(values_fmt)}]")

        self.time = None
        self.values = [None] * self.channel_count

    def push(self, index: int, value: float, timestamp: float) -> None:
        self.time = timestamp - self.start_time
        self.values[index] = value
        if all([v is not None for v in self.values]):
            self._write()


@dataclass
class Callback:
    db: Database
    index: int

    def __call__(self, pvname: str, value: float, timestamp: float, **kws: Any) -> None:
        self.db.push(self.index, value, timestamp)


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

    now = datetime.now()
    date_fmt = now.strftime("%Y-%m-%d_%H-%M-%S")
    out_path = args.out_dir / f"log_adcs_{date_fmt}.csv"
    print(f"Logging to file '{out_path}'")

    channel_count = 6
    with open(out_path, "w") as file:
        writer: CsvWriter = csv.writer(file, delimiter=",", quotechar="\"")
        db = Database(channel_count, now, file, writer)
        values = [None] * channel_count
        pvs = [PV(f"ai{i}.VAL", callback=Callback(db, i)) for i in range(channel_count)]

        while True:
            sleep(1.0)


if __name__ == "__main__":
    main()
