"""Build normative_reference.json from the normative tester sessions export.

Usage:
    python scripts/build_normative_reference.py "normative_sessions_rows.csv"

Method
------
1. Capture-failure exclusion: sessions whose mean inter-key interval
   (task flight_time_mean or calibration kbase_mean) is below 30 ms are
   dropped. Sustained human inter-key intervals are well above this
   (Dhakal et al., 2018, CHI: 136M keystrokes, fastest typists ~120 ms), so
   such values indicate a logging failure, not behaviour.
2. Independence: one session per tester (the earliest valid one). Repeat
   sessions are not independent and carry practice effects.
3. Healthy reference: testers screening positive on PHQ-9 >= 10
   (Kroenke et al., 2001) or GAD-7 >= 10 (Spitzer et al., 2006) are excluded.
4. High-but-plausible values are kept: trimming them would understate
   healthy variability and inflate false alarms.
5. Cut-offs: the 95th/99th percentiles of the healthy distribution, estimated
   with the Harrell-Davis quantile estimator (Harrell & Davis, 1982), which is
   markedly more efficient than the sample quantile at n < 100. Percentile
   bootstrap 95% CIs (B = 5000) are reported for transparency.
6. Population comparison uses empirical mid-rank percentiles, because T²,
   PSI and PAI are strongly right-skewed and a normal-curve percentile would
   misstate them.

The T² values in the export were produced by the ipsative (within-session
EWMA) Hotelling T², so these cut-offs calibrate the ipsative T².
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats.mstats import hdquantiles

MIN_IKI_S = 0.03
SCREEN_CUTOFF = 10
METRICS = ["t2_score", "psi", "pai", "phq_score", "gad_score", "flight_time_mean"]
QUANTILES = [0.05, 0.25, 0.50, 0.75, 0.95, 0.99]
OUT = Path(__file__).resolve().parent.parent / "normative_reference.json"


def hd(values, probs):
    return [float(v) for v in hdquantiles(np.asarray(values, float), probs)]


def bootstrap_ci(values, prob, b=5000, seed=2026):
    rng = np.random.default_rng(seed)
    values = np.asarray(values, float)
    est = [hd(rng.choice(values, len(values), replace=True), [prob])[0] for _ in range(b)]
    return [float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))]


def main(csv_path):
    df = pd.read_csv(csv_path)
    df["ts"] = pd.to_datetime(df["timestamp"], format="mixed", utc=True)
    df = df.sort_values(["ts", "id"])
    n_rows, n_testers = len(df), df["tester_id"].nunique()

    capture_fail = (df["flight_time_mean"] < MIN_IKI_S) | (df["kbase_mean"] < MIN_IKI_S)
    valid = df[~capture_fail]
    first = valid.groupby("tester_id", as_index=False).first()
    screen_pos = (first["phq_score"] >= SCREEN_CUTOFF) | (first["gad_score"] >= SCREEN_CUTOFF)
    healthy = first[~screen_pos]

    metrics = {}
    for m in METRICS:
        v = healthy[m].astype(float).values
        metrics[m] = {
            "n": int(len(v)),
            "mean": float(v.mean()),
            "sd": float(v.std(ddof=1)),
            "quantiles_hd": dict(zip([f"p{int(q * 100):02d}" for q in QUANTILES], hd(v, QUANTILES))),
            "values": sorted(float(x) for x in v),
        }

    item_t2 = [float(x) for s in healthy["domain_t2_json"] for x in json.loads(s).values()]
    t2 = healthy["t2_score"].astype(float).values
    session_p95, session_p99 = hd(t2, [0.95, 0.99])
    item_p95, item_p99 = hd(item_t2, [0.95, 0.99])

    ref = {
        "source": Path(csv_path).name,
        "method": __doc__.strip().split("Method\n------\n")[1],
        "counts": {
            "sessions_exported": n_rows,
            "distinct_testers": n_testers,
            "excluded_capture_failure_sessions": int(capture_fail.sum()),
            "excluded_repeat_sessions": int(len(valid) - len(first)),
            "excluded_screen_positive_testers": int(screen_pos.sum()),
            "healthy_reference_testers": int(len(healthy)),
        },
        "thresholds": {
            "session": {
                "p95": session_p95, "p99": session_p99,
                "p95_ci95": bootstrap_ci(t2, 0.95), "p99_ci95": bootstrap_ci(t2, 0.99),
            },
            "item": {
                "p95": item_p95, "p99": item_p99,
                "n_values": len(item_t2),
                "note": "Pooled per-domain mean item T² (4 per tester).",
            },
            "psi_p99": metrics["psi"]["quantiles_hd"]["p99"],
            "pai_p99": metrics["pai"]["quantiles_hd"]["p99"],
        },
        "metrics": metrics,
    }
    OUT.write_text(json.dumps(ref, indent=2), encoding="utf-8")
    print(json.dumps({k: ref[k] for k in ("counts", "thresholds")}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
