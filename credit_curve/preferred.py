"""Yield, spread and option-adjustment arithmetic for perpetual preferreds."""
import math
from . import bs


def current_yield(annual_dividend, price):
    return annual_dividend / price


def effective_annual(annual_dividend, price, payments_per_year):
    """Perpetuity yield with the payment frequency compounded to an annual rate."""
    return (1 + annual_dividend / payments_per_year / price) ** payments_per_year - 1


def bey_to_effective(y):
    """Semi-annual bond-equivalent yield (Treasury par) to an effective annual rate."""
    return (1 + y / 2) ** 2 - 1


def cc_to_effective(y):
    return math.exp(y) - 1


def yield_to_call(price, annual_dividend, payments_per_year, years_to_call, call_price):
    """IRR (effective annual) of buying at ``price``, receiving dividends, and being called."""
    n = max(1, round(years_to_call * payments_per_year))
    c = annual_dividend / payments_per_year

    flows = [(k / payments_per_year, c) for k in range(1, n + 1) if c > 0]
    flows.append((n / payments_per_year, call_price))

    def log_pv(rho):
        # Work in log-gross annual rates to bracket yields below -50% or above 200%.
        values = [math.log(cash) - rho * t for t, cash in flows]
        largest = max(values)
        return largest + math.log(sum(math.exp(v - largest) for v in values)) - math.log(price)

    lo, hi = -1.0, 1.0
    for _ in range(64):
        if log_pv(lo) >= 0 and log_pv(hi) <= 0:
            rho = bs.bisect(log_pv, lo, hi, tol=1e-13)
            try:
                return math.expm1(rho)
            except OverflowError as error:
                raise ValueError('yield-to-call exceeds representable annual yield') from error
        if log_pv(lo) < 0:
            lo *= 2
        if log_pv(hi) > 0:
            hi *= 2
    raise ValueError('yield-to-call could not be bracketed')


def conversion_option(spot, shares_per_pref, conversion_price, years, rate, vol, borrow=0.0):
    """Value per preferred of a European call on ``shares_per_pref`` shares struck at the conversion price.

    A finite-horizon stand-in for a perpetual holder conversion right (an assumption; see docs)."""
    return shares_per_pref * bs.call(spot, conversion_price, years, rate, vol, borrow)


def price_at_yield(annual_dividend, payments_per_year, y_eff):
    """Perpetuity price that gives effective annual yield ``y_eff``."""
    per = (1 + y_eff) ** (1 / payments_per_year) - 1
    return annual_dividend / payments_per_year / per
