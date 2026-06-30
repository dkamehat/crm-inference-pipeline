# Recovering the revenue you're ignoring — with a measured error rate

[![CI](https://github.com/dkamehat/crm-inference-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/dkamehat/crm-inference-pipeline/actions/workflows/ci.yml)

> A BizOps / analytics portfolio built around one idea: an analyst should be able to
> say *"we found X, here's what to do about it, and here's why you can trust it"* —
> and have every word of that be **checkable**. The flagship is a CRM inference
> pipeline that finds hidden value, decides what to do, and **grades itself against
> ground truth**. Everything reproduces from source; CI re-proves it on every push.

**60-second tour:** read this page → skim the [Decision Brief](00_foundation/DECISION-BRIEF.md)
(what a VP would receive) → if you want the machinery, [`00_foundation/`](00_foundation/);
if you want conventional SQL/BI craft, [`01_b2b_saas/`](01_b2b_saas/).

---

**The business problem.** Sales teams leave money in segments that *look* unpromising: an
account category whose deals convert poorly, so the team deprioritizes it — even though the
accounts in it are quietly worth ~2.8× a typical one. The value is real but masked by low
conversion, so it never gets worked.

**What this does.** From standard CRM tables alone (`accounts`, `opportunities`), this pipeline
surfaces that hidden high-value segment, states **how confident it is** (a measured
false-positive rate), **decides which accounts to work first**, and — running in a controlled
world where the truth is known by construction — **proves each step against ground truth**.

Not a dashboard. Defensible inference *and a graded decision*: the "we found X, here's what to
do, and here's why you can trust it" you can put in front of a VP.

## Why a synthetic world (and why that's the point)

On real CRM data you can never check whether an "insight" was actually right — there is no
answer key. So I built one: a generator plants a known high-value / low-conversion segment, then
hides the answer. The recovery step sees only the observable data and must find the planted
segment on its own; a separate grader — the only component allowed to see the answer — scores it.

That separation is the whole game, and it is what lets every quality number below be *measured*
rather than asserted. The method transfers to real CRM data; the synthetic world is what makes
it provable.

## The pipeline

```
Plant    a generator embeds a known high-value / low-conversion segment in a synthetic B2B world
Hide     the segment is projected into observable tables; the answer is sealed away
Recover  a firewalled step finds the segment from observations only, with a calibrated test
Decide   a ranker turns the recovered segment into a prioritized list of every account to work
Grade    a separate step (the sole answer-reader) scores recovery AND the decision against truth
```

**Firewall:** the components that *claim* a finding (recover) and *act* on it (decide) are
strictly separated from the component that *knows* the answer (grade) — neither recovery nor the
decision ever reads the answer key. Verified adversarially: a tampered result is caught and
rejected, not graded.

## What's proven

**Detection is calibrated** (recovery step):
- False-positive rate **≈ 5%** (measured 5.8% over 120 null trials, within sampling error) — calibrated, not assumed.
- **Power = 100%**: the planted segment is detected at both strong and moderate effect sizes.

**Recovery is accurate** (grader, over a 50-instance set):

| | Result |
|---|---|
| Precision / Recall | **1.0 / 1.0** — found in all 50 noise realizations |
| Magnitude accuracy | **near-unbiased (+0.7%)** — recovered value-uplift matches the truth |
| Every result | firewall re-verified (0 rejected) |

**The decision is correct** (grader, precision@K over the 50-instance set):

| | Result |
|---|---|
| Base rate | **≈ 0.12** — share of accounts in the high-value population |
| precision@50 | **1.0** — of the top-50 accounts the model says to work, all 50 are right |
| precision@200 | **≈ 0.74** — degrades past the ~157 positives, as a metric sanity check |

(Value-uplift is measured in the method's own reference frame — the segment's value relative to a
typical category — which is the quantity the method identifies. precision@K grades the composed
recover→decide call against truth; on this world recovery runs at 1.0, so it isolates the decision
in practice.)

## How I work

The repo *is* the evidence — these are the principles it was built to demonstrate:

- **Inference, not narration.** "High ARPA, low count" is a description; a small segment can look
  high purely from sampling noise. The recovery step separates *truly high and small* from *noisy
  and small* (empirical-Bayes shrinkage), so the finding is earned, not narrated.
- **Measure what you can verify; flag what you can't.** Every headline number is scored against a
  known answer and reported with its uncertainty. The two things v1 *can't* yet verify
  (segment-internal ordering, a no-finding/TN case) are stated as limitations, not hidden.
- **Separate the claim from the judge.** A strict firewall keeps the layer that finds/decides away
  from the layer that knows the truth — and the judge *re-verifies* rather than trusts (a tampered
  result is rejected). It's the same discipline a credible A/B test needs.
- **Be right — and know it.** Claims are revised when the evidence contradicts them. The aim isn't
  a confident story; it's a correct one you can defend in a review.

## Repository map

| Path | What it is | For a reviewer who wants… |
|---|---|---|
| [`00_foundation/DECISION-BRIEF.md`](00_foundation/DECISION-BRIEF.md) | One-page VP-facing decision brief from the pipeline output | business judgment & communication |
| [`00_foundation/`](00_foundation/) | The inference pipeline: generator · recovery · **decision** · grader · harness | rigor, stats, engineering discipline |
| [`00_foundation/L2-DECISION-SPEC.md`](00_foundation/L2-DECISION-SPEC.md) | The decision-layer spec (design → implementation → grading) | how a decision is specified & measured |
| [`01_b2b_saas/`](01_b2b_saas/) | SalesOps & CS analytics: 4 SQL query sets + a rendered Plotly notebook | conventional SQL/BI craft |

## Status

- [x] **Generator** — plants the segment, seals the answer
- [x] **Recovery** — firewalled, calibrated (FPR ≈ 5%, power 100%)
- [x] **Decision** — recovered segment → ranked account prioritization (full universe)
- [x] **Grader** — machine-scores recovery (precision/recall 1.0, near-unbiased magnitude) **and the decision** (precision@50 = 1.0 vs ~0.12 base rate)
- [ ] **Within-segment value ordering** *(next)* — grade the order *inside* the segment against true per-account value (needs an additive L0 field — "Option B")
- [ ] **Specificity / no-finding case** — verify the *absence* of a false segment against ground truth (roadmapped)

## Reproduce

Every headline number above is reproducible from the committed code — no saved outputs required.
CI runs this same path on every push.

```bash
cd 00_foundation
pip install -r ../requirements.txt                 # Python 3.12
python -m pytest world_model/tests recovery/tests grading/tests harness/tests decision/tests  # all checks (100)
python -m world_model.run                          # generate the synthetic world (plants the hidden segment)
python -m recovery.run                             # recover the segment from observations only -> card
python -m decision.run                             # rank the full account universe from the card -> ranking
python -m harness.run --n 50                       # build 50 instances (L0 -> L1 -> L2) -> harness/data/run
python -m grading.run --run-dir harness/data/run            # grade recovery vs truth (precision/recall, magnitude bias)
python -m grading.decision_run --run-dir harness/data/run   # grade the decision vs truth (precision@K)
python -m harness.probe_run                        # detection calibration: false-positive rate + power
```

---

## 日本語サマリ

**一言で**：BizOps/アナリストのポートフォリオです。中核は CRM 推論パイプライン ―
隠れた高価値セグメントを**発見**し、何をすべきかを**意思決定**し、**地上真実に対して
自己採点**します。全数値はソースから再現可能、CI が push 毎に再証明します。

**ビジネス課題**：営業は「転換率」で優先順位を付けるため、「高価値・低転換」セグメント
（1件が典型カテゴリの約2.8倍の価値だが成約数が少ない）が静かに後回しにされ、価値が
放置される。本パイプラインは標準的な CRM テーブル（`accounts`/`opportunities`）だけから
そのセグメントを掘り起こし、**誤検知率を明示**し、**どの口座から攻めるか**を順位付けし、
真実が既知の合成世界で**各段階を検証**します。ダッシュボードではなく、VP に提出できる
「見つけた・こう動く・信頼できる理由」です。

**証明済み**：検出は較正済み（誤検知率 ≈ 5%、検出力100%）／回収は正確（50世界で
精度・再現率1.0、価値倍率は near-unbiased +0.7%）／**意思決定も正しい**
（precision@50 = 1.0、base rate 約0.12に対して。@200 は正例超過で正しく劣化）。

**働き方（このリポジトリ自体が証拠）**：①記述ではなく推論（小カテゴリの高ARPAが真か
雑音かを統計的に弁別）②検証できることを測り、できないことは限界として明示
③主張する層と採点する層を分離し、採点側は信頼せず再検証（改竄は不採点）
④証拠が反すれば主張を改める ― 目的は自信ありげな物語ではなく、レビューで守れる正しさ。

**まず読むなら**：[Decision Brief](00_foundation/DECISION-BRIEF.md)（VP宛て1枚）→
機構は [`00_foundation/`](00_foundation/) → 王道の SQL/BI は [`01_b2b_saas/`](01_b2b_saas/)。

---

*All data here is synthetic and generated by the model, following the standard CRM object model
(accounts, opportunities). The domain is an abstract B2B archetype; nothing is drawn from any real
organization.*

## License

MIT — see [LICENSE](LICENSE).
