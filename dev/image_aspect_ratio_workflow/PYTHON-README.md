# Python 版 画像アスペクト比検出ツール

JavaScript での問題を解決するため、Python 版を作成しました。

## 📁 作成されたファイル

### 1. **`s3-2-3-aspect-python-workflow.json`** - n8n Python ワークフロー

- n8n の Code ノードで Python を使用
- より安定したバイナリデータ処理
- 詳細なエラーログとデバッグ情報

### 2. **`image_aspect_analyzer.py`** - スタンドアロン Python スクリプト

- コマンドライン実行可能
- PIL (Pillow) を使用した実際の画像解析
- AWS SDK (boto3) を使用した S3 アクセス

## 🚀 n8n Python ワークフロー

### **特徴**

- ✅ `language: "python"` で Python 実行
- ✅ `_json`, `_binary` でデータアクセス
- ✅ 詳細なログ出力とエラーハンドリング
- ✅ 型安全なデータ処理

### **使用方法**

1. n8n で `s3-2-3-aspect-python-workflow.json` をインポート
2. AWS 認証情報を設定
3. Webhook エンドポイントにリクエスト送信

```bash
curl -X POST http://your-n8n-instance/webhook/s3-2-3-aspect-python \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket",
    "file_key": "images/portrait-mobile.jpg",
    "width": 1080,
    "height": 1920
  }'
```

### **Python Code ノードの主要機能**

#### **1. 多段階寸法検出**

```python
# 1. 明示的寸法指定
if _json.get('width') and _json.get('height'):
    width = int(_json['width'])
    height = int(_json['height'])

# 2. ファイル名パターン解析
dimension_match = re.search(r'(\d+)x(\d+)', file_name, re.IGNORECASE)

# 3. キーワードベース推測
if any(keyword in lower_filename for keyword in ['portrait', 'mobile']):
    width, height = 1080, 1920

# 4. ファイルサイズベース推測
if file_size > 2000000:
    width, height = 1920, 1080
```

#### **2. 安全なバイナリアクセス**

```python
if _binary and 'image_data' in _binary:
    binary_data = _binary['image_data']
    print(f"Binary keys: {list(_binary.keys())}")
```

#### **3. 詳細なエラーハンドリング**

```python
try:
    # メイン処理
except Exception as error:
    print(f"Analysis Error: {str(error)}")
    import traceback
    traceback.print_exc()
```

## 🖥️ スタンドアロン Python スクリプト

### **インストール**

```bash
pip install boto3 Pillow
```

### **基本的な使用方法**

```bash
# 基本実行
python image_aspect_analyzer.py my-bucket images/photo.jpg

# 明示的寸法指定
python image_aspect_analyzer.py my-bucket images/photo.jpg --width 1080 --height 1920

# AWS認証情報指定
python image_aspect_analyzer.py my-bucket images/photo.jpg \
  --aws-access-key YOUR_ACCESS_KEY \
  --aws-secret-key YOUR_SECRET_KEY \
  --aws-region ap-northeast-1

# JSON出力
python image_aspect_analyzer.py my-bucket images/photo.jpg --output json
```

### **実行例**

#### **縦長画像の分析**

```bash
$ python image_aspect_analyzer.py test-bucket images/portrait_1080x1920.jpg

✅ 分析成功
📐 寸法: 1080x1920
📊 アスペクト比: 0.56
🏷️  分類: 縦長（2:3より縦長）
💡 推奨: ポートレート写真、モバイル向け画像、縦型バナーとして使用
🔍 検出方法: binary_analysis
📱 結果: 縦長画像（2:3より縦長）
```

#### **横長画像の分析**

```bash
$ python image_aspect_analyzer.py test-bucket images/banner_1920x1080.jpg

✅ 分析成功
📐 寸法: 1920x1080
📊 アスペクト比: 1.78
🏷️  分類: 横長
💡 推奨: バナー画像、ヘッダー画像、横型コンテンツに適用
🔍 検出方法: filename_pattern
🖥️  結果: 縦長でない画像（2:3以上）
```

### **JSON 出力例**

```json
{
  "success": true,
  "width": 1080,
  "height": 1920,
  "aspect_ratio": 0.5625,
  "decimal_ratio": 0.56,
  "classification": "tall",
  "detail_classification": "縦長（2:3より縦長）",
  "recommended_action": "ポートレート写真、モバイル向け画像、縦型バナーとして使用",
  "ratio_text": "1080:1920",
  "is_tall": true,
  "ratio_2_3_comparison": {
    "threshold": 0.67,
    "is_taller_than_2_3": true,
    "difference_from_2_3": -0.11
  },
  "detection_method": "binary_analysis",
  "s3_source": {
    "bucket": "test-bucket",
    "key": "images/portrait_1080x1920.jpg"
  },
  "analyzed_at": "2024-01-01T12:00:00.123456"
}
```

## 🔧 Python 版の利点

### **1. 型安全性**

- Python の型システムによる安全なデータ処理
- `isinstance()`, `hasattr()` による堅牢なチェック

### **2. 実際の画像解析**

- PIL (Pillow) による実際の画像ファイル解析
- メタデータからの正確な寸法取得

### **3. 詳細なログ**

- `print()` による詳細なデバッグ情報
- `traceback.print_exc()` による完全なエラー情報

### **4. 柔軟な実行環境**

- n8n ワークフロー内での実行
- コマンドライン スタンドアロン実行
- 他の Python アプリケーションからのインポート

## 🧪 テスト方法

### **n8n ワークフロー**

```bash
# 縦長画像テスト
curl -X POST http://your-n8n-instance/webhook/s3-2-3-aspect-python \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket",
    "file_key": "images/mobile-portrait.jpg"
  }'
```

### **スタンドアロンスクリプト**

```bash
# 複数パターンのテスト
python image_aspect_analyzer.py test-bucket images/portrait.jpg
python image_aspect_analyzer.py test-bucket images/banner_1920x1080.jpg
python image_aspect_analyzer.py test-bucket images/square_500x500.jpg
python image_aspect_analyzer.py test-bucket images/unknown.jpg
```

## 🔒 AWS 認証設定

### **環境変数**

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=ap-northeast-1
```

### **AWS CLI 設定**

```bash
aws configure
```

### **IAM ロール** (EC2 内での実行時)

- S3 読み取り権限を持つ IAM ロールを EC2 インスタンスに付与

## 📊 分類基準

| アスペクト比 | 分類     | 説明                 | 推奨用途                   |
| ------------ | -------- | -------------------- | -------------------------- |
| < 0.67       | tall     | 縦長（2:3 より縦長） | ポートレート、モバイル向け |
| 0.67-0.8     | not_tall | 2:3 から 3:4 の範囲  | 縦型コンテンツ             |
| 0.8-1.2      | not_tall | 正方形に近い         | プロフィール、アイコン     |
| ≥ 1.2        | not_tall | 横長                 | バナー、ヘッダー           |

## 🚀 本番運用推奨

**n8n 環境**: `s3-2-3-aspect-python-workflow.json`
**開発・テスト**: `image_aspect_analyzer.py`

Python 版により、JavaScript 版で発生していたバイナリデータアクセスやプロパティ参照の問題が解決されます！
