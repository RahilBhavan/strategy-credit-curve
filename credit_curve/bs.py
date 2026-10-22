"""Black-Scholes call and a bracketed root finder. stdlib only."""
import math


def ncdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def call(S, K, T, r, sigma, q=0.0):
    """European call on a stock with continuous yield q (use q for borrow cost)."""
    if T <= 0 or sigma <= 0:
        return max(S * math.exp(-q * T) - K * math.exp(-r * T), 0.0) if T > 0 else max(S - K, 0.0)
    v = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / v
    return S * math.exp(-q * T) * ncdf(d1) - K * math.exp(-r * T) * ncdf(d1 - v)


def call_delta(S, K, T, r, sigma, q=0.0):
    v = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / v
    return math.exp(-q * T) * ncdf(d1)


def bisect(f, lo, hi, tol=1e-8, it=200):
    """Root of increasing-or-decreasing f on [lo, hi]; None if not bracketed."""
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if flo * fhi > 0:
        return None
    for _ in range(it):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if abs(fm) < tol or hi - lo < tol:
            return mid
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


def implied_vol(price, S, K, T, r, q=0.0, lo=1e-4, hi=5.0):
    return bisect(lambda s: call(S, K, T, r, s, q) - price, lo, hi)
