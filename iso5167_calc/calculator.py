"""
ISO 5167-2 : 2022 — Orifice Plate Calculator
==============================================
Python module implementing the Reader-Harris/Gallagher (RHG) discharge
coefficient equation, expansion factor Y, and uncertainty estimation.

Usage:
    from calculator import solve_Q_to_dP, solve_dP_to_Q, GasFluid, LiquidFluid

Author: ISO 5167 Python Module
"""

import math
from dataclasses import dataclass, field
from typing import Literal

# ── Constants ────────────────────────────────────────────────────────────────
R_UNIV  = 8314.46    # J / (kmol·K)
M_AIR   = 28.9647    # kg/kmol
T_STD_K = 293.15     # 20 °C  (standard conditions)
P_STD   = 101_325.0  # Pa     (standard conditions)


# ── Fluid descriptors ────────────────────────────────────────────────────────
@dataclass
class GasFluid:
    """Natural gas or any compressible gas."""
    gamma:    float        # Specific gravity relative to air (air = 1.0)
    Z:        float = 0.88 # Compressibility factor at operating conditions
    kappa:    float = 1.27 # Isentropic exponent (≈1.27 natural gas, 1.4 air)
    mu_cP:    float = 0.012 # Dynamic viscosity [cP]

    @property
    def M(self) -> float:
        """Molecular weight [kg/kmol]."""
        return self.gamma * M_AIR

    def density(self, P_Pa: float, T_K: float) -> float:
        """Operating density [kg/m³] from real-gas equation."""
        return P_Pa * self.M / (self.Z * R_UNIV * T_K)

    def density_std(self) -> float:
        """Density at standard conditions (20 °C, 101325 Pa, Z=1) [kg/m³]."""
        return P_STD * self.M / (R_UNIV * T_STD_K)

    @property
    def mu_Pas(self) -> float:
        return self.mu_cP * 1e-3


@dataclass
class LiquidFluid:
    """Incompressible liquid (oil, water, etc.)."""
    rho:   float         # Density [kg/m³]
    mu_cP: float = 2.0   # Dynamic viscosity [cP]

    def density(self, P_Pa: float = 0, T_K: float = 0) -> float:
        return self.rho

    @property
    def mu_Pas(self) -> float:
        return self.mu_cP * 1e-3


# ── Tap-type L1 / L2' parameters (ISO 5167-2 Table 1) ───────────────────────
TAP_PARAMS = {
    "flange": lambda D_mm: (25.4 / D_mm, 25.4 / D_mm),
    "corner": lambda D_mm: (0.0, 0.0),
    "DandD2": lambda D_mm: (1.0, 0.47),
}

TapType = Literal["flange", "corner", "DandD2"]


# ── Core ISO 5167-2 equations ─────────────────────────────────────────────────
def discharge_coefficient(
    beta: float,
    ReD:  float,
    D_mm: float,
    tap:  TapType = "flange",
) -> float:
    """
    Reader-Harris/Gallagher (RHG) discharge coefficient.
    ISO 5167-2:2022, Equation (1).

    Parameters
    ----------
    beta  : d/D ratio
    ReD   : pipe Reynolds number  ρ·v·D/μ
    D_mm  : pipe internal diameter [mm]
    tap   : tap type ('flange', 'corner', 'DandD2')
    """
    ReD = max(ReD, 10.0)
    L1, L2p = TAP_PARAMS[tap](D_mm)

    A   = (19_000 * beta / ReD) ** 0.8
    M2p = 2 * L2p / (1 - beta) if L2p > 0 else 0.0

    C = (
        0.5961
        + 0.0261  * beta ** 2
        - 0.216   * beta ** 8
        + 0.000521 * (1e6 * beta / ReD) ** 0.7
        + (0.0188 + 0.0063 * A) * beta ** 3.5 * (1e6 / ReD) ** 0.3
        + (0.043 + 0.080 * math.exp(-10 * L1) - 0.123 * math.exp(-7 * L1))
          * (1 - 0.11 * A) * beta ** 4 / (1 - beta ** 4)
    )

    if M2p > 0:
        C -= 0.031 * (M2p - 0.8 * M2p ** 1.1) * beta ** 1.3

    # Small-D correction (ISO 5167-2, clause 5.1.2)
    if D_mm < 71.12:
        C += 0.011 * (0.75 - beta) * (2.8 - D_mm / 25.4)

    return C


def expansion_factor(
    beta:  float,
    dP_Pa: float,
    P1_Pa: float,
    kappa: float,
) -> float:
    """
    Gas expansion factor Y.
    ISO 5167-2:2022, Equation (7).
    Valid for ΔP/P₁ ≤ 0.25.
    Returns 1.0 for liquids (just pass kappa=0 or dP_Pa=0).
    """
    if dP_Pa <= 0 or P1_Pa <= 0:
        return 1.0
    tau = dP_Pa / P1_Pa
    if tau >= 1.0:
        return 0.5
    return 1 - (0.351 + 0.256 * beta ** 4 + 0.93 * beta ** 8) * (
        1 - (1 - tau) ** (1 / kappa)
    )


def velocity_approach_factor(beta: float) -> float:
    """Ev = 1 / √(1 − β⁴)."""
    return 1.0 / math.sqrt(1 - beta ** 4)


def reynolds_number(qm_kgs: float, D_m: float, mu_Pas: float) -> float:
    """Re_D = 4·qm / (π·D·μ)."""
    return 4 * qm_kgs / (math.pi * D_m * mu_Pas)


# ── Solvers ──────────────────────────────────────────────────────────────────
def solve_Q_to_dP(
    qm_kgs: float,
    D_mm:   float,
    d_mm:   float,
    fluid,
    P1_Pa:  float,
    T1_K:   float,
    tap:    TapType = "flange",
) -> dict:
    """
    Given mass flowrate → find differential pressure.

    For gas: only Y needs iteration (C is fixed once Re is known from qm).
    Converges in ~5 iterations.
    """
    D = D_mm / 1000
    d = d_mm / 1000
    beta = d / D
    A_d  = math.pi / 4 * d ** 2
    Ev   = velocity_approach_factor(beta)

    is_gas = isinstance(fluid, GasFluid)
    rho1   = fluid.density(P1_Pa, T1_K)
    mu     = fluid.mu_Pas
    kappa  = fluid.kappa if is_gas else 1.0

    # Re is fixed for known qm
    ReD = reynolds_number(qm_kgs, D, mu)
    Cd  = discharge_coefficient(beta, ReD, D_mm, tap)

    # Iterate only Y (gas compressibility)
    Y  = 1.0
    dP = 0.0
    for _ in range(30):
        prev = dP
        dP = (qm_kgs / (Cd * Ev * Y * A_d)) ** 2 / (2 * rho1)
        if is_gas:
            Y = expansion_factor(beta, dP, P1_Pa, kappa)
        if abs(dP - prev) < 1e-6:
            break

    return {
        "dP_Pa": dP,
        "dP_kPa": dP / 1000,
        "Cd": Cd,
        "Ev": Ev,
        "Y": Y,
        "ReD": ReD,
        "beta": beta,
        "rho1": rho1,
        "qm_kgs": qm_kgs,
        "qm_kgh": qm_kgs * 3600,
    }


def solve_dP_to_Q(
    dP_Pa:  float,
    D_mm:   float,
    d_mm:   float,
    fluid,
    P1_Pa:  float,
    T1_K:   float,
    tap:    TapType = "flange",
) -> dict:
    """
    Given differential pressure → find mass flowrate.

    Iterates both Cd and Y until convergence.
    """
    D = D_mm / 1000
    d = d_mm / 1000
    beta = d / D
    A_d  = math.pi / 4 * d ** 2
    Ev   = velocity_approach_factor(beta)

    is_gas = isinstance(fluid, GasFluid)
    rho1   = fluid.density(P1_Pa, T1_K)
    mu     = fluid.mu_Pas
    kappa  = fluid.kappa if is_gas else 1.0

    Cd = 0.606
    Y  = 1.0
    qm = 0.0

    for _ in range(40):
        pCd, pY = Cd, Y
        if is_gas:
            Y = expansion_factor(beta, dP_Pa, P1_Pa, kappa)
        qm  = Cd * Ev * Y * A_d * math.sqrt(2 * dP_Pa * rho1)
        ReD = reynolds_number(qm, D, mu)
        Cd  = discharge_coefficient(beta, ReD, D_mm, tap)
        if abs(Cd - pCd) < 1e-8 and abs(Y - pY) < 1e-8:
            break

    ReD = reynolds_number(qm, D, mu)

    return {
        "qm_kgs": qm,
        "qm_kgh": qm * 3600,
        "dP_Pa": dP_Pa,
        "dP_kPa": dP_Pa / 1000,
        "Cd": Cd,
        "Ev": Ev,
        "Y": Y,
        "ReD": ReD,
        "beta": beta,
        "rho1": rho1,
    }


# ── Uncertainty (ISO 5167-2 Annex B, RSS) ────────────────────────────────────
def measurement_uncertainty(
    beta:          float,
    Cd:            float,
    Y:             float,
    ReD:           float,
    dP_Pa:         float,
    P1_Pa:         float,
    is_gas:        bool,
    d_unc_mm:      float,
    d_mm:          float,
    dp_unc_pct_fs: float,
    dp_span_Pa:    float,
) -> dict:
    """
    Expanded measurement uncertainty (k=2, ~95% confidence).
    ISO 5167-2:2022 Annex B, RSS method.
    """
    # Cd uncertainty (Table 2)
    if beta <= 0.20:
        u_Cd = 0.007
    elif beta <= 0.60:
        u_Cd = 0.005
    elif beta <= 0.75:
        u_Cd = beta / 60
    else:
        u_Cd = 0.013

    # Velocity approach (Ev) — negligible contribution
    u_Ev = beta ** 4 / (1 - beta ** 4) * 0.001

    # Y expansion factor (gas only)
    kappa_ref = 1.27
    u_Y = abs(4 * dP_Pa / (P1_Pa * kappa_ref) * 0.01) if is_gas and P1_Pa > 0 else 0.0

    # Orifice diameter d: 2 × δd/d
    u_d = 2 * (d_unc_mm / d_mm)

    # Differential pressure transmitter: 0.5 × δΔP/ΔP
    u_dP = 0.5 * (dp_unc_pct_fs / 100 * dp_span_Pa / dP_Pa) if dP_Pa > 0 else 0.01

    # RSS total (expanded, k=2)
    u_total = math.sqrt(u_Cd**2 + u_Ev**2 + u_Y**2 + u_d**2 + u_dP**2) * 100

    return {
        "u_total_pct": u_total,
        "u_Cd_pct":    u_Cd  * 100,
        "u_Ev_pct":    u_Ev  * 100,
        "u_Y_pct":     u_Y   * 100,
        "u_d_pct":     u_d   * 100,
        "u_dP_pct":    u_dP  * 100,
    }


# ── ISO validity checks ───────────────────────────────────────────────────────
def validity_checks(
    beta:   float,
    ReD:    float,
    D_mm:   float,
    tap:    TapType,
    dP_Pa:  float,
    P1_Pa:  float,
    is_gas: bool,
    Cd:     float,
) -> list[dict]:
    """
    Returns a list of ISO 5167-2 validity criteria with pass/warn/fail status.
    """
    checks = []
    tau = dP_Pa / P1_Pa if P1_Pa > 0 else 0

    # β range
    b_ok    = 0.10 <= beta <= 0.75
    b_ideal = 0.20 <= beta <= 0.65
    checks.append({
        "name": "Beta ratio β",
        "value": f"{beta:.4f}",
        "reference": "0.10 – 0.75  (ideal: 0.20 – 0.65)",
        "status": "ok" if b_ok and b_ideal else ("warn" if b_ok else "bad"),
    })

    # D range
    d_ok = 50 <= D_mm <= 1000
    checks.append({
        "name": "Diâmetro interno D",
        "value": f"{D_mm:.2f} mm",
        "reference": "50 – 1000 mm",
        "status": "ok" if d_ok else "bad",
    })

    # Re_D minimum
    if tap == "corner":
        re_min = 5000 if beta <= 0.56 else round(16000 * beta**2)
    elif tap == "flange":
        re_min = 5000 if beta <= 0.60 else 10000
    else:  # DandD2
        re_min = 10000 if beta <= 0.56 else round(16000 * beta**2)

    re_ok    = ReD >= re_min
    re_ideal = ReD >= 20000
    checks.append({
        "name": "Reynolds Re_D",
        "value": f"{ReD:.0f}",
        "reference": f"≥ {re_min}  (ideal ≥ 20 000)",
        "status": "ok" if re_ok and re_ideal else ("warn" if re_ok else "bad"),
    })

    # ΔP/P₁ ≤ 0.25 (Y validity)
    if is_gas:
        checks.append({
            "name": "Razão ΔP/P₁ (validade do fator Y)",
            "value": f"{tau*100:.2f}%",
            "reference": "≤ 25%  (ISO 5167-2 Eq. 7)",
            "status": "ok" if tau <= 0.25 else "warn",
        })

    # Cd sanity
    checks.append({
        "name": "Coef. descarga C_d  (RHG)",
        "value": f"{Cd:.5f}",
        "reference": "Típico: 0.595 – 0.625",
        "status": "info",
    })

    return checks


# ── Quick CLI demo ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    gas = GasFluid(gamma=0.65, Z=0.88, kappa=1.27, mu_cP=0.012)

    # Example: PPT-50 plate, 50 000 Sm³/d
    Q_sm3d = 50_000
    qm = Q_sm3d * gas.density_std() / 86_400

    result = solve_Q_to_dP(
        qm_kgs=qm, D_mm=102.26, d_mm=30.73,
        fluid=gas, P1_Pa=3_000_000, T1_K=313.15, tap="flange"
    )

    print("=" * 50)
    print("ISO 5167-2 — Resultado")
    print("=" * 50)
    for k, v in result.items():
        print(f"  {k:<12} = {v}")
