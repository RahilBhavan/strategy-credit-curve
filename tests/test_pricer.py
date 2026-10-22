"""Convertible pricer: textbook validation, analytic limits, convergence and put/call boundaries."""
import math
import unittest

from credit_curve import bs
from credit_curve.convertible import Convertible, bond_floor, implied_vol, price, price_avg, straight_bond_pv


class HullTextbookExample(unittest.TestCase):
    """Hull, Options, Futures, and Other Derivatives, 8th ed., "Convertible bonds" (pp. 608-611):
    9-month zero-coupon bond, face 100, convertible into 2 shares, callable at 113 at any time,
    S0 = 50, sigma = 30%, r = 5%, default intensity 1%/yr, recovery 40%, 3-step tree.
    Published tree parameters u = 1.1519, pu = 0.5167, pd = 0.4808, default prob 0.0025 per step,
    and convertible value 106.93."""

    def setUp(self):
        self.cb = Convertible(face=100, maturity=0.75, ratio=2, call_start=0.0, call_price=113)
        self.r = price(self.cb, 50, 0.30, 0.05, model="hull", hazard=0.01, recovery=0.40, steps=3)

    def test_tree_parameters(self):
        x = self.r.extra
        self.assertAlmostEqual(x["u"], 1.1519, places=4)
        self.assertAlmostEqual(x["pu"], 0.5167, places=4)
        self.assertAlmostEqual(x["pd"], 0.4808, places=4)
        self.assertAlmostEqual(x["pdef"], 0.0025, places=4)

    def test_published_value(self):
        self.assertAlmostEqual(self.r.value, 106.93, places=2)

    def test_call_binds_in_example(self):
        no_call = Convertible(face=100, maturity=0.75, ratio=2)
        v = price(no_call, 50, 0.30, 0.05, model="hull", hazard=0.01, recovery=0.40, steps=3).value
        self.assertGreater(v, self.r.value)


class AnalyticLimits(unittest.TestCase):
    def test_zero_coupon_no_credit_equals_bond_plus_black_scholes_call(self):
        # No dividends, no spread, no call: early conversion is never optimal, so the American
        # convertible equals PV(face) + ratio x European call struck at the conversion price.
        cb = Convertible(face=100, maturity=5, ratio=1)
        exact = 100 * math.exp(-0.05 * 5) + bs.call(100, 100, 5, 0.05, 0.30)
        self.assertAlmostEqual(price(cb, 100, 0.30, 0.05, steps=2000).value, exact, delta=0.01)

    def test_tf_with_spread_matches_risky_bond_plus_call_for_zero_coupon(self):
        # Deep out of the money the cash-only part dominates: value -> face x exp(-(r+s)T)
        cb = Convertible(face=1000, maturity=3, ratio=0.1)        # conversion price 10,000
        v = price(cb, 100, 0.5, 0.04, spread=0.06, steps=600).value
        self.assertAlmostEqual(v, 1000 * math.exp(-0.10 * 3), delta=0.05)

    def test_deep_in_the_money_value_is_parity(self):
        cb = Convertible(face=1000, maturity=3, ratio=10)          # conversion price 100
        r = price(cb, 1000, 0.5, 0.04, spread=0.06, steps=600)
        self.assertAlmostEqual(r.value, 10 * 1000, delta=1.0)
        self.assertAlmostEqual(r.delta, 10, delta=0.01)
        self.assertLess(r.cash_part / r.value, 0.002)   # only far-down nodes keep any cash claim

    def test_bond_floor_matches_closed_form(self):
        cb = Convertible(face=1000, maturity=4, ratio=5, coupon_rate=0.02, coupon_times=tuple(0.5 * k for k in range(1, 9)))
        self.assertAlmostEqual(bond_floor(cb, 0.04, 0.05, steps=800), straight_bond_pv(cb, 0.04, 0.05), delta=0.02)


class IndependentEuropeanTF(unittest.TestCase):
    def test_cash_digital_plus_equity_asset_call_with_credit(self):
        # Restrict exercise to maturity. Integrate the lognormal terminal payoff:
        # cash in S_T<K states, equity in S_T>=K states, discounted separately.
        S, K, T, vol, r, spread = 80.0, 100.0, 3.0, 0.4, 0.04, 0.07
        N = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
        d1 = (math.log(S / K) + (r + 0.5 * vol**2) * T) / (vol * math.sqrt(T))
        d2 = d1 - vol * math.sqrt(T)
        cb = Convertible(face=100, maturity=T, ratio=1, free_convert=T, coco_trigger=1e10)
        exact_cash = 100 * math.exp(-(r + spread) * T) * N(-d2)
        exact_equity = S * N(d1)
        # Digital cash component converges slowly; bracket odd/even trees.
        v = price_avg(cb, S, vol, r, spread, steps=(4000, 4001))
        self.assertAlmostEqual(v.value, exact_cash + exact_equity, delta=0.12)
        self.assertAlmostEqual(v.cash_part, exact_cash, delta=0.5)

    def test_invalid_inputs(self):
        cb = Convertible(face=100, maturity=3, ratio=1)
        for kw in ({"S0": -1}, {"sigma": 0}, {"sigma": float("nan")},
                   {"steps": 0}, {"model": "typo"}, {"recovery": 2},
                   {"model": "hull", "hazard": 0.5}):
            args = {"S0": 80, "sigma": 0.3, "r": 0.04, **kw}
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                price(cb, **args)


class Convergence(unittest.TestCase):
    # Tsiveriotis-Fernandes (1998) Exhibit 5 terms, as restated in arXiv:1111.2683 Table 1: 5-year,
    # 4% semi-annual coupon, 1 share per 100, callable at 110 from year 2, r = 5%, spread 2%, vol 30%.
    TF = dict(face=100, maturity=5, ratio=1, coupon_rate=0.04,
              coupon_times=tuple(0.5 * k for k in range(1, 11)), call_start=2, call_price=110)

    def test_tf_price_settles_inside_a_narrow_band(self):
        cb = Convertible(**self.TF)
        vals = [price(cb, 100, 0.30, 0.05, spread=0.02, steps=n).value for n in (1600, 1601, 3200, 3201, 6400)]
        # the call barrier makes CRR prices oscillate (the artifact arXiv:1111.2683 documents);
        # past 1,600 steps the band is under 0.3% of value
        self.assertLess(max(vals) - min(vals), 0.003 * vals[-1])

    def test_averaged_price_is_stable(self):
        cb = Convertible(**self.TF)
        a = price_avg(cb, 100, 0.30, 0.05, spread=0.02, steps=(800, 801, 1200, 1201))
        b = price_avg(cb, 100, 0.30, 0.05, spread=0.02, steps=(3200, 3201, 4800, 4801))
        self.assertLess(abs(a.value - b.value), 0.002 * b.value)

    def test_bs_limit_error_shrinks(self):
        cb = Convertible(face=100, maturity=5, ratio=1)
        exact = 100 * math.exp(-0.25) + bs.call(100, 100, 5, 0.05, 0.30)
        errs = [abs(price(cb, 100, 0.30, 0.05, steps=n).value - exact) for n in (100, 400, 1600)]
        self.assertTrue(errs[0] > errs[1] > errs[2])


class PutCallBoundaries(unittest.TestCase):
    base = dict(face=1000, maturity=5, ratio=2, coupon_rate=0.0)

    def test_holder_put_sets_a_floor(self):
        no_put = Convertible(**self.base)
        put = Convertible(**self.base, puts=((2.0, 1000.0),))
        for S in (50, 200, 400):
            a = price(no_put, S, 0.6, 0.04, spread=0.08).value
            b = price(put, S, 0.6, 0.04, spread=0.08).value
            self.assertGreaterEqual(b, a - 1e-9)
        # far out of the money the put makes it a 2-year risky zero
        b = price(put, 1, 0.6, 0.04, spread=0.08, steps=1000).value
        self.assertAlmostEqual(b, 1000 * math.exp(-0.12 * 2), delta=0.5)

    def test_off_grid_coupon_date_put_retains_coupon(self):
        cb = Convertible(face=1000, maturity=1, ratio=0.001, coupon_rate=0.02,
                         coupon_times=(0.49, 1), puts=((0.49, 1000),))
        # Both events snap to t=.5. Exercise must preserve the contractual $10 coupon.
        v = price(cb, 1, 0.2, 0.04, spread=0.05, steps=2, allow_convert=False)
        self.assertAlmostEqual(v.value, 1010 * math.exp(-0.09 * 0.5), places=8)

    def test_issuer_call_caps_value(self):
        no_call = Convertible(**self.base)
        call = Convertible(**self.base, call_start=0.0, call_price=1000.0)
        for S in (100, 400, 600):
            self.assertLessEqual(price(call, S, 0.6, 0.04, spread=0.08).value,
                                 price(no_call, S, 0.6, 0.04, spread=0.08).value + 1e-9)
        # a hard call at par forces conversion once parity exceeds par: value = parity
        self.assertAlmostEqual(price(call, 600, 0.6, 0.04, spread=0.08).value, 1200, delta=1e-6)

    def test_soft_call_trigger_only_bites_above_trigger(self):
        soft = Convertible(**self.base, call_start=0.0, call_price=1000.0, call_trigger=1.3)
        hard = Convertible(**self.base, call_start=0.0, call_price=1000.0)
        no_call = Convertible(**self.base)
        # conversion price 500; trigger 650
        v_soft = price(soft, 450, 0.6, 0.04, spread=0.08).value
        self.assertLess(price(hard, 450, 0.6, 0.04, spread=0.08).value, v_soft)
        self.assertLessEqual(v_soft, price(no_call, 450, 0.6, 0.04, spread=0.08).value + 1e-9)
        self.assertAlmostEqual(price(soft, 700, 0.6, 0.04, spread=0.08).value, 1400, delta=1e-6)

    def test_value_is_monotone_in_stock_price(self):
        cb = Convertible(**self.base, puts=((2.0, 1000.0),), call_start=1.0, call_price=1000.0, call_trigger=1.3)
        vals = [price(cb, S, 0.6, 0.04, spread=0.08).value for S in range(50, 1000, 50)]
        self.assertTrue(all(b >= a - 1e-6 for a, b in zip(vals, vals[1:])))


class ImpliedVol(unittest.TestCase):
    def test_round_trip(self):
        cb = Convertible(face=1000, maturity=4, ratio=4, puts=((2.0, 1000.0),))
        target = price(cb, 200, 0.55, 0.04, spread=0.05, steps=400).value
        self.assertAlmostEqual(implied_vol(cb, target, 200, 0.04, 0.05), 0.55, places=3)

    def test_price_below_floor_has_no_implied_vol(self):
        cb = Convertible(face=1000, maturity=4, ratio=4)
        floor = bond_floor(cb, 0.04, 0.05)
        self.assertIsNone(implied_vol(cb, floor - 50, 200, 0.04, 0.05))


if __name__ == "__main__":
    unittest.main()
