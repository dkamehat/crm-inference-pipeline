# Foundation — the CRM inference pipeline (L0 → L3)

The flagship of this portfolio. A layered pipeline that finds a hidden high-value
segment in synthetic CRM data, decides which accounts to work, and **grades every
step against ground truth** — with a strict firewall between the layers that *claim
/ act* and the layer that *knows the answer*.

```
L0  world_model   plant a known high-value / low-conversion segment; seal the answer (manifest)
L1  recovery      recover the segment from observations only — calibrated, firewalled  -> card
L2  decision      rank the full account universe from the card -> prioritized list
L3  grading       the sole answer-reader: score recovery AND the decision vs ground truth
    harness       orchestrate L0→L1→L2 across many seeds so L3 grades over a distribution
```

## Read in this order

1. **[DECISION-BRIEF.md](DECISION-BRIEF.md)** — the one-page, VP-facing output. What
   the whole pipeline is *for*: a finding, a decision, and a stated confidence.
2. **[world_model/](world_model/)** (L0) — the generator. Why a synthetic world makes
   the quality numbers *measurable* instead of asserted.
3. **[recovery/](recovery/)** (L1) — inference, not narration: empirical-Bayes
   shrinkage + permutation-null calibration, under a firewall.
4. **[decision/](decision/)** (L2) — the recovered segment → a graded prioritization
   of every account. See also **[L2-DECISION-SPEC.md](L2-DECISION-SPEC.md)**.
5. **[grading/](grading/)** (L3) — the only layer allowed to read the answer; it
   *re-verifies* the firewall rather than trusting it.
6. **[harness/](harness/)** — multi-seed orchestration so L3 grades over a distribution,
   never a single lucky draw.

## The firewall, in one line

Recovery (L1) and decision (L2) read **only** the observation CSVs (+ L1's card for L2);
both stamp `manifest_read=false` and an `observation_hash`. Grading (L3) recomputes that
hash and confirms it — a layer that peeked at the answer is **rejected, not graded**.

## What's measured (50-seed set)

| Layer | Metric | Result |
|---|---|---|
| L1 detection | false-positive rate / power | ≈ 5% / 100% |
| L1 recovery | precision / recall · magnitude bias | 1.0 / 1.0 · +0.7% (near-unbiased) |
| L2 decision | precision@50 vs base rate | 1.0 vs ≈ 0.12 |

## Run it

```bash
pip install -r ../requirements.txt                 # Python 3.12
python -m pytest world_model/tests recovery/tests grading/tests harness/tests decision/tests  # 100 checks
python -m world_model.run && python -m recovery.run && python -m decision.run
python -m harness.run --n 50 --run-dir ./harness/data/run
python -m grading.run --run-dir ./harness/data/run            # recovery vs truth
python -m grading.decision_run --run-dir ./harness/data/run   # decision vs truth (precision@K)
python -m harness.probe_run                                   # detection calibration
```

---

## 日本語サマリ

ポートフォリオの中核。合成 CRM データから隠れた高価値セグメントを**発見(L1)**し、
攻めるべき口座を**意思決定(L2)**し、**各段階を地上真実に対して採点(L3)**する階層型
パイプライン。主張・実行する層（L1/L2）と答えを知る層（L3）の間に厳密な
**ファイアウォール**を敷く。L1/L2 は観測のみ（L2 は加えて L1 card）を読み、
`manifest_read=false` と `observation_hash` を刻む。L3 はそのハッシュを再計算して検証し、
**答えを覗いた層は不採点で棄却**する。

読む順：①[DECISION-BRIEF.md](DECISION-BRIEF.md)（VP宛て1枚の出力）→ ②world_model(L0)
→ ③recovery(L1) → ④decision(L2, [仕様](L2-DECISION-SPEC.md)) → ⑤grading(L3) → ⑥harness。

測定値（50シード）：L1検出 誤検知率≈5%/検出力100%、L1回収 精度・再現率1.0・価値倍率
バイアス+0.7%、L2意思決定 precision@50=1.0（base rate≈0.12）。
