#!/usr/bin/env python3
"""
画像アスペクト比検出スクリプト
S3から画像を取得してアスペクト比を分析し、2:3を基準に分類する
"""

import json
import re
import math
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import boto3
from PIL import Image
import io
import argparse


class ImageAspectAnalyzer:
    """画像アスペクト比分析クラス"""
    
    def __init__(self, aws_access_key: str = None, aws_secret_key: str = None, aws_region: str = 'ap-northeast-1'):
        """
        初期化
        
        Args:
            aws_access_key: AWS Access Key ID
            aws_secret_key: AWS Secret Access Key  
            aws_region: AWS Region
        """
        self.threshold_2_3 = 2/3  # 0.6667
        
        # S3クライアントの初期化
        if aws_access_key and aws_secret_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
        else:
            # 環境変数またはIAMロールから認証情報を取得
            self.s3_client = boto3.client('s3', region_name=aws_region)
    
    def download_image_from_s3(self, bucket_name: str, file_key: str) -> Optional[bytes]:
        """
        S3から画像をダウンロード
        
        Args:
            bucket_name: S3バケット名
            file_key: S3オブジェクトキー
            
        Returns:
            画像のバイナリデータ、失敗時はNone
        """
        try:
            print(f"Downloading image from S3: s3://{bucket_name}/{file_key}")
            response = self.s3_client.get_object(Bucket=bucket_name, Key=file_key)
            return response['Body'].read()
        except Exception as e:
            print(f"Error downloading from S3: {str(e)}")
            return None
    
    def get_image_dimensions_from_binary(self, image_data: bytes) -> Optional[Tuple[int, int]]:
        """
        バイナリデータから画像の寸法を取得
        
        Args:
            image_data: 画像のバイナリデータ
            
        Returns:
            (width, height) のタプル、失敗時はNone
        """
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                width, height = img.size
                print(f"Detected image dimensions from binary data: {width}x{height}")
                return width, height
        except Exception as e:
            print(f"Error getting dimensions from binary data: {str(e)}")
            return None
    
    def detect_dimensions_from_filename(self, filename: str) -> Optional[Tuple[int, int]]:
        """
        ファイル名から寸法を推測
        
        Args:
            filename: ファイル名
            
        Returns:
            (width, height) のタプル、推測できない場合はNone
        """
        if not filename:
            return None
        
        # パターン1: 1920x1080 形式
        dimension_match = re.search(r'(\d+)x(\d+)', filename, re.IGNORECASE)
        if dimension_match:
            width = int(dimension_match.group(1))
            height = int(dimension_match.group(2))
            print(f"Found dimensions in filename: {width}x{height}")
            return width, height
        
        # パターン2: キーワードベースの推測
        lower_filename = filename.lower()
        print(f"Using keyword-based detection for: {lower_filename}")
        
        if any(keyword in lower_filename for keyword in ['banner', 'header', 'landscape', 'wide']):
            width, height = 1920, 1080  # 横長デフォルト
            print(f"Detected wide image keyword, using: {width}x{height}")
            return width, height
        elif any(keyword in lower_filename for keyword in ['portrait', 'mobile', 'vertical', 'tall']):
            width, height = 1080, 1920  # 縦長デフォルト
            print(f"Detected tall image keyword, using: {width}x{height}")
            return width, height
        elif any(keyword in lower_filename for keyword in ['square', 'icon', 'profile', 'avatar']):
            width, height = 500, 500  # 正方形デフォルト
            print(f"Detected square image keyword, using: {width}x{height}")
            return width, height
        
        return None
    
    def parse_file_size(self, size_input) -> int:
        """
        ファイルサイズ文字列を数値（バイト）に変換
        
        Args:
            size_input: ファイルサイズ（文字列、数値）
            
        Returns:
            ファイルサイズ（バイト）
        """
        if isinstance(size_input, (int, float)):
            return int(size_input)
        
        if not isinstance(size_input, str):
            return 0
        
        # '1.06 MB' のような文字列を数値に変換
        size_match = re.search(r'([\d.]+)\s*(MB|KB|B)', size_input, re.IGNORECASE)
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
            return int(float(size_input))
        except (ValueError, TypeError):
            return 0

    def detect_dimensions_from_filesize(self, file_size: int) -> Tuple[int, int]:
        """
        ファイルサイズから寸法を推測
        
        Args:
            file_size: ファイルサイズ（バイト）
            
        Returns:
            (width, height) のタプル
        """
        print(f"Using file size estimation, size: {file_size}")
        
        if file_size > 2000000:  # 2MB以上 → 高解像度横長
            width, height = 1920, 1080
        elif file_size > 1000000:  # 1MB以上 → 中解像度
            width, height = 1024, 768
        elif file_size > 500000:  # 500KB以上 → 標準解像度
            width, height = 800, 600
        else:  # 小さいファイル → 正方形と仮定
            width, height = 500, 500
        
        print(f"File size based estimation: {width}x{height}")
        return width, height
    
    def classify_aspect_ratio(self, aspect_ratio: float) -> str:
        """
        アスペクト比を分類
        
        Args:
            aspect_ratio: アスペクト比
            
        Returns:
            分類結果 ('tall' または 'not_tall')
        """
        if aspect_ratio < self.threshold_2_3:
            return 'tall'  # 縦長（2:3より縦長）
        else:
            return 'not_tall'  # 縦長でない（2:3以上の比率）
    
    def get_detailed_classification(self, aspect_ratio: float) -> Tuple[str, str]:
        """
        詳細な分類と推奨アクションを取得
        
        Args:
            aspect_ratio: アスペクト比
            
        Returns:
            (詳細分類, 推奨アクション) のタプル
        """
        if aspect_ratio < 0.67:
            return ('縦長（2:3より縦長）', 'ポートレート写真、モバイル向け画像、縦型バナーとして使用')
        elif 0.67 <= aspect_ratio < 0.8:
            return ('2:3から3:4の範囲', 'ポートレート写真や縦型コンテンツに適用')
        elif 0.8 <= aspect_ratio < 1.2:
            return ('正方形に近い', 'プロフィール画像、アイコン、正方形コンテンツに適用')
        else:
            return ('横長', 'バナー画像、ヘッダー画像、横型コンテンツに適用')
    
    def analyze_image(self, bucket_name: str, file_key: str, 
                     explicit_width: int = None, explicit_height: int = None) -> Dict[str, Any]:
        """
        画像を分析してアスペクト比と分類を返す
        
        Args:
            bucket_name: S3バケット名
            file_key: S3オブジェクトキー
            explicit_width: 明示的に指定された幅
            explicit_height: 明示的に指定された高さ
            
        Returns:
            分析結果の辞書
        """
        try:
            print(f"Analyzing image: s3://{bucket_name}/{file_key}")
            
            width = None
            height = None
            detection_method = 'unknown'
            
            # 1. 明示的な寸法指定を優先
            if explicit_width and explicit_height:
                width = int(explicit_width)
                height = int(explicit_height)
                detection_method = 'explicit'
                print(f"Using explicit dimensions: {width}x{height}")
            else:
                # 2. S3から画像をダウンロードして実際の寸法を取得
                image_data = self.download_image_from_s3(bucket_name, file_key)
                if image_data:
                    dimensions = self.get_image_dimensions_from_binary(image_data)
                    if dimensions:
                        width, height = dimensions
                        detection_method = 'binary_analysis'
                    else:
                        # 3. ファイル名から推測
                        dimensions = self.detect_dimensions_from_filename(file_key)
                        if dimensions:
                            width, height = dimensions
                            detection_method = 'filename_pattern'
                        else:
                            # 4. ファイルサイズから推測
                            file_size = len(image_data)
                            width, height = self.detect_dimensions_from_filesize(file_size)
                            detection_method = 'filesize_estimation'
                else:
                    # S3からのダウンロードに失敗した場合
                    dimensions = self.detect_dimensions_from_filename(file_key)
                    if dimensions:
                        width, height = dimensions
                        detection_method = 'filename_pattern'
                    else:
                        # デフォルト値
                        width, height = 800, 600
                        detection_method = 'default'
                        print(f"Using default dimensions: {width}x{height}")
            
            # 寸法の妥当性チェック
            if width and height and width > 0 and height > 0:
                aspect_ratio = width / height
                classification = self.classify_aspect_ratio(aspect_ratio)
                detail_classification, recommendation = self.get_detailed_classification(aspect_ratio)
                
                result = {
                    'success': True,
                    'width': width,
                    'height': height,
                    'aspect_ratio': aspect_ratio,
                    'decimal_ratio': round(aspect_ratio, 2),
                    'classification': classification,
                    'detail_classification': detail_classification,
                    'recommended_action': recommendation,
                    'ratio_text': f"{width}:{height}",
                    'is_tall': aspect_ratio < self.threshold_2_3,
                    'ratio_2_3_comparison': {
                        'threshold': round(self.threshold_2_3, 2),
                        'is_taller_than_2_3': aspect_ratio < self.threshold_2_3,
                        'difference_from_2_3': round(aspect_ratio - self.threshold_2_3, 2)
                    },
                    'detection_method': detection_method,
                    's3_source': {
                        'bucket': bucket_name,
                        'key': file_key
                    },
                    'analyzed_at': datetime.now().isoformat()
                }
                
                print(f"Analysis successful: {width}x{height}, aspect_ratio: {aspect_ratio:.2f}, classification: {classification}")
                return result
            else:
                return {
                    'success': False,
                    'error': f'Invalid dimensions detected: width={width}, height={height}',
                    'classification': 'unknown',
                    'debug_info': {
                        'detected_width': width,
                        'detected_height': height,
                        'detection_method': detection_method
                    },
                    's3_source': {
                        'bucket': bucket_name,
                        'key': file_key
                    },
                    'analyzed_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"Analysis error: {str(e)}")
            return {
                'success': False,
                'error': f'Analysis error: {str(e)}',
                'error_type': type(e).__name__,
                'classification': 'error',
                's3_source': {
                    'bucket': bucket_name,
                    'key': file_key
                },
                'analyzed_at': datetime.now().isoformat()
            }


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='画像アスペクト比分析ツール')
    parser.add_argument('bucket', help='S3バケット名')
    parser.add_argument('key', help='S3オブジェクトキー')
    parser.add_argument('--width', type=int, help='明示的な幅指定')
    parser.add_argument('--height', type=int, help='明示的な高さ指定')
    parser.add_argument('--aws-access-key', help='AWS Access Key ID')
    parser.add_argument('--aws-secret-key', help='AWS Secret Access Key')
    parser.add_argument('--aws-region', default='ap-northeast-1', help='AWS Region')
    parser.add_argument('--output', choices=['json', 'human'], default='human', help='出力形式')
    
    args = parser.parse_args()
    
    try:
        # アナライザーの初期化
        analyzer = ImageAspectAnalyzer(
            aws_access_key=args.aws_access_key,
            aws_secret_key=args.aws_secret_key,
            aws_region=args.aws_region
        )
        
        # 画像分析実行
        result = analyzer.analyze_image(
            bucket_name=args.bucket,
            file_key=args.key,
            explicit_width=args.width,
            explicit_height=args.height
        )
        
        # 結果出力
        if args.output == 'json':
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # 人間が読みやすい形式
            if result['success']:
                print(f"✅ 分析成功")
                print(f"📐 寸法: {result['width']}x{result['height']}")
                print(f"📊 アスペクト比: {result['decimal_ratio']}")
                print(f"🏷️  分類: {result['detail_classification']}")
                print(f"💡 推奨: {result['recommended_action']}")
                print(f"🔍 検出方法: {result['detection_method']}")
                
                if result['classification'] == 'tall':
                    print(f"📱 結果: 縦長画像（2:3より縦長）")
                else:
                    print(f"🖥️  結果: 縦長でない画像（2:3以上）")
            else:
                print(f"❌ 分析失敗: {result['error']}")
                
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()