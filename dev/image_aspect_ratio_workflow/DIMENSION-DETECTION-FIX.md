# 画像寸法検出エラーの修正ガイド

## ❌ 発生していた問題

```json
{
  "image_analysis": {
    "error": "Could not determine image dimensions",
    "classification": "unknown"
  }
}
```

## 🔍 原因分析

### 1. **寸法検出ロジックの不備**

元のコードでは、以下の条件が揃わないと寸法を検出できませんでした：

```javascript
// 問題のあったロジック
if (item.json?.width && item.json?.height) {
  // 明示的な寸法指定のみ
} else if (item.json?.image_width && item.json?.image_height) {
  // 代替フィールド名のみ
} else {
  // ファイル名からの推測のみ（限定的）
}
```

### 2. **不十分なフォールバック**

- ファイル名にパターンがない場合の処理が不十分
- ファイルサイズからの推測ロジックが機能していない
- デフォルト値の設定がない

### 3. **デバッグ情報の不足**

- どの段階で失敗したかが不明
- 入力データの検証が不十分

## ✅ 修正内容

### 1. **Enhanced 版の改善点**

#### **多段階の寸法検出**

```javascript
// 1. 明示的な寸法指定（最優先）
if (item.json?.width && item.json?.height) {
  width = parseInt(item.json.width);
  height = parseInt(item.json.height);
}

// 2. ファイル名パターン解析
else if (fileName.match(/(\d+)x(\d+)/i)) {
  const match = fileName.match(/(\d+)x(\d+)/i);
  width = parseInt(match[1]);
  height = parseInt(match[2]);
}

// 3. キーワードベース推測
else if (fileName.includes("banner")) {
  width = 1920;
  height = 1080;
}

// 4. ファイルサイズベース推測
else if (fileSize > 2000000) {
  width = 1920;
  height = 1080;
}

// 5. デフォルト値（最後の手段）
else {
  width = 800;
  height = 600;
}
```

#### **詳細なログ出力**

```javascript
console.log("Processing item:", {
  bucketName,
  fileKey,
  hasWidth: !!item.json?.width,
  hasHeight: !!item.json?.height,
  hasBinary: !!(item.binary && item.binary.image_data),
});
```

#### **寸法の妥当性チェック**

```javascript
if (
  width &&
  height &&
  width > 0 &&
  height > 0 &&
  !isNaN(width) &&
  !isNaN(height)
) {
  // 有効な寸法として処理
} else {
  // エラー情報にデバッグ詳細を含める
  imageData = {
    error: `Could not determine valid image dimensions. Detected: width=${width}, height=${height}`,
    debug_info: {
      detected_width: width,
      detected_height: height,
      file_key: fileKey,
      has_explicit_width: !!item.json?.width,
      has_explicit_height: !!item.json?.height,
      file_size: binaryData?.fileSize || 0,
    },
  };
}
```

### 2. **Prepare S3 Parameters の改善**

寸法パラメータも明示的に準備：

```json
{
  "id": "width-param",
  "name": "width",
  "value": "={{ $json.width || $json.image_width || null }}",
  "type": "number"
},
{
  "id": "height-param",
  "name": "height",
  "value": "={{ $json.height || $json.image_height || null }}",
  "type": "number"
}
```

## 🧪 テスト方法

### 1. **明示的寸法指定**

```bash
curl -X POST http://your-n8n-instance/webhook/s3-2-3-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket",
    "file_key": "images/test.jpg",
    "width": 1080,
    "height": 1920
  }'
```

### 2. **ファイル名パターン**

```bash
curl -X POST http://your-n8n-instance/webhook/s3-2-3-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket",
    "file_key": "images/photo_1080x1920.jpg"
  }'
```

### 3. **キーワードベース**

```bash
curl -X POST http://your-n8n-instance/webhook/s3-2-3-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket",
    "file_key": "images/mobile-portrait.jpg"
  }'
```

### 4. **デフォルト値テスト**

```bash
curl -X POST http://your-n8n-instance/webhook/s3-2-3-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket",
    "file_key": "images/unknown.jpg"
  }'
```

## 📊 期待される出力

### **成功ケース**

```json
{
  "image_analysis": {
    "width": 1080,
    "height": 1920,
    "aspectRatio": 0.5625,
    "classification": "tall",
    "decimal_ratio": 0.56,
    "detection_method": "explicit",
    "ratio_2_3_comparison": {
      "threshold": 0.67,
      "is_taller_than_2_3": true,
      "difference_from_2_3": -0.11
    }
  }
}
```

### **デフォルト値使用ケース**

```json
{
  "image_analysis": {
    "width": 800,
    "height": 600,
    "aspectRatio": 1.33,
    "classification": "not_tall",
    "decimal_ratio": 1.33,
    "detection_method": "keyword_or_size"
  }
}
```

## 🔧 カスタマイズ可能な設定

### 1. **デフォルト寸法の変更**

```javascript
// デフォルト値を変更
else {
  width = 1024; height = 768; // 4:3
  // または
  width = 1920; height = 1080; // 16:9
}
```

### 2. **キーワードパターンの追加**

```javascript
else if (lowerFileName.includes('thumbnail') || lowerFileName.includes('thumb')) {
  width = 150; height = 150; // サムネイル
} else if (lowerFileName.includes('cover') || lowerFileName.includes('hero')) {
  width = 1920; height = 1080; // カバー画像
}
```

### 3. **ファイルサイズ閾値の調整**

```javascript
if (fileSize > 5000000) {
  // 5MB以上 → 4K
  width = 3840;
  height = 2160;
} else if (fileSize > 2000000) {
  // 2MB以上 → FHD
  width = 1920;
  height = 1080;
}
```

## 📝 使用推奨

1. **本番環境**: `s3-2-3-aspect-workflow-enhanced.json` を使用
2. **デバッグ**: n8n のログでコンソール出力を確認
3. **テスト**: 様々なパターンでテストケースを実行

この修正により、「Could not determine image dimensions」エラーは大幅に減少し、より堅牢な画像分析が可能になります！
