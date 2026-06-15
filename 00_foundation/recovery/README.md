# L1 Recovery — value-concentration wedge (signal 06)

Infers a hidden **value-concentration blind-spot** — a category whose deals are
each worth far more than average, but which is *small* enough that aggregates hide
it — from the **observed** data alone (`accounts.csv` + `opportunities.csv`).

This is **inference, not narration**. A naive reading flags "high observed ARPA,
low count"; but a small category can look high purely from sampling noise. L1
works in log space (the value drivers are multiplicative, so log makes them
additive), fits a two-way `μ + α_segment + β_category` decomposition, and
**empirical-Bayes shrinks** each category effect toward zero with weight
`τ²/(τ² + σ²/n_c)`. Small categories shrink hard, so a category that *survives*
shrinkage is genuinely high-value — separating "noisy and small" from "truly high
and small". Existence and membership thresholds are calibrated against a
**permutation null**, never against fixed currency values.

## Firewall

L1 never reads the ground-truth manifest or the generator internals — it only
reads the two observed CSVs. The card records `manifest_read=false` and a
`observation_hash` so a grader can independently attest L1 touched only the
observation. **Whether the inference is correct is decided downstream, not here.**

## Layout

```
recovery/
  io.py        observed input contract + observation hash      (spec §3)
  wedge.py     two-way decomposition + EB pooling, gate, membership (spec §5)
  guards.py    permutation-null calibration, shape utilities    (spec §7)
  baseline.py  L0 self_check rule, ported for parity            (spec §5.5)
  card.py      recovery card assembly                           (spec §12)
  run.py       observation -> card
  data/        generated cards (git-ignored; reproducible)
```

## Run

```bash
# from 00_foundation/ (regenerate the observation first via the L0 generator)
python -m world_model.run --seed 42
python -m recovery.run --data-dir world_model/data/v1
python -m pytest recovery/tests/        # or 00_foundation/recovery/tests
```

The card lands in `recovery/data/recovery_card.json` (git-ignored). Defaults
(spec §14 R1): `S_min=6, α=0.05, B=1000, p_low=0.5, J_min=0.8`.

## What the card contains

- `wedge_exists` — existence decision, separation statistic, null threshold, p-value.
- `recovered_wedge_category` — the falsifiable claim (category, count, shrunk
  effect, elevation ratio, posterior elevation probability, per-segment breakdown).
- `absence_checks` / `invariants` / `baseline_parity` — L1's own, answer-key-free
  health (no fabrication under the null, no false wedge off the value axis, etc.).

---

## 日本語サマリ

観測データ（`accounts.csv` + `opportunities.csv`）だけから、**価値集中の死角**＝
「各取引の単価が突出して高いが、件数が少ないために集計に埋もれるカテゴリ」を
**推論**します。「観測ARPAが高く件数が少ない」を述べる *narration* ではなく、
小カテゴリの高ARPAが真の性質か低件数ゆえの推定分散かを統計的に弁別する *inference* です。

生成は乗法的なので log で加法化し、`μ + α_segment + β_category` の二元分解＋
**経験ベイズ縮約**（小件数ほど 0 へ強く縮約）で、縮約を生き残った小カテゴリのみを
「真に高単価」と判定します。存在・所属の閾値は**置換帰無分布**で較正し、固定金額や
植えた効果量は一切使いません（firewall）。

L1 は地上真実マニフェストを読みません。card に `manifest_read=false` と
`observation_hash` を刻み、観測しか触れていないことを下流が独立検証できます。
**回収が正しいかの採点は L1 の責務ではありません（L3 が行う）。** 生成 card は
.gitignore（再現可能）、commit する fixture は合成のみ。実ドメイン指紋ゼロ。
