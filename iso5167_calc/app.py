"""
ISO 5167-2 — Flask Web Server
==============================
Serves the orifice plate calculator at http://localhost:5167
and exposes a REST API at /api/calculate for server-side computation.

Run:
    python app.py
"""

import math
import threading
import time
import webbrowser

from flask import Flask, jsonify, render_template, request

from calculator import (
    GasFluid,
    LiquidFluid,
    M_AIR,
    P_STD,
    R_UNIV,
    T_STD_K,
    measurement_uncertainty,
    solve_dP_to_Q,
    solve_Q_to_dP,
    validity_checks,
)

# ── App ───────────────────────────────────────────────────────────────────────
app = Flask(__name__)
PORT = 5167


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def calculate():
    """
    POST /api/calculate
    Body (JSON):
    {
        "mode":      "Q_dP" | "dP_Q",
        "fluid":     "gas" | "liquid",
        "tap":       "flange" | "corner" | "DandD2",
        "D_mm":      102.26,
        "d_mm":      30.73,
        "P1_kPa":    3000,
        "T1_C":      40,
        // gas fields
        "gamma":     0.65,
        "Z":         0.88,
        "kappa":     1.27,
        "mu_cP":     0.012,
        "Q_sm3d":    50000,   // Q_dP mode, gas
        // liquid fields
        "rho":       850,
        "mu_liq_cP": 2.0,
        "Q_m3h":     30,      // Q_dP mode, liquid
        // dP_Q mode
        "dP_kPa":    12.5,
        // instrument
        "dp_urv":    25,
        "dp_lrv":    0,
        "dp_unc_pct":0.1,
        "d_unc_mm":  0.05
    }
    """
    try:
        d = request.get_json(force=True)

        mode    = d.get("mode", "Q_dP")
        tap     = d.get("tap",  "flange")
        D_mm    = float(d["D_mm"])
        d_mm    = float(d["d_mm"])
        P1_Pa   = float(d["P1_kPa"]) * 1000
        T1_K    = float(d["T1_C"]) + 273.15
        dp_urv  = float(d.get("dp_urv",  25))
        dp_lrv  = float(d.get("dp_lrv",  0))
        dp_unc  = float(d.get("dp_unc_pct", 0.1))
        d_unc   = float(d.get("d_unc_mm",   0.05))
        dp_span = (dp_urv - dp_lrv) * 1000  # Pa

        # Build fluid
        is_gas = d.get("fluid", "gas") == "gas"
        if is_gas:
            gamma = float(d.get("gamma", 0.65))
            fluid = GasFluid(
                gamma  = gamma,
                Z      = float(d.get("Z", 0.88)),
                kappa  = float(d.get("kappa", 1.27)),
                mu_cP  = float(d.get("mu_cP", 0.012)),
            )
        else:
            gamma = 0
            fluid = LiquidFluid(
                rho   = float(d.get("rho", 850)),
                mu_cP = float(d.get("mu_liq_cP", 2.0)),
            )

        # Compute
        if mode == "Q_dP":
            if is_gas:
                Q_sm3d = float(d.get("Q_sm3d", 50000))
                qm_kgs = Q_sm3d * fluid.density_std() / 86_400
            else:
                Q_m3h  = float(d.get("Q_m3h", 30))
                rho1   = fluid.density(P1_Pa, T1_K)
                qm_kgs = rho1 * Q_m3h / 3600

            res = solve_Q_to_dP(qm_kgs, D_mm, d_mm, fluid, P1_Pa, T1_K, tap)
            dP_Pa = res["dP_Pa"]

        else:  # dP_Q
            dP_Pa = float(d.get("dP_kPa", 12.5)) * 1000
            res   = solve_dP_to_Q(dP_Pa, D_mm, d_mm, fluid, P1_Pa, T1_K, tap)
            qm_kgs = res["qm_kgs"]

        beta = res["beta"]
        Cd   = res["Cd"]
        Y    = res["Y"]
        Ev   = res["Ev"]
        ReD  = res["ReD"]
        rho1 = res["rho1"]

        # % of transmitter span
        pct_span = (dP_Pa - dp_lrv * 1000) / dp_span * 100 if dp_span > 0 else 0

        # Flow range at 100% and 20% FS
        def qm_to_q(qm, gamma_val, rho1_val):
            if is_gas:
                return qm * 86_400 / fluid.density_std()
            return qm / rho1_val * 3600

        res_100 = solve_dP_to_Q(dp_span,        D_mm, d_mm, fluid, P1_Pa, T1_K, tap)
        res_20  = solve_dP_to_Q(dp_span * 0.20, D_mm, d_mm, fluid, P1_Pa, T1_K, tap)

        Q_op   = qm_to_q(qm_kgs,          gamma, rho1)
        Q_100  = qm_to_q(res_100["qm_kgs"], gamma, rho1)
        Q_20   = qm_to_q(res_20["qm_kgs"],  gamma, rho1)
        Q_unit = "Sm³/d" if is_gas else "m³/h"

        turndown = Q_100 / Q_20 if Q_20 > 0 else 0

        # Uncertainty
        unc = measurement_uncertainty(
            beta, Cd, Y, ReD, dP_Pa, P1_Pa, is_gas,
            d_unc, d_mm, dp_unc, dp_span
        )

        # ISO checks
        chk = validity_checks(beta, ReD, D_mm, tap, dP_Pa, P1_Pa, is_gas, Cd)

        # Global status
        states  = [c["status"] for c in chk]
        dp_stat = ("ok" if 20<=pct_span<=80 else "warn" if 10<=pct_span<=90 else "bad")
        states.append(dp_stat)
        if "bad"  in states: global_status = "nogo"
        elif "warn" in states: global_status = "warn"
        else:                  global_status = "go"

        return jsonify({
            "ok": True,
            # geometry
            "beta": beta,
            "D_mm": D_mm,
            "d_mm": d_mm,
            # orifice params
            "Cd": Cd,
            "Ev": Ev,
            "Y":  Y,
            "ReD": ReD,
            "rho1_kgm3": rho1,
            # main output
            "dP_Pa":  dP_Pa,
            "dP_kPa": dP_Pa / 1000,
            "qm_kgs": qm_kgs,
            "qm_kgh": qm_kgs * 3600,
            "Q_op":   Q_op,
            "Q_unit": Q_unit,
            # transmitter
            "pct_span": pct_span,
            "dp_status": dp_stat,
            # flowrate range
            "Q_100":    Q_100,
            "Q_20":     Q_20,
            "turndown": turndown,
            # quality
            "uncertainty": unc,
            "checks":      chk,
            "status":      global_status,
        })

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "port": PORT})


# ── Launch ────────────────────────────────────────────────────────────────────
def _open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    print("=" * 55)
    print("  ISO 5167-2  Placa de Orifício — Calculadora")
    print(f"  http://localhost:{PORT}")
    print("=" * 55)
    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False)
