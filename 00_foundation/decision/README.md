# L2 Decision — account prioritization from a recovered category

L1 answers *"what did we miss?"* (a hidden high-value / low-conversion category,
recovered under a firewall with a calibrated false-positive rate). **L2 answers
*"what do we do about it?"*** — it turns that recovery into a **decision**: rank the
**entire account universe** so a sales team knows which accounts to work next.

This is the "drive the business" leg. Recovery that no one can act on is a finding;
a ranked shortlist a rep can work on Monday is a decision.

## The ranker — lexicographic by construction

L2 orders every account by three keys, in strict priority order (spec §4):

1. **In the recovered category** (the decision): pursue the category L1 found.
   This block boundary dominates everything below it.
2. **Segment tier** (observable value proxy): Enterprise > MidMarket > SMB.
3. **Under-penetration**: fewer Closed-Won first — the "high value, still not
   worked" accounts surface to the top.

The weights are chosen only to preserve key priority (`W1 ≫ W2·max_tier ≫ W3·…`),
so there is **no tuning sensitivity** — the ordering is lexicographic by
construction and deterministic (ties break by `AccountId`). L2 reads observations
and the L1 card only; it never scores true monetary value (it has no firewall-safe
way to — that is honestly out of scope, spec §4.3).

## Firewall (inherited, unchanged)

L2 reads exactly `accounts.csv`, `opportunities.csv`, and the L1 card. It **never**
reads the ground-truth manifest. The ranking records `manifest_read=false` and an
`observation_hash` — byte-identical in form to L1's — so L3 re-verifies the firewall
from the answer side and **rejects** any ranking that read the answer.

## How it's graded — precision@K (the test that matters)

L3 (the sole answer-reader) scores the ranking by **precision@K** against the
planted high-value population: *"of the top-K accounts L2 told you to pursue, what
fraction were genuinely in the high-value population?"* The metric is a real test
**only because L2 ranks all accounts, not a pre-filtered candidate set** (spec §5.4):

- ignore the recovered category → top-K is a random draw → precision@K ≈ base rate;
- use it correctly → the recovered block fills the top → precision@K ≈ 1.0.

On the reference world (50 seeds): **base rate ≈ 0.12**, and **precision@50 = 1.0** —
the planted population is pulled to the top out of the full 1,200-account universe.
precision@200 falls (only ~157 positives exist) as a built-in sanity check.

## Layout

```
decision/
  io.py      observed input contract + observation hash + card read   (spec §3)
  rank.py    the lexicographic ranker                                 (spec §4)
  card.py    ranking artifact assembly + firewall attestation         (spec §3 output)
  run.py     (observation + card) -> ranking
  data/      generated rankings (git-ignored; reproducible)
```

## Run

```bash
# from 00_foundation/ (regenerate the observation + L1 card first)
python -m world_model.run
python -m recovery.run
python -m decision.run                              # -> decision/data/decision_ranking.json
python -m pytest decision/tests/

# end-to-end multi-seed precision@K:
python -m harness.run --n 50                        # now runs L0 -> L1 -> L2 per seed
python -m grading.decision_run --run-dir harness/data/run
```

## Honest limitations (surfaced, not hidden)

- **Segment order is an observable assumption.** Enterprise > MidMarket > SMB by
  value matches the design intent, but `seg_value_mult` is a non-emitted constant —
  L2 cannot confirm it read-only, so it treats the label order as a stated
  assumption (spec §4.1).
- **Within-category ordering is not certified.** precision@K (Option A) treats all
  positives as equal, so the segment-tier + under-penetration ordering inside the
  block is invisible to it. Measuring it needs true per-account value — Option B,
  deferred to an additive L0 extension (spec §5.5, §7). v1 states this rather than
  implying the internal ordering is validated.
- **Attribution is the composed L1→L2 decision.** precision@K grades L2's use of the
  card's *recovered* category against the manifest's *true* category; on the
  reference world L1 runs at precision/recall 1.0, so this isolates L2 in practice,
  but the honest scope is the composed decision (spec §5.4).

---

## 日本語サマリ

L1 が「何を見逃したか」（隠れた高価値・低転換カテゴリの回収）を答えるのに対し、
**L2 は「ではどう動くか」を答えます** ― 回収結果を**意思決定**に変換し、
**全口座（1,200件）を優先順位付け**して「次にどの口座を攻めるか」を提示します。
回収は「発見」、ランク付きの実行リストは「意思決定」です。

ランカーは3つのキーの**辞書式（lexicographic）**順序：(1) 回収カテゴリ所属＝意思決定
そのもの（最優先）、(2) セグメント階層（Enterprise > MidMarket > SMB、観測可能な
価値代理）、(3) 浸透不足（Closed-Won が少ない順＝「高価値だが未着手」が上位に浮上）。
重みはキー優先順位を保つためだけのもので**チューニング感度ゼロ**、同点は AccountId で
決定論的に解消。L2 は観測と L1 card のみを読み、地上真実は読みません
（`manifest_read=false` + `observation_hash` を刻み、L3 が答え側から検証・違反は不採点）。

採点は **precision@K**：「L2 が上位 K 件として勧めた口座のうち、本当に高価値母集団に
属していた割合は？」。**全口座をランク付けするからこそ**意味を持つ検定です（カテゴリを
無視すれば base rate ≈ 0.12 に崩れ、正しく使えば ≈ 1.0）。参照世界（50シード）で
**base rate ≈ 0.12、precision@50 = 1.0**、@200 は正例（約157件）を超えるため正しく劣化
（メトリクス自体の健全性チェック）。

**正直な限界**（隠さず明示）：セグメント順は観測仮定／カテゴリ内順序は未認証
（Option B、L0拡張待ち）／帰属は L1→L2 の合成意思決定。
