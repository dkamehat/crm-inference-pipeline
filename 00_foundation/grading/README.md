# L3 Grading — answer-checking the recovery

Machine-scores the L1 recovery card against the world model's ground truth. L3 is
the **sole layer permitted to read the answer** (`_ground_truth.json`), and unlike
L0/L1 the **grade is the deliverable**. The card is consumed as a **black box**
(persisted JSON) — L3 never imports or re-runs L1.

## v1 scope (L3-GRADING-SPEC §4, §5.1)

Decision-gated **TP / FP / FN** + **magnitude calibration**. Not in v1:
- **TN** — the V1 generator always plants a wedge (§4.3), so no manifest-graded
  TN instances exist; reported as `pending no-wedge profile` (hand-off §8.1).
- **post_prob calibration (§5.2)** — deferred: the card exposes a posterior only
  for the recovered wedge, not per category, so there are no negatives to calibrate
  against yet (hand-off §8.2).

Extension points are left clean (no faked TN/post_prob results).

## Match predicate (field-driven, segment-tolerant)

```
planted_cat = manifest.wedge.category               # indexed, never hardcoded
planted_mag = manifest.cat_value_mult[planted_cat]
TP = decision and recovered_category == planted_cat
FP = decision and recovered_category != planted_cat
FN = (wedge always planted in V1) and not decision
```

The planted wedge is a **category main effect** spanning all segments, so segment
is **never** a TP gate — `cell_breakdown[].segment_id` is a tolerant cross-check
only. Magnitude calibration binds to `cat_value_mult` (the value elevation L1
reports as `elevation_ratio`), never `true_cat_w`.

## Firewall re-verification (§4.4)

Before grading, L3 recomputes the observation hash over the two observed CSVs and
confirms it equals the card's, and that `manifest_read == false`. A card that fails
is **rejected, never graded**. All answer reads go through one accessor
(`ground_truth.load`).

## Layout

```
grading/
  ground_truth.py  THE single answer accessor + field helpers   (§1)
  card_io.py       load a persisted card as data (no L1 import)  (§2)
  provenance.py    pure observation-hash primitive (replicated)  (§4.4)
  firewall.py      re-verify the card's provenance attestation   (§4.4)
  match.py         decision-gated, segment-tolerant predicate    (§4.1)
  calibration.py   magnitude calibration vs planted elevation    (§5.1)
  grade.py         aggregate over a SET of (manifest, card) pairs (§4, §7)
  run.py           entry point
  data/            generated reports (git-ignored)
```

## Run

```bash
# from 00_foundation/
python -m grading.run --run-dir <dir-of-per-seed-subdirs>   # aggregate
python -m grading.run                                        # single-pair smoke
python -m pytest grading/tests/
```

Each run-dir subdir holds `_ground_truth.json`, `recovery_card.json`,
`accounts.csv`, `opportunities.csv`. L3 does **not** generate these (that needs
L1) — the multi-seed set comes from an L1/orchestration-lane harness.

---

## 日本語サマリ

L1 の recovery card を世界モデルの地上真実と機械照合し、TP/FP/FN と規模較正を出す
採点層です。L3 は**答え（`_ground_truth.json`）を読める唯一の層**で、L0/L1 と違い
**採点結果が成果物**。card は **black box**（永続化 JSON）として読み、L1 を import も
再実行もしません。

v1 は **TP/FP/FN ＋ 規模較正**のみ。TN は V1 が常に wedge を植えるため採点不能
（`pending no-wedge profile`・§8.1 ハンドオフ）、post_prob 較正（§5.2）は card が
recovered wedge の事後確率しか持たないため延期（§8.2）。捏造スタブは置かず拡張点のみ。

判定は**フィールド駆動・segment 寛容**：`wedge.category` を index（ハードコード禁止）、
segment は TP ゲートにしない。規模較正は `cat_value_mult`（value 上昇＝`elevation_ratio`）
に束縛（`true_cat_w` ではない）。採点前に observation_hash を2CSVから再計算し card と
照合（`manifest_read==false` も確認）、不一致 card は**採点せず reject**。答えへのアクセスは
単一 accessor 経由。生成レポートは .gitignore。
