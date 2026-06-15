# Orchestration harness — multi-seed quad generation

Produces the cross-seed set of `(manifest, card, accounts, opportunities)` quads
that the L3 grader aggregates over. For each seed it runs **L0** (generator) and
**L1** (recovery) and persists exactly the four grader files into
`run_dir/seed_<n>/`.

This is the L1 / orchestration lane: it **imports and calls** L0/L1/L3 but modifies
none of them (additive).

## Firewall discipline (the point of this lane)

L1 receives **only the two observation CSVs**. The manifest is emitted into a
private staging dir, and only `accounts.csv` + `opportunities.csv` are copied into
a separate, manifest-free input dir that L1 reads. So:
- the manifest is never passed to L1 and never sits in L1's input directory;
- every generated card keeps `manifest_read == false`;
- the grader's firewall re-verification passes (the observation hash matches —
  it is over the CSV bytes, independent of directory).

## Run

```bash
# from 00_foundation/
python -m harness.run --n 50                 # fixed schedule: seeds 1000..1049
python -m harness.run --seeds 1000,1001      # explicit list
python -m grading.run --run-dir 00_foundation/harness/data/run   # then grade the set
python -m pytest harness/tests/
```

The schedule is fixed/reproducible (`manifest.seed == schedule seed`). Generated
quads are artifacts under a git-ignored `data/run/`; only source + tests are
committed. Because V1's wedge is a profile constant (same category every seed),
the set measures how reliably the canonical wedge is recovered across noise
realizations, plus the magnitude-bias distribution.

---

## 日本語サマリ

L3 grader が集計する seed 横断の `(manifest, card, accounts, opportunities)` quad 集合を
生成します。各 seed で **L0**（生成器）と **L1**（recovery）を回し、grader が期待する
4ファイルちょうどを `run_dir/seed_<n>/` に永続化。L0/L1/L3 は import・呼び出しのみで
**改変しません**（additive）。

firewall 規律が要点：L1 には**観測 CSV 2枚だけ**を渡します。manifest は private な
staging に出し、`accounts.csv` + `opportunities.csv` のみを manifest 無しの別入力 dir に
コピーして L1 に渡すため、生成 card は `manifest_read == false` を保ち、grader の
firewall 再検証を通ります。schedule は固定・再現可能（`manifest.seed == seed`）、
生成 quad は .gitignore（source ＋ test のみ commit）。
