import streamlit as st
import json
import csv
import io
import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from llm_client import OllamaClient
from main import extract_text_from_pdf, filter_prescriptions

st.set_page_config(
    page_title="カルテ解析ツール",
    page_icon="🏥",
    layout="wide"
)

# カスタムCSS
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1a5276;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #2e86c1;
        margin-bottom: 2rem;
    }
    .subtitle {
        font-size: 1rem;
        color: #7f8c8d;
        text-align: center;
        margin-top: -1.5rem;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1a5276;
        border-left: 4px solid #2e86c1;
        padding-left: 0.5rem;
        margin: 1rem 0 0.5rem 0;
    }
    .result-table {
        width: 100%;
        border-collapse: collapse;
    }
    .result-table th {
        background-color: #2e86c1;
        color: white;
        padding: 8px 12px;
        text-align: left;
        font-weight: 600;
    }
    .result-table td {
        padding: 8px 12px;
        border-bottom: 1px solid #d5d8dc;
        vertical-align: top;
    }
    .result-table tr:nth-child(even) {
        background-color: #f2f3f4;
    }
    .stButton > button {
        background-color: #2e86c1;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        width: 100%;
    }
    .download-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# タイトル
st.markdown('<div class="main-title">🏥 カルテ解析ツール</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">PDFカルテをアップロードして自動解析</div>', unsafe_allow_html=True)

KEY_MAP = {
    "patient_name": "患者名",
    "chief_complaint": "主訴",
    "present_illness": "現病歴",
    "past_history": "既往歴",
    "test_results": "検査結果",
    "prescription": "処方",
}

if "all_results" not in st.session_state:
    st.session_state.all_results = []

# サイドバー
with st.sidebar:
    st.markdown("### ⚙️ 設定")
    st.divider()
    active_days = st.number_input(
        "処方対象日数",
        min_value=1,
        max_value=9999,
        value=30,
        help="この日数以内の処方のみ表示します"
    )
    st.divider()
    st.markdown("### 📋 使い方")
    st.markdown("""
    1. PDFをアップロード
    2. 「解析開始」をクリック
    3. 結果を確認・ダウンロード
    """)
    st.divider()
    st.markdown("### ℹ️ 注意事項")
    st.caption("患者データはこのPC内のみで処理されます。外部には送信されません。")

# メインエリア
uploaded_files = st.file_uploader(
    "📂 PDFファイルをアップロード",
    type="pdf",
    accept_multiple_files=True,
    help="複数ファイルの同時アップロード可能"
)

if uploaded_files:
    st.info(f"{len(uploaded_files)}件のファイルが選択されています")

col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    analyze_button = st.button("🔍 解析開始", type="primary", disabled=not uploaded_files)

if analyze_button and uploaded_files:
    st.session_state.all_results = []

    for uploaded_file in uploaded_files:
        with st.spinner(f"解析中: {uploaded_file.name}"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            try:
                full_text = extract_text_from_pdf(tmp_path)
                client = OllamaClient(model_name="qwen3.5")
                extracted_data = client.get_medical_data(full_text)

                if "prescription" in extracted_data and "error" not in extracted_data:
                    extracted_data["prescription"] = filter_prescriptions(
                        extracted_data["prescription"],
                        active_days=active_days,
                    )

                japanese_result = {KEY_MAP.get(k, k): v for k, v in extracted_data.items()}
                japanese_result["ファイル名"] = uploaded_file.name
                st.session_state.all_results.append(japanese_result)

            finally:
                os.unlink(tmp_path)

    st.success("解析完了！")

# 結果表示
if st.session_state.all_results:
    for japanese_result in st.session_state.all_results:
        st.markdown(f'<div class="section-header">📄 {japanese_result.get("ファイル名", "")}</div>', unsafe_allow_html=True)

        # 基本情報
        st.markdown(f"**患者名：** {japanese_result.get('患者名', '不明')}")
        st.markdown(f"**主訴：** {japanese_result.get('主訴', '記載なし')}")

        
        # 表形式で表示
        table_data = {
            "項目": ["現病歴", "既往歴", "検査結果"],
            "内容": [
                japanese_result.get("現病歴", ""),
                japanese_result.get("既往歴", ""),
                japanese_result.get("検査結果", ""),
            ]
        }

        html_table = '<table class="result-table"><tr><th>項目</th><th>内容</th></tr>'
        for item, content in zip(table_data["項目"], table_data["内容"]):
            if isinstance(content, str):
                items = content.split("、")
                if len(items) > 1:
                    content_html = "<br>・".join([""] + items)
                else:
                    content_html = content
            else:
                content_html = content
            html_table += f'<tr><td><strong>{item}</strong></td><td>{content_html}</td></tr>'

        # 処方
        prescription = japanese_result.get("処方", [])
        if isinstance(prescription, list) and prescription:
            prescription_html = "<br>・".join([""] + prescription)
        else:
            prescription_html = str(prescription)
        html_table += f'<tr><td><strong>処方</strong></td><td>{prescription_html}</td></tr>'
        html_table += '</table>'

        st.markdown(html_table, unsafe_allow_html=True)
        st.divider()

    # ダウンロード
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.markdown("### 💾 ダウンロード")
    all_results = st.session_state.all_results

    col1, col2, col3 = st.columns(3)

    # CSV
    with col1:
        flat_results = []
        for r in all_results:
            flat = {}
            for k, v in r.items():
                flat[k] = "、".join(v) if isinstance(v, list) else v
            flat_results.append(flat)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=flat_results[0].keys())
        writer.writeheader()
        writer.writerows(flat_results)

        st.download_button(
            label="📊 CSVダウンロード",
            data=output.getvalue().encode("utf-8-sig"),
            file_name=f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    # TXT
    with col2:
        txt_lines = []
        for r in all_results:
            txt_lines.append(f"【ファイル名】{r.get('ファイル名', '')}")
            txt_lines.append("")
            for k, v in r.items():
                if k == "ファイル名":
                    continue
                txt_lines.append(f"【{k}】")
                if isinstance(v, list):
                    for item in v:
                        txt_lines.append(f"  ・{item}")
                else:
                    items = str(v).split("、")
                    if len(items) > 1:
                        for item in items:
                            txt_lines.append(f"  ・{item.strip()}")
                    else:
                        txt_lines.append(f"  {v}")
                txt_lines.append("")
            txt_lines.append("=" * 40)
            txt_lines.append("")

        st.download_button(
            label="📝 TXTダウンロード",
            data="\n".join(txt_lines).encode("utf-8"),
            file_name=f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )

    # PDF
    with col3:
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
        c.setFont("HeiseiKakuGo-W5", 10)

        width, height = A4
        y_pos = [height - 50]

        def add_line(text, indent=0):
            if y_pos[0] < 50:
                c.showPage()
                c.setFont("HeiseiKakuGo-W5", 10)
                y_pos[0] = height - 50
            c.drawString(50 + indent, y_pos[0], text)
            y_pos[0] -= 18

        for r in all_results:
            add_line(f"【ファイル名】{r.get('ファイル名', '')}")
            add_line("")
            for k, v in r.items():
                if k == "ファイル名":
                    continue
                add_line(f"【{k}】")
                if isinstance(v, list):
                    for item in v:
                        add_line(f"・{item}", indent=20)
                else:
                    items = str(v).split("、")
                    if len(items) > 1:
                        for item in items:
                            add_line(f"・{item.strip()}", indent=20)
                    else:
                        add_line(str(v), indent=20)
                add_line("")
            add_line("=" * 30)
            add_line("")

        c.save()
        pdf_buffer.seek(0)

        st.download_button(
            label="📄 PDFダウンロード",
            data=pdf_buffer,
            file_name=f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf"
        )
    st.markdown('</div>', unsafe_allow_html=True)