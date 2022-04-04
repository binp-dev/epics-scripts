from __future__ import annotations
from typing import List, Generator

from pyepics_asyncio import Pv

DAC_WF_MAX_LEN = 10000
DAC_PERIOD_S = 1.0 / DAC_WF_MAX_LEN

ADC_CHANNEL_COUNT = 6
ADC_WF_MAX_LEN = 10000
ADC_PERIOD_S = 1.0 / DAC_WF_MAX_LEN


async def play_on_dac(generator: Generator[List[float], None, None], cyclic: bool = False) -> None:
    dac = await Pv.connect("aao0")
    ready = await Pv.connect("aao0_request")

    await (await Pv.connect("aao0_cyclic")).put(cyclic)

    async with ready.monitor(current=True) as ready_mon:
        for i, waveform in enumerate(generator):
            assert len(waveform) <= DAC_WF_MAX_LEN
            async for flag in ready_mon:
                if flag:
                    break
            print(f"Sending waveform {i} of {len(waveform)} points")
            await dac.put(waveform)
