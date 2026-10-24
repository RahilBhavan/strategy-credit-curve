"""Render figures/preferred-yields.svg from results/preferred.json: one bar per preferred, zero baseline."""
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDTH, LEFT = 760, 32
BAR_X, AXIS_MAX = 150, 0.20
SCALE = (600 - BAR_X) / AXIS_MAX
INK, CONTEXT, ACCENT, SURFACE = '#111214', '#52545A', '#FFE500', '#F5F5EF'


def x_of(value):
    return BAR_X + value * SCALE


def day_label(iso):
    return dt.date.fromisoformat(iso).strftime('%-d %b %Y')


def detail(row):
    extra = {'STRC': f'{100 * row["rate"]:g}% rate, reset monthly', 'STRK': 'also converts to MSTR'}.get(row['ticker'])
    return f'${row["price"]:.2f} close · ' + (extra or ('cumulative' if row['cumulative'] else 'noncumulative'))


def render():
    source = ROOT / 'results/preferred.json'
    data = json.loads(source.read_text())
    if data['market_inputs']['kind'] != 'exchange_close':
        raise SystemExit('preferred-yields.svg shows exchange closes only; results/preferred.json is '
                         f'{data["market_inputs"]["kind"]}')
    rows = data['rows']
    priced = [r for r in rows if r['price'] is not None]
    top = max(priced, key=lambda r: r['effective_yield'])
    low = min(priced, key=lambda r: r['effective_yield'])
    ust = data['benchmarks']['ust30']['effective']
    day = day_label(data['as_of'])
    rank = 'Junior ' if top is rows[-1] else ''
    title = f'{rank}{top["ticker"]} yields the most: {100 * top["effective_yield"]:.1f}%'
    desc = (f'Effective annual yield of Strategy preferreds at the {day} Nasdaq close, in seniority order: '
            + '; '.join(f'{r["ticker"]} {100 * r["effective_yield"]:.2f}%' if r['price'] is not None
                        else f'{r["ticker"]} excluded, no trade' for r in rows)
            + f'. 30-year Treasury par yield {100 * ust:.2f}% effective.')
    height = 206 + 104 * len(rows) + 76 + 5 * 42 - 10
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" role="img" '
           'aria-labelledby="title desc">',
           f'<title id="title">{title}</title>', f'<desc id="desc">{desc}</desc>',
           f'<rect width="{WIDTH}" height="{height}" fill="{SURFACE}"/>',
           f'<g font-family="IBM Plex Sans, Arial, sans-serif" fill="{INK}">']

    def text(x, y, content, size=28, anchor='start', weight='400', fill=INK):
        svg.append(f'<text x="{x:.1f}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                   f'font-weight="{weight}" fill="{fill}">{content}</text>')

    text(LEFT, 46, 'RAHIL BHAVAN / BUILD NOTES', 28, fill=CONTEXT)
    text(LEFT, 96, title, 36, weight='600')
    text(LEFT, 140, f'Effective annual yield at the {day} close', 28)
    text(LEFT, 178, 'Senior at top, junior at bottom (filing order)', 28, fill=CONTEXT)
    plot_top, plot_bottom = 206, 206 + 104 * len(rows)
    ref = x_of(ust)
    svg.append(f'<path d="M{x_of(0):.1f} {plot_top}V{plot_bottom}" stroke="{INK}" stroke-width="2"/>')
    for i, row in enumerate(rows):
        y = plot_top + 104 * i
        text(LEFT, y + 42, row['ticker'], 28, weight='600')
        if row['price'] is None:
            text(BAR_X + 14, y + 42, f'No trade on {day}; excluded', 28, fill=CONTEXT)
            text(BAR_X + 14, y + 80, f'LuxSE, EUR; last trade {day_label(row["price_source"]["as_of"])}',
                 28, fill=CONTEXT)
            continue
        svg.append(f'<path d="M{ref:.1f} {y + 8}V{y + 60}" stroke="{CONTEXT}" stroke-width="2" '
                   'stroke-dasharray="6 6"/>')
        end = x_of(row['effective_yield'])
        fill, stroke = (ACCENT, f' stroke="{INK}" stroke-width="2"') if row is top else (CONTEXT, '')
        svg.append(f'<rect x="{x_of(0):.1f}" y="{y + 16}" width="{end - x_of(0):.1f}" height="36" '
                   f'fill="{fill}"{stroke}/>')
        text(end + 10, y + 44, f'{100 * row["effective_yield"]:.2f}%', 28, weight='600' if row is top else '400')
        text(BAR_X + 10, y + 88, detail(row), 28, fill=CONTEXT)
    svg.append(f'<path d="M{ref:.1f} {plot_bottom + 6}V{plot_bottom + 34}" stroke="{CONTEXT}" stroke-width="2" '
               'stroke-dasharray="6 6"/>')
    text(ref + 8, plot_bottom + 30, f'30-year Treasury {100 * ust:.2f}%', 28, fill=CONTEXT)
    text(x_of(0), plot_bottom + 30, '0%', 28, 'middle', fill=CONTEXT)
    notes = [f'Range {100 * low["effective_yield"]:.1f}% ({low["ticker"]}) to {100 * top["effective_yield"]:.1f}% '
             f'({top["ticker"]}); bars start at 0%.',
             'Yield: stated dividend over the close,',
             'compounded at each payment frequency.',
             'Closes: Nasdaq, data/market/2026-10-21.',
             'Source: results/preferred.json']
    for k, line in enumerate(notes):
        text(LEFT, plot_bottom + 76 + 42 * k, line, 28, fill=INK if k == 0 else CONTEXT)
    svg.extend(['</g>', '</svg>'])
    target = ROOT / 'figures/preferred-yields.svg'
    target.write_text('\n'.join(svg) + '\n')
    print(f'{target.relative_to(ROOT)}; input SHA-256 {hashlib.sha256(source.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    render()
