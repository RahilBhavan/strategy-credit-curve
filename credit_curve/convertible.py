"""Convertible-bond pricer on a CRR binomial tree.

Two credit treatments share one backward induction:

- ``"tf"``: Tsiveriotis-Fernandes (1998). Value V is split into a cash-only part B, discounted at
  r + credit spread, and an equity part V - B, discounted at r. Coupons, put and call cash go to B;
  conversion moves the whole value into equity (B = 0).
- ``"hull"``: Hull's default-intensity tree (Options, Futures, and Other Derivatives, 8th ed.,
  section "Convertible bonds"). The stock jumps to zero on default with intensity lambda and the bond
  recovers ``recovery x face``. Used to validate the tree mechanics against a published answer.

Terms are expressed in years from the valuation date (see ``notes.py`` for the date layer).
All money amounts are per ``face`` (use 1000 for a $1,000 note).

Approximations (documented in docs/methodology.md):
- Provisional (soft) call: the issuer may call only at nodes where S >= call_trigger x conversion price,
  a node-level stand-in for "130% for 20 of 30 trading days".
- Contingent conversion before ``free_convert`` is allowed only at nodes where S >= coco_trigger x
  conversion price, a stand-in for the 130% last-sale-price condition. The 98% trading-price
  condition and make-whole share increases are not modelled.
"""
from dataclasses import dataclass, field
import math
import numpy as np


@dataclass(frozen=True)
class Convertible:
    face: float
    maturity: float                      # years
    ratio: float                         # shares per face
    coupon_rate: float = 0.0             # annual, on face
    coupon_times: tuple = ()             # years of remaining coupon payments (incl. maturity)
    redemption: float = None             # paid at maturity, default face
    call_start: float = None             # years; None = not callable
    call_price: float = None             # default face (+accrued)
    call_trigger: float = 0.0            # S >= trigger x conversion price; 0 = hard call
    puts: tuple = ()                     # ((time, price), ...) holder puts (+accrued)
    free_convert: float = 0.0            # years from which conversion is unconditional
    coco_trigger: float = 0.0            # S >= trigger x conversion price before free_convert

    @property
    def conversion_price(self):
        return self.face / self.ratio

    def accrued(self, t):
        if not self.coupon_rate or not self.coupon_times:
            return 0.0
        per = self.face * self.coupon_rate / 2.0          # semi-annual coupons
        nxt = [c for c in self.coupon_times if c >= t - 1e-12]
        if not nxt:
            return 0.0
        start = nxt[0] - 0.5
        return per * min(max((t - start) / 0.5, 0.0), 1.0)


@dataclass
class Result:
    value: float
    cash_part: float
    equity_part: float
    delta: float          # dV/dS per face, from the first step
    steps: int
    extra: dict = field(default_factory=dict)


def price(cb, S0, sigma, r, spread=0.0, q=0.0, steps=600, model="tf", hazard=0.0, recovery=0.0,
          allow_convert=True):
    """Price ``cb`` at stock price S0. ``q`` is a continuous stock borrow/dividend yield."""
    if model not in ("tf", "hull"):
        raise ValueError("model must be tf or hull")
    if not isinstance(steps, int) or isinstance(steps, bool) or steps < 2:
        raise ValueError("steps must be an integer >= 2")
    if not all(math.isfinite(x) for x in (S0, sigma, r, spread, q, cb.face, cb.maturity, cb.ratio, hazard, recovery)):
        raise ValueError("pricing inputs must be finite")
    if min(S0, sigma, cb.face, cb.maturity, cb.ratio) <= 0:
        raise ValueError("spot, volatility, face, maturity and ratio must be positive")
    if hazard < 0 or not 0 <= recovery <= 1 or (model == "hull" and sigma * sigma <= hazard):
        raise ValueError("invalid hazard/recovery or hazard >= variance")
    T = cb.maturity
    n = steps
    dt = T / n
    red = cb.face if cb.redemption is None else cb.redemption
    if model == "hull":
        u = math.exp(math.sqrt((sigma * sigma - hazard) * dt))
        d = 1.0 / u
        a = math.exp((r - q) * dt)
        pu = (a - d * math.exp(-hazard * dt)) / (u - d)
        pd = (u * math.exp(-hazard * dt) - a) / (u - d)
        pdef = 1.0 - math.exp(-hazard * dt)
    else:
        u = math.exp(sigma * math.sqrt(dt))
        d = 1.0 / u
        pu = (math.exp((r - q) * dt) - d) / (u - d)
        pd = 1.0 - pu
        pdef = 0.0
    if not (0.0 < pu < 1.0 and 0.0 <= pd <= 1.0):
        raise ValueError("risk-neutral probability outside (0, 1); use more steps")
    disc_r = math.exp(-r * dt)
    disc_rs = math.exp(-(r + spread) * dt)
    cp = cb.conversion_price

    # coupon amounts mapped to the step on or just after each coupon time
    cpn = np.zeros(n + 1)
    per = cb.face * cb.coupon_rate / 2.0
    for t in cb.coupon_times:
        if 0 < t <= T + 1e-9:
            cpn[min(n, int(math.ceil(t / dt - 1e-9)))] += per
    puts = {}
    for t, px in cb.puts:
        if 0 < t < T + 1e-9:
            # Freeze the cash entitlement at the contractual date before grid snapping.
            # A node just after a coupon date must not reset that put's unpaid coupon.
            puts[min(n, int(round(t / dt)))] = px + cb.accrued(t)

    j = np.arange(n + 1)
    S = S0 * u ** j * d ** (n - j)
    conv = cb.ratio * S if allow_convert else np.zeros_like(S)
    final = red + cpn[n]
    V = np.maximum(final, conv)
    B = np.where(conv > final, 0.0, final)
    v1 = None
    for i in range(n - 1, -1, -1):
        t = i * dt
        S = S0 * u ** j[: i + 1] * d ** (i - j[: i + 1])
        if model == "hull":
            hold = disc_r * (pu * V[1:] + pd * V[:-1] + pdef * recovery * cb.face)
            Bh = hold.copy()
        else:
            E = V - B
            Bh = disc_rs * (pu * B[1:] + pd * B[:-1])
            hold = disc_r * (pu * E[1:] + pd * E[:-1]) + Bh
        hold = hold + cpn[i]
        Bh = Bh + cpn[i]
        V, B = hold, Bh
        conv = cb.ratio * S if allow_convert else np.zeros_like(S)
        acc = cb.accrued(t)
        if cb.call_start is not None and t >= cb.call_start - 1e-12:
            cpx = (cb.face if cb.call_price is None else cb.call_price) + acc
            callable_ = (S >= cb.call_trigger * cp) & (V > cpx)
            forced = callable_ & (conv >= cpx)
            cash = callable_ & ~forced
            V = np.where(forced, conv, np.where(cash, cpx, V))
            B = np.where(forced, 0.0, np.where(cash, cpx, B))
        if i in puts:
            ppx = puts[i]
            put = V < ppx
            V = np.where(put, ppx, V)
            B = np.where(put, ppx, B)
        if allow_convert:
            ok = np.ones_like(S, dtype=bool) if t >= cb.free_convert - 1e-12 else S >= cb.coco_trigger * cp
            cv = ok & (conv > V)
            V = np.where(cv, conv, V)
            B = np.where(cv, 0.0, B)
        if i == 1:
            v1 = (V.copy(), S.copy())
    delta = float((v1[0][1] - v1[0][0]) / (v1[1][1] - v1[1][0])) if v1 is not None else float("nan")
    return Result(float(V[0]), float(B[0]), float(V[0] - B[0]), delta, n,
                  {"u": u, "d": d, "pu": pu, "pd": pd, "pdef": pdef})


def price_avg(cb, S0, sigma, r, spread=0.0, q=0.0, steps=(1000, 1001, 1500, 1501), **kw):
    """Average over several step counts to damp the odd/even and barrier oscillation of CRR prices."""
    rs = [price(cb, S0, sigma, r, spread, q, n, **kw) for n in steps]
    k = len(rs)
    return Result(sum(x.value for x in rs) / k, sum(x.cash_part for x in rs) / k,
                  sum(x.equity_part for x in rs) / k, sum(x.delta for x in rs) / k, max(steps),
                  {"band": max(x.value for x in rs) - min(x.value for x in rs)})


def bond_floor(cb, r, spread, steps=600):
    """Straight-debt value: no conversion, puts and hard-dated cash flows, discounted at r + spread."""
    return price(cb, 1.0, 0.2, r, spread, steps=steps, allow_convert=False).value


def straight_bond_pv(cb, r, spread, horizon=None):
    """Closed-form PV of coupons + principal to ``horizon`` (default maturity) at r + spread."""
    H = cb.maturity if horizon is None else horizon
    red = cb.face if cb.redemption is None else cb.redemption
    k = r + spread
    pv = sum(cb.face * cb.coupon_rate / 2.0 * math.exp(-k * t) for t in cb.coupon_times if 0 < t <= H + 1e-9)
    final = red if horizon is None else dict(cb.puts).get(H, red)
    return pv + final * math.exp(-k * H)


def implied_vol(cb, target, S0, r, spread, q=0.0, steps=400, lo=0.05, hi=3.0):
    from .bs import bisect
    return bisect(lambda s: price(cb, S0, s, r, spread, q, steps).value - target, lo, hi, tol=1e-6, it=80)


def implied_spread(cb, target, S0, sigma, r, q=0.0, steps=400, lo=-0.02, hi=0.40):
    from .bs import bisect
    return bisect(lambda c: price(cb, S0, sigma, r, c, q, steps).value - target, lo, hi, tol=1e-7, it=80)
