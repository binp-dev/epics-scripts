from __future__ import annotations
from typing import List

import sys
import math

from epics import PV # type: ignore

from utils.tornado import DAC_WF_MAX_LEN


def sine(mag: float, freq: float, count: int) -> List[float]:
    ts = [float(i) / count for i in range(count)]
    return [mag * math.sin(2.0 * math.pi * freq * t) for t in ts]


def main() -> None:
    mag = float(sys.argv[1])
    freq = float(sys.argv[2])

    PV("aao0_cyclic").put(True, wait=True)

    PV("aao0").put(sine(mag, freq, DAC_WF_MAX_LEN), wait=True)


if __name__ == "__main__":
    main()
