# 🏥 カルテ解析ツール（psych-doc-ai）

精神科カルテPDFをAIで自動解析し、患者情報・現病歴・既往歴・検査結果・処方を構造化するツールです。

## 概要

電子カルテのPDFをアップロードするだけで、AIが自動的に以下の情報を抽出します。

- 患者基本情報（氏名・主訴）
- 現在治療中の疾患（現病歴）
- 過去に治療した疾患（既往歴）
- 検査項目一覧
- 処方薬（指定日数以内のみ表示）

## 特徴

- **完全ローカル動作**：患者データは外部サーバーに送信されません
- **GPU対応**：NVIDIA GPUを使った高速処理（複数GPU対応）
- **WebUI**：Streamlitによるブラウザベースの使いやすいUI
- **複数フォーマット出力**：CSV・TXT・PDFでダウンロード可能

## 技術スタック

| 技術 | 用途 |
|------|------|
| Python | メイン言語 |
| Streamlit | WebUI |
| Ollama | ローカルLLM実行 |
| Docling | PDF解析 |
| ReportLab | PDF出力 |

## 動作環境

- Windows PC
- NVIDIA GPU（推奨：VRAM 8GB以上）
- Python 3.10以上

## セットアップ

### 1. Pythonのインストール
[python.org](https://www.python.org/downloads/) からダウンロードしてインストール。
インストール時に「Add Python to PATH」に必ずチェックを入れる。

### 2. Ollamaのインストール
[ollama.com](https://ollama.com/download) からダウンロードしてインストール。

### 3. ライブラリのインストール
```bash
python -m pip install streamlit docling reportlab ollama
```

### 4. AIモデルのダウンロード
```bash
ollama pull gpt-oss:20b
```
※約13GBあるためダウンロードに時間がかかります

### 5. 起動
`起動.bat`をダブルクリックするとブラウザが自動で開きます。

## 使い方

1. `起動.bat`をダブルクリック
2. ブラウザが開いたらPDFをアップロード
3. サイドバーで処方対象日数を設定
4. 「解析開始」をクリック
5. 結果を確認してCSV・TXT・PDFでダウンロード

## ディレクトリ構成
```
psych-doc-ai/
├── app.py          # Streamlit WebUI
├── main.py         # PDF抽出・処方フィルター
├── llm_client.py   # AI解析クライアント
├── 起動.bat        # 起動用バッチファイル
└── README.md       # このファイル
```

## 注意事項

- 患者情報を含むPDFはこのPC内のみで処理されます
- 外部サーバーには一切送信されません
- 本ツールはAIによる補助ツールです。最終判断は必ず医師が行ってください
- PCを再起動するとOllamaが停止します（起動.batで再起動してください）