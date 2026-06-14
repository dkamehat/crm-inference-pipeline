# L0 WorldModel — hidden-causal data generator

A synthetic data generator for a **high-frequency transactional platform
archetype**. It does not generate "flat random" CRM rows; it defines a *hidden
causal world* and emits the **lossy projection** of that world as
Salesforce-shaped CSVs — plus a **ground-truth manifest** that records the hidden
truth. Later analysis layers are then judged on whether they *recover* the
planted structure, not on whether they narrate the surface.

All data is synthetic and seeded. Naming is deliberately generic: there is no
real domain, employer, or figure anywhere in this package.

---

## Why a world model, not a random generator

A flat random generator produces tables with no recoverable structure — every
"insight" is a tautology of the sampling code. This generator instead keeps three
layers genuinely distinct:

| Layer | Class | What it decides |
|-------|-------|-----------------|
| **Outcome** | `TrueConversionModel` | the hidden true weights that actually win/lose deals and set value |
| **Priority** | `AssumedScoreModel` | the org's *assumed* prioritization, miscalibrated at first, learning via PDCA |
| **Record** | `RepBehaviorModel` | what reps actually *record*, distorted by comp incentives |

Because these three diverge, the gap between them becomes something analysis can
*infer*: a planted weight gap that closes over time, a value blind-spot the score
never sees, under-credited partner sourcing, concentrated hidden ownership, and a
coverage-vs-execution confound.

## The six hidden structures

1. **Controlling-entity graph** — a few entities own many accounts (power-law,
   capped); the observed CRM hides or mis-parents most links.
2. **Demand sources** — outbound / inbound / partner, with partner genuinely
   stronger but under-credited by last-touch attribution.
3. **True vs. assumed weights** — the prior is miscalibrated and learns toward the
   realized signal each period (PDCA).
4. **Comp-driven record distortion** — sandbag, stale stage (rep doesn't update),
   happy-ears, close-date optimism.
5. **Capacity / two motions** — finite per-territory and global capacity; skewed
   territory potential produces a coverage confound.
6. **Exogenous seasonality** — a smooth annual cycle with a Q4 bump and summer dip.

Exogenous and source effects are added in **logit space** so the partner signal
survives instead of being crushed against the probability ceiling.

## Layout

```
world_model/
  config.py     # Config (structural knobs) + WorldProfile (profile-specific values)
  graph.py      # ControllingEntityGraph         (structure ①)
  models.py     # TrueConversionModel / AssumedScoreModel  (structure ③)
  reps.py       # RepBehaviorModel                (structure ④)
  market.py     # seasonality / sources / territory latent  (②⑤⑥)
  simulate.py   # WorldModel — the period loop
  emit.py       # observed CSVs + _ground_truth.json
  run.py        # CLI entry
  self_check.py # planted-signal recovery report (eyeball + machine-checkable)
  tests/        # pytest: the ten signals + structural invariants
```

The **core engine is generic**. Everything V1-specific (segments, categories, the
planted wedge, territories, sources, loss mix) lives in a `WorldProfile` in
`config.py`. Additional regimes (V2, V3) are added as new profiles in `PROFILES`;
the engine is never forked.

## Run

```bash
# from 00_foundation/
python -m world_model.run --seed 42 --periods 18
# or directly
python 00_foundation/world_model/run.py --seed 42 --out ./data/v1
```

Outputs land in `world_model/data/<profile>/` and are reproducible from the seed.
**Generated CSVs are git-ignored** — regenerate them, don't commit them.

```bash
python -m pytest world_model/tests/      # the ten signals + invariants
```

## Outputs

Observed tables (the lossy projection): `accounts`, `opportunities`,
`assumed_scores`, `users`, `activities`, `usage`, `health`.

`_ground_truth.json` (the answer key) records the true weights, the true
ownership graph, the true source mix, the planted wedge, the weight-gap curve, and
territory potential. It contains no volatile paths.

## Planted signals (and what recovers them)

| Signal | Recovery |
|--------|----------|
| Seasonality | peaks/troughs in monthly won-count |
| Segment-conditional loss | Pareto, not a flat uniform |
| Temporal integrity | cohort months-since ≥ 0 |
| Realistic dwell | days-open capped (no 1,200-day stuck) |
| Activation correlation | usage ↔ health |
| **Wedge** | high-value / low-conversion cell stays under-worked *after* learning |
| **Weight gap** | assumed-vs-true gap shrinks over periods |
| **Ownership concentration** | true buyer count ≪ CRM rows |
| **Partner under-credit** | true partner conversion > observed |
| **Coverage confound** | high-potential territory under-covered, reps execute fine |

---

## 日本語サマリ

これは **高頻度トランザクション型プラットフォームの汎用アーキタイプ**向けの合成
データ生成器です。フラットな乱数を吐くのではなく、**隠れた因果世界**を定義し、その
**歪んだ射影**を Salesforce 型 CSV として出力します。さらに、隠れた真値を記録した
**地上真実マニフェスト**を併せて出力し、後段の分析が「表層のナレーション」ではなく
「隠れた構造の回収」をできているかを答え合わせできるようにします。

中核は **勝敗（真モデル）・優先順位（想定モデル）・記録（rep 行動）の三層のズレ**で、
このズレが weight gap・value blind-spot（wedge）・partner 過小評価・支配集中・
coverage 交絡を「推定可能な隠れ真値」にします。外生・源の効果は **logit 空間**で
加算します（確率乗算は天井に当たり partner シグナルを潰すため）。

コアエンジンは汎用で、V1 固有の値（segment / category / wedge など）は `config.py` の
`WorldProfile` に分離。V2・V3 は profile を追加するだけで、エンジンを fork しません。
データはすべて合成・seed で再現可能で、**生成 CSV は commit しません**（再生成する）。
実ドメイン・実社名・実数値は一切含みません。
