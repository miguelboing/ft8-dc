#!/usr/bin/env python3
#
# plot_reports.py - Reception reports per timeframe for the power experiment
#
# Part of the ft8dc project: https://github.com/miguelboing/ft8dc
#
# -----------------------------------------------------------------------------
# WHAT THIS DOES
# -----------------------------------------------------------------------------
# Joins the transmission log produced by extra/power_experiment.py against the
# PSK Reporter dumps (https://pskreporter.info/csv/) and plots, for each of the
# three power levels (one dedicated callsign each), how many reception reports
# the CQ in every timeframe collected:
#
#       1 W  -> M7NSE
#      10 W  -> M7LSI
#      25 W  -> MB0LSI
#
#   x-axis : timeframe index (the system-model time slot)
#   y-axis : number of distinct receivers that reported that transmission
#
# MATCHING (how a report is attributed to a timeframe)
# Every burst keys exactly one 15 s FT8 slot, logged as `tx_slot_utc`. A spot in
# the PSK Reporter dump carries `flowStartSeconds`, the start of the 15 s slot in
# which it was decoded. A report is attributed to a burst when
#
#       floor(flowStartSeconds / 15) * 15  ==  tx_slot_utc      AND
#       senderCallsign                     ==  burst callsign
#
# Exact-slot matching (no +/-15 s tolerance) is deliberate: two bursts of the
# same callsign can be only 30 s apart, so a one-slot tolerance would be
# ambiguous between two different timeframes/power levels.
#
# The PSK Reporter dumps come in "_e" and "_o" halves and consecutive hourly
# files overlap, so reports are de-duplicated on (sender, receiver, slot) before
# counting -- the y value is therefore a count of *unique receivers*.
#
# -----------------------------------------------------------------------------
# HOW TO RUN
# -----------------------------------------------------------------------------
#   # auto-detect the log + every *_e/_o dump in extra/experiment/, show & save:
#   python extra/plot_reports.py
#
#   # point it at specific files / control output:
#   python extra/plot_reports.py --log path/to/power_experiment_*.csv \
#       --dumps extra/experiment/*.tsv.gz --out reports.png --no-show
# -----------------------------------------------------------------------------

import os
import csv
import gzip
import glob
import argparse
from collections import defaultdict
from datetime import datetime, timezone

import matplotlib
import matplotlib.pyplot as plt

# Power (W) -> dedicated callsign, mirrors extra/power_experiment.py.
POWER_CALLSIGNS = [
    (1,  "M7NSE"),
    (10, "M7LSI"),
    (25, "MB0LSI"),
]
CALL_TO_POWER = {c: p for p, c in POWER_CALLSIGNS}
OUR_CALLSIGNS = set(CALL_TO_POWER)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERIMENT_DIR = os.path.join(REPO_ROOT, "extra", "experiment")

# PSK Reporter TSV column order (the dumps carry a header row too).
COL_FLOWSTART = 0
COL_SENDER = 4
COL_RECEIVER = 6


def load_bursts(log_path):
    """Return {(callsign, slot_epoch): timeframe} and the set of timeframes.

    `slot_epoch` is the integer Unix timestamp of the burst's 15 s FT8 slot, so
    it can be compared directly against floor(flowStartSeconds / 15) * 15.
    """
    bursts = {}
    timeframes = set()
    with open(log_path, newline="") as f:
        for row in csv.DictReader(f):
            dt = datetime.strptime(row["tx_slot_utc"], "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
            tf = int(row["timeframe"])
            bursts[(row["callsign"], int(dt.timestamp()))] = tf
            timeframes.add(tf)
    return bursts, timeframes


def count_reports(dump_paths, bursts):
    """Count unique-receiver reports per (timeframe, callsign).

    Returns counts[(timeframe, callsign)] -> int and a small stats dict.
    """
    counts = defaultdict(int)
    seen = set()                      # (sender, receiver, slot) -> de-dup
    n_ours = n_matched = 0

    for path in dump_paths:
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt") as fh:
            next(fh, None)            # skip header row
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) <= COL_RECEIVER:
                    continue
                sender = parts[COL_SENDER]
                if sender not in OUR_CALLSIGNS:
                    continue
                try:
                    ts = int(parts[COL_FLOWSTART])
                except ValueError:
                    continue
                receiver = parts[COL_RECEIVER]
                slot = (ts // 15) * 15

                key = (sender, receiver, slot)
                if key in seen:
                    continue
                seen.add(key)
                n_ours += 1

                tf = bursts.get((sender, slot))
                if tf is None:
                    continue
                n_matched += 1
                counts[(tf, sender)] += 1

    stats = {"unique_reports": n_ours, "matched": n_matched,
             "unmatched": n_ours - n_matched}
    return counts, stats


def rolling_mean(y, window):
    """Centred moving average over `y`, shrinking the window at the edges.

    Edge points average only the timeframes that exist, so the smoothed curve
    spans the full x-range without NaN gaps or end artefacts.
    """
    n = len(y)
    half = window // 2
    out = []
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        seg = y[lo:hi]
        out.append(sum(seg) / len(seg))
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Plot reception reports per timeframe per power level")
    ap.add_argument("--log", default=None,
                    help="power_experiment_*.csv log (default: newest in extra/experiment/)")
    ap.add_argument("--dumps", nargs="+", default=None,
                    help="PSK Reporter TSV(.gz) dumps (default: all *_e/_o in extra/experiment/)")
    ap.add_argument("--out", default=os.path.join(EXPERIMENT_DIR, "reports_per_timeframe.png"),
                    help="output image path")
    ap.add_argument("--csv-out", default=None,
                    help="optional CSV of the per-timeframe counts")
    ap.add_argument("--smooth", type=int, default=9,
                    help="centred rolling-average window in timeframes; "
                         "0 disables the overlay (default: 9)")
    ap.add_argument("--no-show", action="store_true", help="don't open a window")
    args = ap.parse_args()

    log_path = args.log
    if log_path is None:
        candidates = sorted(glob.glob(os.path.join(EXPERIMENT_DIR, "power_experiment_*.csv")))
        if not candidates:
            ap.error(f"no power_experiment_*.csv found in {EXPERIMENT_DIR}; pass --log")
        log_path = candidates[-1]

    dump_paths = args.dumps
    if dump_paths is None:
        dump_paths = sorted(glob.glob(os.path.join(EXPERIMENT_DIR, "*_e.tsv.gz")) +
                            glob.glob(os.path.join(EXPERIMENT_DIR, "*_o.tsv.gz")))
        if not dump_paths:
            ap.error(f"no *_e/_o dumps found in {EXPERIMENT_DIR}; pass --dumps")

    print(f"Log   : {log_path}")
    print(f"Dumps : {len(dump_paths)} file(s)")
    for p in dump_paths:
        print(f"        {os.path.basename(p)}")

    bursts, timeframes = load_bursts(log_path)
    counts, stats = count_reports(dump_paths, bursts)

    print(f"\nBursts logged       : {len(bursts)} "
          f"({len(timeframes)} timeframes x {len(POWER_CALLSIGNS)} powers)")
    print(f"Unique reports (ours): {stats['unique_reports']}")
    print(f"  matched to a slot  : {stats['matched']}")
    print(f"  unmatched (skew)   : {stats['unmatched']}")

    tfs = sorted(timeframes)

    if args.csv_out:
        with open(args.csv_out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timeframe"] + [f"{p}W_{c}" for p, c in POWER_CALLSIGNS])
            for tf in tfs:
                w.writerow([tf] + [counts.get((tf, c), 0) for _, c in POWER_CALLSIGNS])
        print(f"\nPer-timeframe CSV   : {args.csv_out}")

    # --- plot -----------------------------------------------------------------
    if args.no_show:
        matplotlib.use("Agg")

    win = args.smooth if args.smooth and args.smooth > 1 else 0

    fig, ax = plt.subplots(figsize=(12, 5))
    for power, callsign in POWER_CALLSIGNS:
        y = [counts.get((tf, callsign), 0) for tf in tfs]
        total = sum(y)
        # Raw per-timeframe counts. Faded when a smoothed overlay is drawn on
        # top, full strength when it is the only curve.
        line, = ax.plot(tfs, y, marker=".", markersize=4, linewidth=1,
                        alpha=0.25 if win else 1.0,
                        label=None if win else f"{power} W  (n={total})")
        if win:
            ys = rolling_mean(y, win)
            ax.plot(tfs, ys, linewidth=2.2, color=line.get_color(),
                    label=f"{power} W  (n={total})")
    if win:
        ax.text(0.99, 0.97, f"lines: {win}-timeframe rolling mean",
                transform=ax.transAxes, ha="right", va="top", fontsize=8,
                color="0.4")

    ax.set_xlabel("Timeframe")
    ax.set_ylabel("Number of reception reports")
    ax.set_title("FT8 reception reports per timeframe by transmit power")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()

    fig.savefig(args.out, dpi=150)
    print(f"Figure saved        : {args.out}")
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
