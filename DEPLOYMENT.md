## デプロイ & 運用手順

このリポジトリを GitHub 上で「定期 (07:00/17:00 JST) に Gemini API でスコアリングし、`docs/rss.xml` を GitHub Pages で公開」するための具体手順です。

### 1. リポジトリ要件
- デフォルトブランチ: `main`（別ならワークフロー cron のブランチ参照に注意）
- Actions 有効化済み

### 2. Secrets / Variables 設定
GitHub リポジトリ: Settings > Secrets and variables > Actions

1. Secrets タブで New repository secret:
   - Name: `GEMINI_API_KEY`
   - Value: (取得した Gemini API Key)
2. Variables タブで New variable:
   - Name: `SITE_BASE_URL`
   - Value: `https://<your-account>.github.io/rssCallSystem/` (末尾スラッシュ必須)

CLI (gh) での設定例:
```
export REPO="<owner>/<repo>"  # 例: TakMczk/rssCallSystem
gh secret set GEMINI_API_KEY -R "$REPO" --body "$GEMINI_API_KEY"
gh variable set SITE_BASE_URL -R "$REPO" --body "https://<your-account>.github.io/rssCallSystem/"
```

### 3. GitHub Pages 設定
Settings > Pages:
1. Build and deployment: Source = "Deploy from a branch"
2. Branch = `main` / `/docs`
3. 保存
4. 発行 URL が表示される (数分かかる)

CLI (Pages 未構成時):
```
gh api -X POST repos/:owner/:repo/pages \
  -f source[branch]=main -f source[path]=/docs || \
  echo "Pages 既に設定済みか確認"
```

### 4. 初回動作確認
1. 手動ワークフロー起動: Actions > Update Curated RSS > Run workflow
2. 実行成功後 commit 差分に `docs/rss.xml` 更新が含まれる
3. 公開 URL `https://<your-account>.github.io/rssCallSystem/rss.xml` にアクセスし XML が取得できる

### 5. cron スケジュール
`update_rss.yml` の cron: `0 22,8 * * *` (UTC) → JST 07:00 / 17:00
変更する場合はファイル編集し commit。

### 6. 失敗時トラブルシュート
| 症状 | 確認ポイント | 対処 |
|------|--------------|------|
| 401/403 | Secrets 設定漏れ | `GEMINI_API_KEY` 再登録 |
| 404 モデル | `GEMINI_MODEL` 値 | `gemini-1.5-flash` に戻す |
| RSS 生成なし | ワークフローログ | fetch/score ログ確認 |
| 日本時間がずれる | cron 式 | UTC であるか再確認 |

### 7. ローカル簡易検証
```
./scripts/local_run.sh
```
(事前に `chmod +x scripts/*.sh`)

### 8. セキュリティ留意
- API Key を Issue / PR ログへ貼らない
- フォークでの無制限実行を防ぐため権限/制限設定検討

### 9. 拡張案
- 生成後 feed validator を呼び結果を PR コメント
- スコアキャッシュ TTL 導入

---
以上。
