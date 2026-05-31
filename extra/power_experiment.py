#!/usr/bin/env python3
#
# power_experiment.py - Sequential multi-power FT8 transmission experiment
#
# Part of the ft8dc project: https://github.com/miguelboing/ft8dc
#
# -----------------------------------------------------------------------------
# WHAT THIS DOES
# -----------------------------------------------------------------------------
# Transmits a plain CQ at three power levels, each with its OWN callsign so that
# PSK Reporter spots can be attributed to a power without ambiguity:
#
#       1 W  -> M7NSE
#      10 W  -> M7LSI
#      25 W  -> MB0LSI
#
# CADENCE (important):
# An FT8 burst occupies the *entire* 15 s slot (the generated audio buffer is a
# full 15 s long), and switching RF power over CAT + cycling PTT between bursts
# takes a second or two. There is therefore no room to transmit in consecutive
# 15 s slots: in practice each burst lands on every *other* slot, i.e. one burst
# every 30 s (:00, :30, :00, ...). This script embraces that: it transmits one
# burst every 30 s and never tries to pack three into a single clock minute.
#
# A "timeframe" (the time slot of the system model) is therefore one ROUND of
# three transmissions, one per power level, spanning 90 s.
#
# COUNTERBALANCING:
# Within every block of 3 timeframes the power -> position assignment follows a
# randomized 3-minute Latin square: each power occupies position 0, 1 and 2
# exactly once per block. Over the whole run each power lands in each position an
# equal number of times, so position/time is decorrelated from power by
# construction. The ACTUAL UTC slot of every burst is written to the CSV log so
# it can be joined against the PSK Reporter dumps (https://pskreporter.info/csv/).
#
# Only a plain CQ is transmitted, e.g. "CQ M7NSE IO93". No ATU, single band
# (20 m / 14.074 MHz by default).
#
# -----------------------------------------------------------------------------
# HOW TO RUN  (rigctld must already be running, exactly like the main program)
# -----------------------------------------------------------------------------
#   # real run, ~2 hours:
#   python extra/power_experiment.py
#
#   # rehearse the schedule WITHOUT keying the radio (validates timing + CSV):
#   python extra/power_experiment.py --dry-run --minutes 6
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

# Power (Watts) -> dedicated callsign. One transmission per entry, per timeframe.
POWER_CALLSIGNS = [
    (1,  "M7NSE"),
    (10, "M7LSI"),
    (25, "MB0LSI"),
]

DEFAULT_MINUTES = 120          # approximate wall-clock duration of the run
DEFAULT_GRID = "IO93"          # Maidenhead locator used in the CQ message
DEFAULT_BAND_HZ = 14074000     # 20 m FT8 dial frequency
MAX_POWER_W = 100              # Rig's maximum RF power, used to scale RFPOWER

# One burst every 30 s -> a 3-power timeframe lasts 90 s.
SLOT_PERIOD_S = 30
TIMEFRAME_S = SLOT_PERIOD_S * len(POWER_CALLSIGNS)

# Audio offset (Hz) inside the SSB passband. A fresh value is drawn each
# timeframe to avoid sitting on a fixed sub-channel for the whole run.
AUDIO_OFFSET_MIN = 500
AUDIO_OFFSET_MAX = 2000

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


def next_15s_boundary(now):
    """Next FT8 slot boundary at or after `now` -- mirrors RadioControl.

    RadioControl.wait_until_next_15s() always advances to the *next* multiple of
    15 s, so this is the slot a transmit_samples() call started now will key on.
    """
    seconds = ((now.second // 15) + 1) * 15
    if seconds == 60:
        return now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return now.replace(second=seconds, microsecond=0)


def build_waveforms(modulator, grid, audio_offset, sample_rate):
    """Pre-generate the FT8 audio for each callsign for the upcoming timeframe."""
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
                        help="Approximate wall-clock duration in minutes (default: 120)")
    parser.add_argument("--grid", default=DEFAULT_GRID,
                        help="Maidenhead locator for the CQ message (default: IO93)")
    parser.add_argument("--band", type=int, default=DEFAULT_BAND_HZ,
                        help="Dial frequency in Hz (default: 14074000 = 20 m)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Rehearse the schedule and CSV without keying the radio")
    args = parser.parse_args()

    # Each timeframe is 3 bursts x 30 s = 90 s; derive how many fit the duration.
    n_timeframes = max(1, (args.minutes * 60) // TIMEFRAME_S)

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
    log(f"Timeframes : {n_timeframes}  (~{n_timeframes * TIMEFRAME_S / 60:.0f} min, "
        f"{n_timeframes * len(POWER_CALLSIGNS)} bursts @ {SLOT_PERIOD_S}s spacing)")
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
        "timeframe", "block", "slot", "tx_slot_utc",
        "power_w", "callsign", "message", "band_hz", "audio_offset_hz",
        "tx_power_set_ok",
    ])
    csv_file.flush()

    base_order = None  # base power order for the current Latin-square block

    try:
        for tf in range(n_timeframes):
            # Counterbalanced rotation: a fresh random base order at the start of
            # each block of 3 timeframes, then a cyclic shift per timeframe so
            # each power visits each position exactly once across the block.
            block, row = divmod(tf, len(POWER_CALLSIGNS))
            if row == 0:
                base_order = POWER_CALLSIGNS[:]
                random.shuffle(base_order)
            order = base_order[row:] + base_order[:row]

            audio_offset = random.randint(AUDIO_OFFSET_MIN, AUDIO_OFFSET_MAX)
            waveforms = None
            if not args.dry_run:
                waveforms = build_waveforms(modulator, args.grid, audio_offset, sample_rate)

            log(f"--- Timeframe {tf + 1}/{n_timeframes} (block {block}, row {row}) "
                f"offset={audio_offset}Hz order={[p for p, _ in order]}W ---")

            for slot, (power, callsign) in enumerate(order):
                message = f"CQ {callsign} {args.grid}"
                tx_power_ok = True

                if args.dry_run:
                    # Mimic the real cadence: wait for the slot, then occupy a
                    # full 15 s burst so the next one lands ~30 s later.
                    tx_slot = next_15s_boundary(datetime.now(UTC))
                    sleep_until(tx_slot)
                    log(f"  [dry] slot {slot} {power:>2}W {callsign:<7} "
                        f"\"{message}\" @ {tx_slot.strftime('%H:%M:%S')}Z")
                    sleep_until(tx_slot + timedelta(seconds=15))
                else:
                    try:
                        if radio.set_tx_power(power) != 0:
                            tx_power_ok = False
                            log(f"  WARNING: could not confirm {power}W for {callsign}.")
                    except Exception as e:  # rigctl/subprocess failure
                        tx_power_ok = False
                        log(f"  WARNING: set_tx_power({power}) raised: {e}")

                    # transmit_samples() internally waits for the next 15 s
                    # boundary; record exactly which slot that will be.
                    tx_slot = next_15s_boundary(datetime.now(UTC))
                    log(f"  slot {slot} {power:>2}W {callsign:<7} \"{message}\" "
                        f"-> TX @ {tx_slot.strftime('%H:%M:%S')}Z")
                    radio.transmit_samples(
                        filename="",
                        samples=waveforms[callsign],
                        sample_rate=sample_rate,
                        audio_device=tx_audio_channel,
                    )

                writer.writerow([
                    tf, block, slot,
                    tx_slot.strftime("%Y-%m-%d %H:%M:%S"), power, callsign,
                    message, args.band, audio_offset, tx_power_ok,
                ])
                csv_file.flush()

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
