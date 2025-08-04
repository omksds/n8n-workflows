# Python 版 ファイルサイズエラー修正ガイド

## 🚨 **検出されたエラー**

### **コンソールログから特定されたエラー**

```
[Node: "S3 Image Analyzer (Python)"] Analysis Error: '>' not supported between instances of 'str' and 'int'
```

### **エラーの原因**

n8n の S3 ノードから取得される `fileSize` が文字列形式（例: `'1.06 MB'`）で返されるが、Python コードで数値比較を行おうとしてエラーが発生。

### **問題のあったコード**

```python
# 問題のあったコード
file_size = binary_data.get('fileSize', 0)  # '1.06 MB' が返される
if file_size > 2000000:  # TypeError: '>' not supported between instances of 'str' and 'int'
    width, height = 1920, 1080
```

## 🔧 **修正内容**

### **1. ファイルサイズパース関数の追加**

```python
def parse_file_size(size_str):
    """
    ファイルサイズ文字列を数値（バイト）に変換
    例: '1.06 MB' -> 1111490
    """
    if isinstance(size_str, (int, float)):
        return int(size_str)

    if not isinstance(size_str, str):
        return 0

    # '1.06 MB' のような文字列を数値に変換
    size_match = re.search(r'([\d.]+)\s*(MB|KB|B)', size_str, re.IGNORECASE)
    if size_match:
        size_value = float(size_match.group(1))
        size_unit = size_match.group(2).upper()
        if size_unit == 'MB':
            return int(size_value * 1024 * 1024)
        elif size_unit == 'KB':
            return int(size_value * 1024)
        else:  # B
            return int(size_value)

    # 数値のみの場合
    try:
        return int(float(size_str))
    except (ValueError, TypeError):
        return 0
```

### **2. 修正されたファイルサイズ処理**

```python
# 修正後のコード
raw_file_size = binary_data.get('fileSize', 0)
file_size_bytes = parse_file_size(raw_file_size)
print(f"Parsed file size: {file_size_bytes} bytes (from: {raw_file_size})")

if file_size_bytes > 2000000:  # 正常に数値比較が実行される
    width, height = 1920, 1080
    detection_method = 'filesize_large'
elif file_size_bytes > 1000000:
    width, height = 1024, 768
    detection_method = 'filesize_medium'
# ... 以下続く
```

### **3. デバッグ情報の強化**

```python
# デバッグログの追加
print(f"File size (raw): {raw_file_size}")
print(f"Parsed file size: {file_size_bytes} bytes (from: {raw_file_size})")

# 出力データにも raw と parsed の両方を含める
'file_size': file_size_for_output,
'file_size_raw': raw_file_size if 'raw_file_size' in locals() else 'unknown',
```

## 📁 **修正されたファイル**

### **1. `s3-2-3-aspect-python-workflow-fixed.json`**

- **Webhook パス**: `/webhook/s3-2-3-aspect-python-fixed`
- **修正内容**: `parse_file_size()` 関数を追加してファイルサイズ文字列を適切に処理
- **改善点**: より詳細なデバッグログとエラーハンドリング

### **2. `image_aspect_analyzer.py`**

- **修正内容**: スタンドアロンスクリプトにも同様の `parse_file_size()` メソッドを追加
- **改善点**: 型安全なファイルサイズ処理

## 🧪 **テスト方法**

### **修正版ワークフローのテスト**

```bash
curl -X POST http://your-n8n-instance/webhook/s3-2-3-aspect-python-fixed \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "tokushima-return",
    "file_key": "r7/BroadCast/map.png"
  }'
```

### **期待される成功ログ**

```
[Node: "S3 Image Analyzer (Python Fixed)"] Processing item: bucket=tokushima-return, file_key=r7/BroadCast/map.png
[Node: "S3 Image Analyzer (Python Fixed)"] File size (raw): 1.06 MB
[Node: "S3 Image Analyzer (Python Fixed)"] Parsed file size: 1111490 bytes (from: 1.06 MB)
[Node: "S3 Image Analyzer (Python Fixed)"] Using file size estimation, size: 1111490 bytes
[Node: "S3 Image Analyzer (Python Fixed)"] File size based estimation: 1024x768, file_size: 1111490 bytes
[Node: "S3 Image Analyzer (Python Fixed)"] Successfully analyzed image: 1024x768, aspect_ratio: 1.33, classification: not_tall
```

## 🔍 **サポートされるファイルサイズ形式**

| 入力形式    | 変換結果（バイト） | 例                 |
| ----------- | ------------------ | ------------------ |
| `"1.06 MB"` | `1,111,490`        | メガバイト         |
| `"512 KB"`  | `524,288`          | キロバイト         |
| `"1024 B"`  | `1,024`            | バイト             |
| `"2.5 mb"`  | `2,621,440`        | 大文字小文字無視   |
| `1048576`   | `1,048,576`        | 数値のまま         |
| `"invalid"` | `0`                | パースできない場合 |

## 🎯 **期待される出力**

### **成功時の `image_analysis` オブジェクト**

```json
{
  "width": 1024,
  "height": 768,
  "aspectRatio": 1.33,
  "classification": "not_tall",
  "detection_method": "filesize_medium",
  "file_size": 1111490,
  "file_size_raw": "1.06 MB",
  "mime_type": "image/png"
}
```

### **分類結果**

- **ファイルサイズ > 2MB**: `1920x1080` (横長、`not_tall`)
- **ファイルサイズ > 1MB**: `1024x768` (横長、`not_tall`) ← **今回のケース**
- **ファイルサイズ > 500KB**: `800x600` (横長、`not_tall`)
- **ファイルサイズ ≤ 500KB**: `500x500` (正方形、`not_tall`)

## 🚀 **推奨使用方法**

1. **新規実装**: `s3-2-3-aspect-python-workflow-fixed.json` を使用
2. **既存ワークフロー**: 該当部分のコードを修正版に置き換え
3. **スタンドアロン**: 修正済み `image_aspect_analyzer.py` を使用

この修正により、`'>' not supported between instances of 'str' and 'int'` エラーが完全に解決され、n8n の S3 ノードから返される様々なファイルサイズ形式に対応できるようになります！
