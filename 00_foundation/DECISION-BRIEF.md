# Decision Brief — reprioritize the sales motion toward a recovered high-value segment

*One-page brief for a VP of Sales / RevOps. Written from the output of the inference
pipeline in this repo. The world is synthetic (no real org, no real currency), so the
dollar figures below are an explicitly-labeled illustrative sizing, not a measured
result — the **structure** of the recommendation and the **confidence** behind it are
the point.*

---

## Recommendation (BLUF)

**Work a ranked shortlist of accounts in segment `Cat-D` next cycle.** The analysis
recovered a category whose accounts are worth **~2.8× a typical category's** but that
converts poorly — so a conversion-weighted pipeline view has been quietly
deprioritizing it. We can name the accounts, in priority order, and we know the
false-positive rate of the call.

**Confidence: high, and measured.** The detection fires at a **calibrated ~5%
false-positive rate** (not assumed — measured over 120 null trials) with **100%
power** on the planted effect; across 50 independent worlds the recovery is correct
every time (precision/recall 1.0), and the resulting prioritization puts the right
accounts at the top with **precision@50 = 1.0 against a ~12% base rate.**

---

## The problem, in one paragraph

Sales prioritization optimizes for *conversion*: reps work the deals most likely to
close. That is rational locally and wrong globally when a segment is **high-value but
low-conversion** — each win is large, but because few of them close, the segment
looks unpromising on a win-rate dashboard and slides down the queue. The value is
real; it is *masked* by conversion. Aggregate ARPA does not surface it either,
because the segment is small enough to be diluted in the blended average.

## What the analysis found

| | Finding | How we know |
|---|---|---|
| **Where** | Category `Cat-D` — recovered from `accounts` + `opportunities` alone | Two-way log decomposition + empirical-Bayes shrinkage; a small category that *survives* shrinkage is genuinely elevated, not noise |
| **How much** | ~2.8× the value of a typical category's account (geomean-relative) | Magnitude is near-unbiased vs. ground truth (+0.7% over 50 worlds) |
| **How sure** | False-positive rate ≈ 5%, power 100% | Calibrated against a permutation null, measured on a held-out null batch |
| **Who to work** | 157 accounts (~13% of the universe), ranked | L2 ranks all 1,200 accounts; the recovered segment fills the top of the list |

## The decision the ranking informs

The prioritizer ranks the **entire** account universe by three observable keys, in
order: (1) in the recovered segment, (2) segment tier (Enterprise > MidMarket > SMB),
(3) under-penetration (fewest wins first — "high value, not yet worked"). A rep
working top-down therefore hits high-value, under-penetrated accounts first. Because
the ranking is graded by precision@K against the truth, we know the shortlist is
right, not just plausible: **of the top 50 accounts the model says to pursue, all 50
are in the genuinely high-value population.**

## Illustrative sizing (assumptions labeled — not a measured result)

To make the decision tangible, a back-of-envelope on *illustrative* inputs:

- Reachable under-penetrated accounts in the segment this cycle: **~50** (= the K=50
  shortlist precision@K certifies).
- Assume a typical category's won deal ≈ **¥1.0M ARR**; the segment runs **~2.8×** →
  **~¥2.8M** per win.
- Assume a focused motion lifts the segment's low conversion enough to add **~0.5 wins
  per worked account** over a cycle.

→ **~50 × 0.5 × ¥2.8M ≈ ¥70M** incremental ARR exposure from one cycle's reprioritization —
versus working the same 50 rep-hours on the blended pipeline at typical value. *Every
input here is an assumption; the measured part is **which** 50 accounts and **how
confident** we are they are the right ones.* The model gives the targeting; the org
supplies the conversion lift and deal-size numbers to finalize the business case.

## Risks & what would change the call

- **Segment-value ordering is an assumption, not a proof.** The Enterprise > MidMarket
  > SMB tiering inside the segment is an observable heuristic; ranking *within* the
  segment is not yet validated against true per-account value (a planned measurement).
  → Don't over-index on the intra-segment order; the segment-level call is the solid one.
- **The lift is unproven until tested.** The analysis proves *where* the value is, not
  that a new motion will convert it. → Run it as a measured experiment: a holdout of
  comparable accounts, pre-registered success metric (segment win-rate / ARR per rep-hour),
  and read it the same way we calibrated the detector — against a null.
- **Composition can drift.** Re-run the recovery each quarter; the firewall + calibration
  make that a one-command, gradable refresh.

## Recommended next steps

1. **This week** — hand reps the top-50 ranked shortlist; brief them on the "high value,
   low conversion" framing so the low win-rate doesn't scare them off.
2. **This cycle** — stand up the holdout experiment; instrument segment win-rate and ARR
   per rep-hour.
3. **Next cycle** — read the experiment against a null; if the lift is real, fold the
   recovered-segment signal into standard prioritization and re-run recovery quarterly.

---

## 日本語サマリ（要点）

**結論（BLUF）**：次サイクルは、回収された高価値セグメント `Cat-D` の**ランク付き
ショートリスト**を攻めるべき。このセグメントの口座は典型カテゴリの**約2.8倍**の価値だが
転換率が低いため、転換率重視のパイプライン運用が静かに後回しにしてきた。攻めるべき口座を
優先順位付きで名指しでき、しかもその判断の**誤検知率まで分かっている**。

**確信度：高く、かつ測定済み**。検出は**較正済み誤検知率 約5%**（仮定ではなく120回の
帰無試行で測定）・**検出力100%**。50個の独立世界で回収は毎回正解（精度/再現率1.0）、
優先順位付けは**precision@50 = 1.0（base rate 約12%に対して）**。

**問題**：営業優先順位は「転換率」を最適化する。局所的に合理的だが、「高価値・低転換」
セグメントでは大域的に誤る ― 1件が大きいのに成約数が少なく、勝率ダッシュボード上は
不振に見えて後回しになる。価値は実在し、転換率に**覆い隠されている**。

**意思決定**：全1,200口座を3キー（①回収セグメント所属 ②セグメント階層 ③浸透不足）の
辞書式で順位付け。上から攻めれば高価値・未浸透の口座に最初に当たる。precision@K で採点
されているため、ショートリストは「もっともらしい」ではなく「正しい」と分かる。

**試算（仮定は明示・測定結果ではない）**：約50口座 × 0.5勝/口座 × ¥2.8M ≈ **約¥70M** の
増分ARRエクスポージャ（1サイクル）。測定済みなのは「どの50口座か」と「その確信度」。
転換率リフトと単価は組織側の数値で確定する。

**リスク**：①セグメント内順序は仮定（真の口座別価値での検証は今後）②リフトは未検証 ―
**ホールドアウト実験**で測る（事前登録した指標を帰無分布に対して読む）③構成は変化しうる
ので四半期ごとに再回収（firewall + 較正により1コマンドで採点可能）。
