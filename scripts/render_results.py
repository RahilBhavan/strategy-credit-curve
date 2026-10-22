"""Render the reviewed result JSON as an accessible SVG table and the README summary, using only stdlib."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from credit_curve import summary  # noqa: E402  (stdlib-only module; no numpy needed)

START, END = '<!-- preferred-summary:start -->', '<!-- preferred-summary:end -->'


def render():
    source = ROOT / 'results/convertibles.json'
    data = json.loads(source.read_text())
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 940" role="img" aria-labelledby="title desc">',
           '<title id="title">Six notes, nine model values each</title>',
           '<desc id="desc">Model scenario minima, central assumptions and maxima per $1,000 face. These are not market quotes or confidence intervals.</desc>',
           '<rect width="760" height="940" fill="#F5F5EF"/>',
           '<g font-family="IBM Plex Sans, Arial, sans-serif" fill="#111214">']

    def text(x, y, content, size=28, anchor='start', weight='400', fill='#111214'):
        svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}">{content}</text>')

    text(32, 46, 'RAHIL BHAVAN / BUILD NOTES', 28, fill='#52545A')
    text(32, 104, 'Six notes, nine model values each', 32, weight='600')
    text(32, 150, 'Synthetic inputs • USD per $1,000 face', 28)
    text(32, 192, 'Contract/rate snapshot: 21 Oct 2026', 28, fill='#52545A')
    svg.append('<rect x="431" y="216" width="152" height="410" fill="#FFE500"/>')
    for x, label in ((32, 'Note'), (403, 'Low'), (557, 'Central*'), (718, 'High')):
        text(x, 260, label, 28, 'start' if x == 32 else 'end', '600')
    svg.append('<path d="M32 280H728" stroke="#C6C7BF"/>')
    for i, note in enumerate(data['notes']):
        scenarios = note['scenarios']
        values = [s['value_per_1000_usd'] for s in scenarios]
        central = next(s['value_per_1000_usd'] for s in scenarios
                       if s['vol_assumption'] == 0.6 and s['spread_assumption'] == 0.05)
        y = 327 + 55 * i
        text(32, y, note['terms']['name'], 30)
        for x, value in zip((403, 557, 718), (min(values), central, max(values))):
            text(x, y, f'{value:,.2f}', 30, 'end')
    text(32, 675, '*Central: 60% volatility, 5% credit spread.', 28)
    text(32, 717, 'Grid: vol 40/60/80%; spread 2/5/10%.', 28)
    text(32, 759, 'Low/high are grid extrema, not probabilities.', 28)
    text(32, 801, '600 steps; simplified exercise triggers.', 28, fill='#52545A')
    text(32, 843, 'Source: results/convertibles.json', 28, fill='#52545A')
    text(32, 885, 'Synthetic prices/vols; not market quotes.', 28, fill='#52545A')
    text(32, 927, 'Method: docs/methodology.md', 28, fill='#52545A')
    svg.extend(['</g>', '</svg>'])
    target = ROOT / 'figures/scenarios.svg'
    target.parent.mkdir(exist_ok=True)
    target.write_text('\n'.join(svg) + '\n')
    print(f'{target.relative_to(ROOT)}; input SHA-256 {hashlib.sha256(source.read_bytes()).hexdigest()}')
    readme = ROOT / 'README.md'
    body = readme.read_text()
    if START not in body or END not in body:
        raise SystemExit('README.md lacks the preferred-summary markers')
    table = summary.markdown(json.loads((ROOT / 'results/preferred.json').read_text()))
    head, rest = body.split(START, 1)
    readme.write_text(head + START + '\n' + table + '\n' + END + rest.split(END, 1)[1])
    print('README.md preferred summary regenerated from results/preferred.json')


if __name__ == '__main__':
    render()
