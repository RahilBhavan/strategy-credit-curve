# Five-minute input diagnostics

The default example stays synthetic. Inspect it without network calls:

```bash
python -m credit_curve.diagnostics --out results/local/diagnostics.json
python -m credit_curve.diagnostics --out results/local/diagnostics.json --require-complete
```

The first command writes a deterministic diagnostic report. The second writes the same report and exits **3**, because synthetic assumptions and absent note marks cannot establish complete observed coverage. Invalid files exit **2** before writing output. Use the environment described in the README.

For your own authorized data, supply `--market-input /path/to/market.json` and optionally `--note-marks /path/to/marks.json`. The market schema is documented in [market inputs](market-inputs.md). Note marks use this separate schema (only supported note names may appear):

```json
{
  "schema_version": 1,
  "kind": "user_supplied",
  "valuation_date": "2026-10-21",
  "marks": {
    "2028": {
      "price": 1000,
      "currency": "USD",
      "face_amount": 1000,
      "price_basis": "dirty",
      "price_date": "2026-10-21",
      "quote_type": "indicative",
      "source": {
        "description": "Authored illustration only; replace with your authorized observation",
        "as_of": "2026-10-21",
        "fetched_utc": "2026-10-22T00:30:00Z",
        "url": null
      }
    }
  }
}
```

This illustration is not a market quote. `quote_type` accepts bid, ask, mid, trade or indicative. Prices must be positive, finite USD full (dirty) prices per $1,000 face, valued on the snapshot date. Clean prices and other units are rejected rather than silently converted. An omitted mark remains missing; June filing values and offering prices are never substituted.

Each input retains description, observation/retrieval dates and file SHA-256. Ages are calendar days relative to the frozen valuation date, not the machine's current date. Missing observation/retrieval dates, any earlier observation, or synthetic kind make an input unusable for comparisons. Missing/stale MSTR blocks every note comparison. Missing/stale STRE is reported but does not block independent note comparisons. No verified STRE observation was obtained or added in this slice.

For each usable mark, the report retains all nine unchanged volatility/spread scenarios and computes model minus supplied price in dollars and percent of supplied price. Same-day dates do not establish synchronized intraday observations. Values remain conditional on model assumptions; differences are neither fitted spreads nor evidence of mispricing. The model omits exact accrual/settlement and record-date ownership. Preferred diagnostics inspect inputs only and do not calculate preferred model valuations.

The CLI is offline: source strings and dates are supplied assertions, never independently verified. No vendor bodies, private history or new live feed are included. Tests use authored fixtures, test repeatability with network access forbidden, and preserve existing public scenario values.
