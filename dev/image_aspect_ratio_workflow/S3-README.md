# S3 画像アスペクト比検出ワークフロー

この n8n ワークフローは、AWS S3 から画像ファイルを取得し、アスペクト比を検出して画像の向きに応じて異なる処理パスに分岐します。

## 機能

- AWS S3 からの画像ファイル自動取得
- 画像のアスペクト比を自動計算
- 画像の向きによる分類：
  - **横長** (wide): アスペクト比 > 1.5
  - **縦長** (tall): アスペクト比 < 0.75
  - **正方形** (square): 0.75 ≤ アスペクト比 ≤ 1.5
- S3 ファイル情報の詳細取得（ファイルサイズ、MIME タイプ等）
- 各カテゴリに応じた推奨アクションの提供

## ワークフロー構成

### ノード構成

1. **Webhook Trigger** - S3 画像処理リクエストを受信
2. **Prepare S3 Parameters** - S3 アクセス用パラメータを準備
3. **S3 Download Image** - AWS S3 から画像ファイルをダウンロード
4. **S3 Image Analyzer** - 取得した画像のアスペクト比を分析
5. **Aspect Ratio Switch** - 画像の向きによって分岐
6. **Wide Image Processor** - 横長画像の処理
7. **Tall Image Processor** - 縦長画像の処理
8. **Square Image Processor** - 正方形画像の処理
9. **Error Handler** - エラー処理

## 事前準備

### 1. AWS 認証情報の設定

n8n の管理画面で AWS 認証情報を設定：

1. 「Credentials」→「Add Credential」
2. 「AWS」を選択
3. 以下の情報を入力：
   - Access Key ID
   - Secret Access Key
   - Region (例: ap-northeast-1)

### 2. S3 バケットの準備

- 画像ファイルが保存された S3 バケットを用意
- n8n からアクセス可能な権限設定

## 使用方法

### 1. ワークフローのインポート

n8n の管理画面で以下の手順を実行：

1. 「Workflows」→「Import from file」
2. `s3-image-aspect-ratio-workflow.json` を選択
3. AWS 認証情報を設定
4. ワークフローをアクティブ化

### 2. S3 画像データの処理リクエスト

Webhook エンドポイントに POST リクエストで S3 ファイル情報を送信：

```bash
# 基本的な使用例
curl -X POST http://your-n8n-instance/webhook/s3-image-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "your-image-bucket",
    "file_key": "images/sample-photo.jpg"
  }'
```

### 3. 必要なデータ形式

リクエストボディに以下の形式で S3 ファイル情報を含める：

#### 基本形式

```json
{
  "bucket_name": "your-image-bucket",
  "file_key": "images/photo.jpg"
}
```

#### 寸法が既知の場合

```json
{
  "bucket_name": "your-image-bucket",
  "file_key": "images/banner.jpg",
  "width": 1920,
  "height": 1080
}
```

#### 代替フィールド名

```json
{
  "bucket_name": "your-image-bucket",
  "image_key": "images/profile.jpg",
  "image_width": 500,
  "image_height": 500
}
```

## 寸法検出方法

このワークフローは以下の順序で画像の寸法を検出します：

1. **明示的な寸法指定**: リクエストの `width`/`height` フィールド
2. **ファイル名からの推測**: `image_1920x1080.jpg` のようなパターン
3. **ファイル名キーワード**: `banner`, `portrait`, `square` 等から推測
4. **ファイルサイズからの概算**: バイナリデータサイズから推測

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
    "decimal_ratio": 1.78,
    "file_size": 2048576,
    "mime_type": "image/jpeg",
    "s3_source": {
      "bucket": "your-image-bucket",
      "key": "images/banner.jpg"
    }
  },
  "processing_result": {
    "category": "wide_image",
    "message": "S3から横長画像を検出しました。アスペクト比: 1.78",
    "recommended_action": "バナー画像やヘッダー画像として使用することをお勧めします",
    "dimensions": "1920x1080",
    "file_info": {
      "size": 2048576,
      "mime_type": "image/jpeg",
      "s3_location": "s3://your-image-bucket/images/banner.jpg"
    },
    "processed_at": "2024-01-01T12:00:00.000Z",
    "processing_type": "s3_source"
  }
}
```

### エラーケースの場合

```json
{
  "processing_result": {
    "category": "unknown_or_error",
    "message": "S3画像の分析中にエラーが発生したか、画像の種類を特定できませんでした",
    "recommended_action": "S3のファイルパスと画像ファイルを確認してください",
    "error_details": "Failed to download image from S3",
    "file_info": {
      "s3_location": "s3://your-image-bucket/images/missing.jpg"
    },
    "processed_at": "2024-01-01T12:00:00.000Z",
    "processing_type": "s3_source"
  }
}
```

## カスタマイズ

### デフォルトバケット名の設定

`Prepare S3 Parameters` ノードで、デフォルトのバケット名を設定：

```javascript
"value": "={{ $json.bucket_name || 'your-default-bucket' }}"
```

### 寸法推測ロジックの調整

`S3 Image Analyzer` ノードの JavaScript コードで、ファイル名パターンや推測ロジックをカスタマイズ：

```javascript
// ファイル名パターンによる推測
if (fileName.includes("banner") || fileName.includes("header")) {
  width = 1920;
  height = 1080; // デフォルト横長
} else if (fileName.includes("portrait") || fileName.includes("mobile")) {
  width = 1080;
  height = 1920; // デフォルト縦長
}
```

### アスペクト比の閾値変更

各プロセッサーノードで、アスペクト比の閾値を調整可能。

## テストケース

### cURL テスト例

```bash
# 横長画像のテスト
curl -X POST http://your-n8n-instance/webhook/s3-image-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket",
    "file_key": "images/banner_1920x1080.jpg"
  }'

# 縦長画像のテスト
curl -X POST http://your-n8n-instance/webhook/s3-image-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket",
    "file_key": "images/portrait_1080x1920.jpg"
  }'

# 正方形画像のテスト
curl -X POST http://your-n8n-instance/webhook/s3-image-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket",
    "file_key": "images/square_500x500.jpg"
  }'
```

## 注意事項

### AWS 権限

S3 バケットへのアクセスに必要な IAM 権限：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectMetadata"],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

### パフォーマンス

- 大きな画像ファイルの処理には時間がかかる場合があります
- バイナリデータの転送により、ネットワーク使用量が増加します
- 適切なタイムアウト設定を行ってください

### 制限事項

- 現在の実装では、画像の実際の寸法を取得するために画像処理ライブラリが必要です
- ファイル名やサイズからの推測に依存している部分があります
- より正確な分析には、Sharp や ImageMagick などのライブラリの統合が推奨されます

## トラブルシューティング

### S3 接続エラー

- AWS 認証情報が正しく設定されていることを確認
- S3 バケットの権限設定を確認
- リージョン設定が正しいことを確認

### 画像が見つからない

- バケット名とファイルキーが正しいことを確認
- S3 コンソールでファイルの存在を確認

### 寸法検出の精度向上

- リクエストに明示的に `width` と `height` を含める
- ファイル名に寸法情報を含める（例: `image_1920x1080.jpg`）
- 画像処理ライブラリの統合を検討

## 関連ファイル

- `image-aspect-ratio-workflow.json`: 基本版（Webhook 直接入力）
- `test-requests.json`: テストケース集
- `README.md`: 基本版の使用方法
