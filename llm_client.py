import ollama
import json
import re


class OllamaClient:
    def __init__(self, model_name="gpt-oss:20b"):
        self.model_name = model_name

    def get_medical_data(self, medical_text):
        try:
            # Step 1: 構造理解（フォーマット非依存）
            forced_japanese = """以下の医療文書を分析し、下記6項目を日本語で簡潔に出力せよ。余計な説明不要。

1. 患者情報（氏名・生年月日・性別）
2. 主訴（S)やS:の記載のみ。なければ「記載なし」）
3. 現在治療中の疾患（終了日なし）
4. 過去に治療した疾患（終了日あり）
5. 検査項目（全て列挙）
6. 処方（処方日：薬剤名 用量 用法 日数）

"""
            response1 = ollama.generate(
                model=self.model_name,
                prompt=forced_japanese + medical_text,
                system="あなたは日本語のみで回答する医療専門家です。",
                 options={
                    "temperature": 0,
                    "num_ctx": 32768,
                    "num_predict": 6000,
                },
            )
            structured_text = response1.response or response1.thinking or ""

            # Step 2: JSON抽出（整理済みテキストから）
            step2_prompt = """
以下の整理済み医療情報からJSONのみを出力しなさい。
present_illnessには「現在治療中の疾患」のみ入れること。
past_historyには「過去に治療した疾患」のみ入れること。
chief_complaintには患者が自分の言葉で述べた症状のみ入れること。「精神科通院」「受診」などの行動は主訴ではない。該当する記載がなければ「記載なし」とすること。
絶対に混在させないこと。

{
    "patient_name": "患者氏名",
    "chief_complaint": "患者が述べた症状のみ。なければ記載なし",
    "present_illness": "現在治療中の疾患のみ",
    "past_history": "過去に治療した疾患のみ",
    "test_results": "検査結果",
    "prescription": "処方日・薬剤名・用量・用法・日数を全て列挙。省略禁止。""
}
"""
            response2 = ollama.generate(
                model=self.model_name,
                prompt=structured_text,
                system=step2_prompt,
                format="json",
                options={"temperature": 0, "num_ctx": 32768, "num_predict": 2000, "think": False},
            )
            raw_res = response2.response or response2.thinking or ""

            raw_res = re.sub(r"<think>.*?</think>", "", raw_res, flags=re.DOTALL).strip()

            if not raw_res.endswith("}"):
                raw_res = raw_res + '"}'

            try:
                return json.loads(raw_res)
            except json.JSONDecodeError:
                return {"error": "JSONパース失敗", "raw": raw_res[:500]}

        except Exception as e:
            print(f"エラー発生: {e}")
            return {"error": str(e)}