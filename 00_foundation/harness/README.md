# Orchestration harness — multi-seed instance generation

Produces the cross-seed set of `(manifest, card, ranking, accounts, opportunities)`
instances that the L3 graders aggregate over. For each seed it runs **L0** (generator),
**L1** (recovery), and **L2** (decision), and persists the grader files into
`run_dir/seed_<n>/`: the quad the recovery grader reads, plus the L2
`decision_ranking.json` the decision grader reads.

This is the orchestration lane: it **imports and calls** L0/L1/L2/L3 but modifies
none of them (additive).

## Firewall discipline (the point of this lane)

L1 and L2 receive **only the two observation CSVs** (L2 additionally reads L1's card,
which itself carries no answer). The manifest is emitted into a private staging dir,
and only `accounts.csv` + `opportunities.csv` are copied into a separate, manifest-free
input dir that L1/L2 read. So:
- the manifest is never passed to L1/L2 and never sits in their input directory;
- every generated card AND ranking keeps `manifest_read == false`;
- the graders' firewall re-verification passes (the observation hash matches —
  it is over the CSV bytes, independent of directory).

## Run

```bash
# from 00_foundation/
python -m harness.run --n 50                 # fixed schedule: seeds 1000..1049 (L0->L1->L2)
python -m harness.run --seeds 1000,1001      # explicit list
python -m grading.run --run-dir 00_foundation/harness/data/run            # grade recovery
python -m grading.decision_run --run-dir 00_foundation/harness/data/run   # grade the decision (precision@K)
python -m pytest harness/tests/
```

The schedule is fixed/reproducible (`manifest.seed == schedule seed`). Generated
quads are artifacts under a git-ignored `data/run/`; only source + tests are
committed. Because V1's wedge is a profile constant (same category every seed),
the set measures how reliably the canonical wedge is recovered across noise
realizations, plus the magnitude-bias distribution.

---

## 日本語サマリ

L3 grader が集計する seed 横断の `(manifest, card, ranking, accounts, opportunities)`
集合を生成します。各 seed で **L0**（生成器）・**L1**（recovery）・**L2**（decision）を
回し、grader 用ファイルを `run_dir/seed_<n>/` に永続化（recovery grader が読む quad ＋
decision grader が読む `decision_ranking.json`）。L0/L1/L2/L3 は import・呼び出しのみで
**改変しません**（additive）。

firewall 規律が要点：L1/L2 には**観測 CSV 2枚だけ**を渡します（L2 は加えて L1 card を
読むが、card 自体に答えは無い）。manifest は private な staging に出し、観測2枚のみを
manifest 無しの別入力 dir にコピーするため、生成 card も ranking も
`manifest_read == false` を保ち、grader の firewall 再検証を通ります。schedule は固定・
再現可能（`manifest.seed == seed`）、生成物は .gitignore（source ＋ test のみ commit）。
