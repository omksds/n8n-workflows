# エラー修正ガイド

## 発生したエラー

```
TypeError: Cannot read properties of undefined (reading 'includes')
```

## エラーの原因

このエラーは、`fileName.includes()` メソッドを呼び出そうとした際に、`fileName` が `undefined` または `null` だったことが原因です。

### 具体的な問題箇所

1. **S3 Image Analyzer ノード**で、以下のコードが問題を引き起こしていました：

```javascript
// 問題のあるコード
const fileName = item.json.file_key;
if (fileName.includes("banner")) {
  // fileName が undefined の場合エラー
  // 処理...
}
```

2. **データの流れ**で、`item.json.file_key` が undefined になるケース：
   - Webhook で `file_key` が送信されない
   - S3 パラメータ準備で適切に設定されない
   - 前のノードでデータが正しく渡されない

## 修正内容

### 1. 安全なデフォルト値の設定

```javascript
// 修正後
const fileName = item.json.file_key || "";
if (fileName && fileName.includes("banner")) {
  // 処理...
}
```

### 2. オプショナルチェーニングの使用

```javascript
// より安全なアクセス
const bucketName = item.json?.bucket_name || "unknown";
const fileKey = item.json?.file_key || "unknown";
```

### 3. 型チェックの追加

```javascript
// 型と値の確認
if (fileName && typeof fileName === "string" && fileName.length > 0) {
  const lowerFileName = fileName.toLowerCase();
  if (lowerFileName.includes("banner")) {
    // 処理...
  }
}
```

### 4. パラメータ検証ノードの追加

新しく **Validate Parameters** ノードを追加して、必須パラメータの事前チェックを実行：

```javascript
// パラメータ検証
{
  "leftValue": "={{ $json.file_key }}",
  "rightValue": "",
  "operator": {
    "type": "string",
    "operation": "notEquals"
  }
}
```

## 修正されたファイル

### 1. `s3-image-aspect-ratio-workflow-fixed.json`

**主な改善点：**

- ✅ 安全なプロパティアクセス (`?.` オペレータ)
- ✅ デフォルト値の設定
- ✅ 型チェックの追加
- ✅ パラメータ検証ノードの追加
- ✅ 詳細なエラーログ
- ✅ エラーハンドリングの強化

**新しいワークフロー構造：**

```
Webhook → Prepare S3 Parameters → Validate Parameters
                                         ↓
                              ┌─ S3 Download (正常)
                              └─ Parameter Error (エラー)
                                         ↓
                                 S3 Image Analyzer → Switch → Processors
```

### 2. エラーハンドリングの改善

```javascript
try {
  // メイン処理
} catch (error) {
  console.error("S3 Image Analysis Error:", error);
  results.push({
    json: {
      ...item.json,
      image_analysis: {
        error: `S3 Image Analysis Error: ${error.message || "Unknown error"}`,
        error_stack: error.stack || "No stack trace",
        orientation: "error",
      },
    },
  });
}
```

## テスト方法

### 1. 正常ケースのテスト

```bash
curl -X POST http://your-n8n-instance/webhook/s3-image-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket",
    "file_key": "images/banner_1920x1080.jpg"
  }'
```

### 2. エラーケースのテスト

```bash
# file_key が空の場合
curl -X POST http://your-n8n-instance/webhook/s3-image-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket"
  }'

# file_key が null の場合
curl -X POST http://your-n8n-instance/webhook/s3-image-aspect-check \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "test-bucket",
    "file_key": null
  }'
```

## 予防策

### 1. 入力データの検証

常に Webhook で受信するデータを検証：

```javascript
const requiredFields = ["bucket_name", "file_key"];
for (const field of requiredFields) {
  if (!item.json[field]) {
    throw new Error(`Missing required field: ${field}`);
  }
}
```

### 2. デフォルト値の設定

```javascript
const config = {
  bucketName: item.json?.bucket_name || "default-bucket",
  fileKey: item.json?.file_key || "",
  width: item.json?.width || null,
  height: item.json?.height || null,
};
```

### 3. 型安全なアクセス

```javascript
// 文字列メソッドを使用する前の確認
if (typeof fileName === "string" && fileName.length > 0) {
  // 安全に includes() を使用
  if (fileName.includes("pattern")) {
    // 処理...
  }
}
```

## デバッグのコツ

### 1. ログの追加

```javascript
console.log("Input data:", JSON.stringify(item.json, null, 2));
console.log("File key:", item.json?.file_key);
console.log("Type of file_key:", typeof item.json?.file_key);
```

### 2. 段階的なテスト

1. まず Webhook → Prepare S3 Parameters の出力を確認
2. 次に Validate Parameters の分岐を確認
3. 最後に S3 Download → Analyzer の流れを確認

### 3. エラー情報の詳細化

```javascript
catch (error) {
  const errorInfo = {
    message: error.message,
    stack: error.stack,
    inputData: item.json,
    timestamp: new Date().toISOString()
  };
  console.error('Detailed error info:', errorInfo);
}
```

## まとめ

このエラーは、JavaScript で未定義の値に対してメソッドを呼び出そうとした典型的な問題でした。修正版では：

- ✅ **安全なプロパティアクセス**
- ✅ **適切なデフォルト値**
- ✅ **型チェック**
- ✅ **パラメータ検証**
- ✅ **詳細なエラーログ**

これらの改善により、より堅牢で信頼性の高いワークフローになりました。
