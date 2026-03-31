import os
from docling.document_converter import DocumentConverter
from llm_client import OllamaClient
import json
from datetime import datetime
import re

PRESCRIPTION_ACTIVE_DAYS = 710  # この日数以内の処方のみ表示


def extract_text_from_pdf(pdf_path):
    """PDFからMarkdown形式でテキストを抽出する。"""
    print(f"--- Step 1: PDF解析を開始します（CPU） ---")
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False  # OCRをオフ

    converter = DocumentConverter(
        format_options={
            "pdf": PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    result = converter.convert(pdf_path)
    return result.document.export_to_markdown()

def filter_prescriptions(prescription_data, active_days=30):
    """直近active_days日以内に処方された薬剤のみ返す"""
    today = datetime.now()
    result = {}

    def clean_content(content):
        return re.sub(r'\s*\d+\s*日分', '', content).strip()

    # 辞書形式の場合
    if isinstance(prescription_data, dict):
        for content, period in prescription_data.items():
            dates = re.findall(r'\d{4}/\d{2}/\d{2}', period)
            if not dates:
                continue
            last_date = datetime.strptime(dates[-1], "%Y/%m/%d")
            if (today - last_date).days <= active_days:
                result[clean_content(content)] = True

    # 文字列形式の場合
    elif isinstance(prescription_data, str):
        # 「日付: 内容」のパターンを全て抽出
        pattern = r'(\d{4}/\d{2}/\d{2}):\s*(.*?)(?=、\d{4}/\d{2}/\d{2}:|$)'
        for match in re.finditer(pattern, prescription_data, re.DOTALL):
            date_str = match.group(1).strip()
            content = match.group(2).strip()
            date = datetime.strptime(date_str, "%Y/%m/%d")
            cleaned = clean_content(content)
            if (today - date).days <= active_days:
                result[cleaned] = True

    else:
        return prescription_data
   
    return list(result.keys())


def main():
    pdf_path = "sample.pdf"
    if not os.path.exists(pdf_path):
        print(f"エラー：{pdf_path} が見つからないわ。ファイル名を確認して。")
        return

    full_text = extract_text_from_pdf(pdf_path)
    print(f"DEBUG: 抽出完了（全 {len(full_text)} 文字）")

    print(f"--- Step 2: AI（GPU）に全文渡して解析を開始 ---")
    input_text = full_text

    client = OllamaClient(model_name="qwen3.5")
    extracted_data = client.get_medical_data(input_text)

    if "prescription" in extracted_data and "error" not in extracted_data:
        print(f"DEBUG: 処方の生データ: {extracted_data['prescription']}")
        extracted_data["prescription"] = filter_prescriptions(
            extracted_data["prescription"],
            active_days=PRESCRIPTION_ACTIVE_DAYS,
        )

    KEY_MAP = {
        "patient_name": "患者名",
        "chief_complaint": "主訴",
        "present_illness": "現病歴",
        "past_history": "既往歴",
        "test_results": "検査結果",
        "prescription": "処方",
    }
    japanese_result = {KEY_MAP.get(k, k): v for k, v in extracted_data.items()}

    print("\n--- 解析結果（JSON） ---")
    print(json.dumps(japanese_result, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()