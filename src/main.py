#!/usr/bin/env python3

"""
main.py

This Python script serves as the main entry point for the application. It coordinates various
tasks related to time management, scheduling, and GPIO pin control. The script initializes
the application, manages schedule updates, and triggers callbacks for work and break events.

Dependencies:
- asyncio: Handling asynchronous tasks and event loops.
- datetime: Manipulating timestamps and datetime objects.
- typing: Specifying function argument and return types.
- tabulate: Formatting data into tables.

Functionality:
- Initializing and configuring the application.
- Managing the schedule and updating timestamps.
- Triggering callbacks for work and break events.
- Handling exceptions and cleaning up GPIO pins in case of errors.

"""

import asyncio
import time  # Import the time module

from datetime import datetime, time
from typing import List, Optional
from tabulate import tabulate

import config
import utils
import wrapper

from classes.schedule_keeper import ScheduleKeeper
from classes.virtual_clock import VirtualClock

# Function to calculate GMT+2 date and time from epoch absolute time
def get_current_gmt2_datetime():
    gmt2_offset = 2 * 3600  # GMT+2 offset in seconds
    epoch_time = time.time()
    gmt2_time = epoch_time + gmt2_offset
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(gmt2_time))

async def main():
    utils.logging_formatter.startup()
    utils.logging_formatter.test()

    schedule_keeper = ScheduleKeeper()
    virtual_clock = VirtualClock()

    gpio_setup_good: bool = wrapper.setup_gpio_pins()
    clock_sync_after_callbacks_enabled: Optional[bool] = utils.user_config.get(
        "clock_sync_after_callbacks_enabled", False)

    # ================# Local Functions #================ #

    # Note: Add lambdas here

    async def break_callback():
        utils.logger.info("Break callback triggered")
        await wrapper.callback_handler(False, gpio_setup_good)

        if clock_sync_after_callbacks_enabled:
            asyncio.create_task(virtual_clock.sync_time())

    async def work_callback():
        utils.logger.info("Work callback triggered")
        await wrapper.callback_handler(True, gpio_setup_good)

        if clock_sync_after_callbacks_enabled:
            asyncio.create_task(virtual_clock.sync_time())

    async def update():
        _schedule: List[str] = schedule_keeper.sync_schedule()
        utils.log_table(_schedule)

        await virtual_clock.sync_time()
        virtual_clock.set_timestamps(schedule_keeper.get_timestamps())

    # ================# Local Functions #================ #

    await update()

    # Note: remove after testing!
    # virtual_clock.current_time = datetime(2023, 9, 29, 6, 59, 55)
    virtual_clock.add_wb_callbacks(work_callback, break_callback)

    clock_task = asyncio.create_task(virtual_clock.start_t())
    sync_timestamps: Optional[List[str]] = utils.user_config.get(
        "sync_timestamps", [])

    if not sync_timestamps:
        utils.logger.warn("Sync timestamps are empty")
    else:
        timestamps: List[time] = []

        # Validate all sync timestamps
        for raw_timestamp in sync_timestamps:
            is_valid, timestamp = utils.is_valid_timestamp(raw_timestamp)

            if not is_valid:
                utils.logger.error(
                    "Invalid timestamp in user config: " + str(raw_timestamp))
                continue

            timestamps.append(timestamp)

        utils.log_table([[utils.to_string(timestamp)
                        for timestamp in timestamps]], [])

        virtual_clock.add_timestamp_callback(timestamps, update)

    await clock_task

if __name__ == "__main__":
    try:
        # wrapper.cleanup_gpio()
        asyncio.run(main())
    except Exception as e:
        print(e)
        wrapper.cleanup_gpio()
