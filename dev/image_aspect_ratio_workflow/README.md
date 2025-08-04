# 画像アスペクト比検出ワークフロー

この n8n ワークフローは、入力された画像のアスペクト比を検出し、画像の向きに応じて異なる処理パスに分岐します。

## 機能

- 画像のアスペクト比を自動計算
- 画像の向きによる分類：
  - **横長** (wide): アスペクト比 > 1.5
  - **縦長** (tall): アスペクト比 < 0.75
  - **正方形** (square): 0.75 ≤ アスペクト比 ≤ 1.5
- 各カテゴリに応じた推奨アクションの提供

## ワークフロー構成

### ノード構成

1. **Webhook Trigger** - 画像データを受信
2. **Aspect Ratio Calculator** - アスペクト比を計算
3. **Aspect Ratio Switch** - 画像の向きによって分岐
4. **Wide Image Processor** - 横長画像の処理
5. **Tall Image Processor** - 縦長画像の処理
6. **Square Image Processor** - 正方形画像の処理
7. **Error Handler** - エラー処理

## 使用方法

### 1. ワークフローのインポート

n8n の管理画面で以下の手順を実行：

1. 「Workflows」→「Import from file」
2. `image-aspect-ratio-workflow.json` を選択
3. ワークフローをアクティブ化

### 2. 画像データの送信

Webhook エンドポイントに POST リクエストで画像データを送信：

```bash
# 例：cURLを使用した送信
curl -X POST http://your-n8n-instance/webhook/image-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "width": 1920,
    "height": 1080,
    "filename": "sample-image.jpg"
  }'
```

### 3. 必要なデータ形式

リクエストボディに以下のいずれかの形式で画像の寸法情報を含める：

```json
{
  "width": 1920,
  "height": 1080,
  "filename": "image.jpg"
}
```

または

```json
{
  "image_width": 1920,
  "image_height": 1080,
  "filename": "image.jpg"
}
```

## 出力例

### 横長画像の場合

```json
{
  "image_analysis": {
    "width": 1920,
    "height": 1080,
    "aspectRatio": 1.78,
    "orientation": "wide",
    "ratio_text": "1920:1080",
    "decimal_ratio": 1.78
  },
  "processing_result": {
    "category": "wide_image",
    "message": "横長画像を検出しました。アスペクト比: 1.78",
    "recommended_action": "バナー画像やヘッダー画像として使用することをお勧めします",
    "dimensions": "1920x1080",
    "processed_at": "2024-01-01T12:00:00.000Z"
  }
}
```

### 縦長画像の場合

```json
{
  "processing_result": {
    "category": "tall_image",
    "message": "縦長画像を検出しました。アスペクト比: 0.56",
    "recommended_action": "ポートレート写真やモバイル向け画像として使用することをお勧めします"
  }
}
```

### 正方形画像の場合

```json
{
  "processing_result": {
    "category": "square_image",
    "message": "正方形に近い画像を検出しました。アスペクト比: 1.0",
    "recommended_action": "プロフィール画像やアイコンとして使用することをお勧めします"
  }
}
```

## カスタマイズ

### アスペクト比の閾値変更

`Aspect Ratio Calculator` ノードの JavaScript コードで閾値を調整できます：

```javascript
// 現在の設定
if (aspectRatio > 1.5) {
  orientation = "wide";
} else if (aspectRatio < 0.75) {
  orientation = "tall";
} else {
  orientation = "square";
}
```

### 処理ロジックの追加

各プロセッサーノード（Wide/Tall/Square Image Processor）で、画像の向きに応じた独自の処理ロジックを追加できます。

## 注意事項

- このワークフローは画像の寸法情報（width, height）をリクエストデータから取得します
- 実際の画像ファイルから寸法を自動抽出する場合は、追加の画像処理ライブラリが必要です
- バイナリデータの処理が必要な場合は、適切なファイルアップロード機能を追加してください

## トラブルシューティング

### 画像の寸法が取得できない場合

- リクエストデータに `width` と `height` または `image_width` と `image_height` が含まれていることを確認
- データ型が数値であることを確認

### ワークフローが動作しない場合

- Webhook トリガーがアクティブになっていることを確認
- n8n インスタンスの Webhook URL が正しいことを確認
- リクエストの Content-Type が適切に設定されていることを確認
