# GitHub 公開手順

## 全体フロー

1. ローカルにリポジトリを配置
2. **pre-commit hook を有効化**(これを最初にやる)
3. **手動 grep で個人情報チェック**
4. git init → commit → push
5. GitHub Actions が自動でチェック → 緑なら成功

---

## Step 1: ファイルをローカルに配置

`~/projects/sales-analytics-portfolio/` に展開:

```bash
mkdir -p ~/projects/sales-analytics-portfolio
cd ~/projects/sales-analytics-portfolio
# このパッケージの中身をコピー (zip の場合は解凍)
```

---

## Step 2: pre-commit hook を有効化

**最初に必ずこれをやる**。これをやらずに commit すると、防御策が効かない。

```bash
cd ~/projects/sales-analytics-portfolio
git init -b main
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit

# テスト実行(空でも動作確認)
.githooks/pre-commit
```

---

## Step 3: 手動 grep チェック

`docs/PRE-PUBLISH-CHECKLIST.md` の §2 にあるコマンドを実行し、**全て空の結果**であることを確認:

```bash
grep -rin "kamekichii\|亀畑" . --include='*.md' --include='*.ipynb' --include='*.py'
grep -rin "demae\|出前館" . --include='*.md' --include='*.ipynb' --include='*.py'
grep -rin "komoju\|sakana ai" . --include='*.md' --include='*.ipynb' --include='*.py'
grep -rin "60,000 merchants\|105 sales reps" . --include='*.md' --include='*.ipynb' --include='*.py'
```

何か出てきたら **commit 禁止**。修正してから次のステップ。

---

## Step 4: 初回 commit と push

```bash
git add .
git commit -m "Initial commit: Phase 1 B2B SaaS; defense layers in place"
# ↑ ここで pre-commit hook が動く。
# 個人情報パターンを検出したら commit が拒否される。

gh repo create dkamehat/sales-analytics-portfolio \
  --public \
  --source=. \
  --remote=origin \
  --push \
  --description "Sales operations & customer success analytics across three businesses. SQL + Python + Plotly. Synthetic Salesforce-shaped data."
```

---

## Step 5: GitHub Actions の確認

push 後、ブラウザで以下を確認:

1. `https://github.com/dkamehat/sales-analytics-portfolio/actions` を開く
2. "Personal Info Check" ワークフローが **緑のチェックマーク**になっているか
3. もし赤(エラー)になっていたら、ログを見て修正対象を特定 → 修正 → 再 push

---

## Claude Code に渡す場合のコマンド一式

ターミナル(あるいはClaude Code) にこのまま貼り付け:

```bash
cd ~/projects/sales-analytics-portfolio

# 1. Pre-commit hook 有効化
git init -b main
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit

# 2. 手動 grep チェック(全て空であること)
echo "=== Personal info grep check ==="
grep -rin "kamekichii\|亀畑\|demae\|出前館\|komoju\|sakana ai\|60,000 merchants\|105 sales reps" \
  . --include='*.md' --include='*.ipynb' --include='*.py' --include='*.sql' --include='*.yml' \
  && echo "❌ FOUND - DO NOT COMMIT" || echo "✓ clean"

# 3. Commit と push
git add .
git commit -m "Initial commit: Phase 1 B2B SaaS; defense layers in place"

# 4. GitHub リポジトリ作成と push
gh repo create dkamehat/sales-analytics-portfolio \
  --public \
  --source=. \
  --remote=origin \
  --push \
  --description "Sales operations & customer success analytics across three businesses. SQL + Python + Plotly. Synthetic Salesforce-shaped data."

# 5. URL 表示
echo "Live at: https://github.com/dkamehat/sales-analytics-portfolio"
echo "Actions: https://github.com/dkamehat/sales-analytics-portfolio/actions"
```

---

## Notebook レンダリングの確認

push 後、ブラウザで以下を開いて、Plotly チャートがインタラクティブに動くことを確認:

`https://github.com/dkamehat/sales-analytics-portfolio/blob/main/01_b2b_saas/notebooks/analysis.ipynb`

GitHub の Notebook レンダラーは Plotly に対応しています。もし動かない場合は nbviewer をフォールバックとして使えます:

`https://nbviewer.org/github/dkamehat/sales-analytics-portfolio/blob/main/01_b2b_saas/notebooks/analysis.ipynb`

---

## 防御策の構成

| ファイル | 役割 |
|---|---|
| `.githooks/pre-commit` | ローカル commit 時に個人情報パターンをブロック |
| `.github/workflows/check-personal-info.yml` | push/PR 時に同じパターンをチェック (GitHub Actions) |
| `.gitignore` | `.env` `*.sqlite` `notes/` `CLAUDE.md` 等を除外 |
| `docs/PRE-PUBLISH-CHECKLIST.md` | 人間レビュー用の手順書 |

3層 (ローカルhook + CI + 人間レビュー) で守ります。1層でも漏れた時の備え。

---

## 応募メールへの記載例

```
Portfolio: https://github.com/dkamehat/sales-analytics-portfolio

  Phase 1 (published): B2B SaaS — 4 dashboards built with SQL + Python + Plotly
  on Salesforce-shaped synthetic data. Per-section Design Notes make
  the analytical reasoning explicit.

  Phase 2-5 (incremental): Food Delivery, EC Marketplace, advanced
  pandas analytics, and field-sales geographic optimization.
```
