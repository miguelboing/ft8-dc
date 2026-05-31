#!/usr/bin/env python3
#
# power_experiment.py - Sequential multi-power FT8 transmission experiment
#
# Part of the ft8dc project: https://github.com/miguelboing/ft8dc
#
# -----------------------------------------------------------------------------
# WHAT THIS DOES
# -----------------------------------------------------------------------------
# Every wall-clock minute is treated as one "timeframe" (the time slot of the
# system model). An FT8 minute is divided into four 15 s slots; this experiment
# uses the first three and leaves the fourth idle:
#
#     :00-:15  slot 0  ->  one of {1 W, 10 W, 25 W}
#     :15-:30  slot 1  ->  one of {1 W, 10 W, 25 W}
#     :30-:45  slot 2  ->  one of {1 W, 10 W, 25 W}
#     :45-:60  slot 3  ->  idle
#
# Each power level has its OWN callsign so that PSK Reporter spots can be
# attributed to a power without ambiguity:
#
#       1 W  -> M7NSE
#      10 W  -> M7LSI
#      25 W  -> MB0LSI
#
# The power -> slot assignment is counterbalanced with a 3-minute Latin square:
# within every block of 3 timeframes each power visits slot 0, slot 1 and slot 2
# exactly once. Over the whole run each power therefore lands in each slot an
# equal number of times, so slot/time position is decorrelated from power by
# construction (no power can benefit from a fixed slot). The base order of each
# block is randomized. The exact mapping for every transmission is written to a
# CSV log so it can later be joined against the PSK Reporter dumps
# (https://pskreporter.info/csv/...).
#
# Only a plain CQ is transmitted, e.g. "CQ M7NSE IO93". No ATU, single band
# (20 m / 14.074 MHz by default).
#
# -----------------------------------------------------------------------------
# HOW TO RUN  (rigctld must already be running, exactly like the main program)
# -----------------------------------------------------------------------------
#   # real run, 2 hours (120 timeframes):
#   python extra/power_experiment.py
#
#   # rehearse the schedule WITHOUT keying the radio (validates timing + CSV):
#   python extra/power_experiment.py --dry-run --minutes 5
#
#   # override duration / grid / band:
#   python extra/power_experiment.py --minutes 120 --grid IO93 --band 14074000
#
# Infrastructure values (CAT host/port, TX audio channel, sample rate) are read
# from config.toml, so this script stays consistent with the main application.
# -----------------------------------------------------------------------------

import os
import sys
import csv
import time
import random
import argparse
from datetime import datetime, timedelta, UTC

import numpy as np
import toml

# Make the repository root importable so that "transmission.*" resolves no
# matter the current working directory.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from transmission.radio_control.radio_control import RadioControl
from transmission.modulation.modulator import FT8Modulator

# -----------------------------------------------------------------------------
# Experiment configuration -- edit these if needed
# -----------------------------------------------------------------------------

# Power (Watts) -> dedicated callsign. One transmission per entry, per minute.
POWER_CALLSIGNS = [
    (1,  "M7NSE"),
    (10, "M7LSI"),
    (25, "MB0LSI"),
]

DEFAULT_MINUTES = 120          # 2 hours = 120 timeframes
DEFAULT_GRID = "IO93"          # Maidenhead locator used in the CQ message
DEFAULT_BAND_HZ = 14074000     # 20 m FT8 dial frequency
MAX_POWER_W = 100              # Rig's maximum RF power, used to scale RFPOWER

# Audio offset (Hz) inside the SSB passband. A fresh value is drawn each minute
# (shared by the three slots, which never overlap in time) to avoid sitting on a
# fixed sub-channel for the whole run.
AUDIO_OFFSET_MIN = 500
AUDIO_OFFSET_MAX = 2000

# Number of seconds before a minute boundary at which we arm the first slot.
# transmit_samples() internally waits for the *next* 15 s boundary, so we just
# need to be inside the idle slot (:45-:00) when we arm slot 0.
ARM_LEAD_SECONDS = 3

OUTPUT_DIR = os.path.join(REPO_ROOT, "dataset", "output", "power_experiment")


def log(msg):
    print(f"[{datetime.now(UTC).strftime('%H:%M:%S')}Z] {msg}", flush=True)


def sleep_until(target_dt):
    """Sleep (in short increments, so Ctrl-C stays responsive) until target_dt."""
    while True:
        delay = (target_dt - datetime.now(UTC)).total_seconds()
        if delay <= 0:
            return
        time.sleep(min(delay, 2.0))


def build_waveforms(modulator, grid, audio_offset, sample_rate):
    """Pre-generate the FT8 audio for each callsign for the upcoming minute."""
    waveforms = {}
    for _power, callsign in POWER_CALLSIGNS:
        signal = modulator.create_signal("CQ", callsign, grid, audio_offset, 0.0)
        waveforms[callsign] = modulator.generate_msg_samples(
            [signal], filename="", norm_factor=0.89, dtype=np.float32
        )
    return waveforms


def main():
    parser = argparse.ArgumentParser(description="Sequential multi-power FT8 experiment")
    parser.add_argument("--minutes", type=int, default=DEFAULT_MINUTES,
                        help="Number of 1-minute timeframes to run (default: 120 = 2h)")
    parser.add_argument("--grid", default=DEFAULT_GRID,
                        help="Maidenhead locator for the CQ message (default: IO93)")
    parser.add_argument("--band", type=int, default=DEFAULT_BAND_HZ,
                        help="Dial frequency in Hz (default: 14074000 = 20 m)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Rehearse the schedule and CSV without keying the radio")
    args = parser.parse_args()

    # Infrastructure parameters come from the shared config.toml.
    with open(os.path.join(REPO_ROOT, "config.toml"), "r") as f:
        cfg = toml.load(f)["general_config"]

    cat_port = f"{cfg['cat_tcp_server']}:{cfg['cat_tcp_port']}"
    tx_audio_channel = cfg["tx_audio_channel"]
    sample_rate = cfg["sample_rate"]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_path = os.path.join(
        OUTPUT_DIR,
        f"power_experiment_{datetime.now(UTC).strftime('%Y%m%d_%H%M%SZ')}.csv",
    )

    log("=== FT8 sequential multi-power experiment ===")
    log(f"Timeframes : {args.minutes} minute(s)")
    log(f"Band       : {args.band} Hz   Grid: {args.grid}")
    log(f"Powers     : " + ", ".join(f"{p}W={c}" for p, c in POWER_CALLSIGNS))
    log(f"Audio dev  : {tx_audio_channel}   Sample rate: {sample_rate} Hz")
    log(f"CSV log    : {csv_path}")
    if args.dry_run:
        log("DRY RUN: the radio will NOT be keyed.")

    modulator = FT8Modulator(sample_rate=sample_rate)

    radio = None
    if not args.dry_run:
        radio = RadioControl(port=cat_port, max_power_W=MAX_POWER_W)
        radio.rx_mode()
        if radio.set_mode(mode="USB", passband=-1) != 0:
            log("WARNING: failed to confirm USB mode.")
        if radio.set_if_frequency(args.band) != 0:
            log("WARNING: failed to confirm dial frequency.")

    csv_file = open(csv_path, "w", newline="")
    writer = csv.writer(csv_file)
    writer.writerow([
        "timeframe", "block", "minute_start_utc", "slot", "slot_start_utc",
        "power_w", "callsign", "message", "band_hz", "audio_offset_hz",
        "tx_power_set_ok",
    ])
    csv_file.flush()

    # Anchor every timeframe to the top of the next full minute.
    now = datetime.now(UTC)
    first_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    log(f"Aligning to first timeframe at {first_minute.strftime('%H:%M:%S')}Z ...")

    base_order = None  # base power order for the current 3-minute Latin-square block

    try:
        for tf in range(args.minutes):
            minute_start = first_minute + timedelta(minutes=tf)

            # Prepare this minute's waveforms and slot order during the idle
            # window of the previous minute (or the initial alignment wait).
            audio_offset = random.randint(AUDIO_OFFSET_MIN, AUDIO_OFFSET_MAX)
            waveforms = None
            if not args.dry_run:
                waveforms = build_waveforms(modulator, args.grid, audio_offset, sample_rate)
                # Re-assert band/mode each minute in case the rig drifted.
                radio.set_mode(mode="USB", passband=-1)
                radio.set_if_frequency(args.band)

            # Counterbalanced rotation: a fresh random base order at the start of
            # each 3-minute block, then a cyclic shift per minute so each power
            # visits each slot exactly once across the block.
            block, row = divmod(tf, len(POWER_CALLSIGNS))
            if row == 0:
                base_order = POWER_CALLSIGNS[:]
                random.shuffle(base_order)
            order = base_order[row:] + base_order[:row]

            log(f"--- Timeframe {tf + 1}/{args.minutes} (block {block}, row {row}) "
                f"@ {minute_start.strftime('%H:%M')}Z "
                f"offset={audio_offset}Hz order={[p for p, _ in order]}W ---")

            # Arm slot 0: be inside the idle slot so the internal 15 s alignment
            # in transmit_samples() lands us exactly on the minute boundary.
            sleep_until(minute_start - timedelta(seconds=ARM_LEAD_SECONDS))

            for slot, (power, callsign) in enumerate(order):
                slot_start = minute_start + timedelta(seconds=slot * 15)
                message = f"CQ {callsign} {args.grid}"
                tx_power_ok = True

                if args.dry_run:
                    # Just respect the slot boundary and record the plan.
                    sleep_until(slot_start)
                    log(f"  [dry] slot {slot} {power:>2}W {callsign:<7} \"{message}\"")
                else:
                    try:
                        if radio.set_tx_power(power) != 0:
                            tx_power_ok = False
                            log(f"  WARNING: could not confirm {power}W for {callsign}.")
                    except Exception as e:  # rigctl/subprocess failure
                        tx_power_ok = False
                        log(f"  WARNING: set_tx_power({power}) raised: {e}")

                    log(f"  slot {slot} {power:>2}W {callsign:<7} \"{message}\" -> TX")
                    # Internally waits for the next 15 s boundary, keys PTT,
                    # plays the ~12.6 s FT8 burst, then returns to RX.
                    radio.transmit_samples(
                        filename="",
                        samples=waveforms[callsign],
                        sample_rate=sample_rate,
                        audio_device=tx_audio_channel,
                    )

                writer.writerow([
                    tf, block, minute_start.strftime("%Y-%m-%d %H:%M:%S"), slot,
                    slot_start.strftime("%Y-%m-%d %H:%M:%S"), power, callsign,
                    message, args.band, audio_offset, tx_power_ok,
                ])
                csv_file.flush()

            # Slot 3 stays idle; the next iteration sleeps past :45 to :00,
            # which both skips the idle slot and re-aligns slot 0.

        log("Experiment finished. All timeframes transmitted.")

    except KeyboardInterrupt:
        log("Interrupted by user -- stopping.")
    finally:
        csv_file.close()
        if radio is not None:
            radio.rx_mode()
        log(f"CSV saved to {csv_path}")


if __name__ == "__main__":
    main()
