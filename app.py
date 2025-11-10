from flask import Flask, render_template, request, jsonify
import requests
import graphviz
import re
import time
from config import GOOGLE_GEMINI_API_KEY

app = Flask(__name__)

# === API URL của Gemini === (giữ nguyên model cũ)
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.0-flash:generateContent?key={GOOGLE_GEMINI_API_KEY}"
)


# ======== HÀM PHỤ TRỢ ========

def extract_graphviz_code(ai_response):
    """Tách mã Graphviz DOT từ phản hồi của AI (trong khối ```dot ... ```)."""
    match = re.search(r"```dot\n(.*?)\n```", ai_response, re.DOTALL)
    return match.group(1).strip() if match else ai_response.strip()


def send_to_gemini(filename, code):
    """Gửi mã nguồn của 1 file lên Gemini để sinh Graphviz DOT code."""
    headers = {"Content-Type": "application/json"}
    prompt = (
        f"Convert the following {filename} code into a Graphviz DOT format diagram. "
        "Output only valid Graphviz DOT code fenced in ```dot```.\n\n"
        f"{code}"
    )
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}

    max_retries = 5
    attempt = 0

    while attempt < max_retries:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)

        # ✅ Thành công
        if response.status_code == 200:
            try:
                ai_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                dot_code = extract_graphviz_code(ai_text)
                return dot_code, None
            except Exception as e:
                return None, f"Error parsing AI response: {e}"

        # ⚠️ Nếu bị giới hạn 429 (quota)
        elif response.status_code == 429:
            try:
                data = response.json()
                details = data["error"].get("details", [])
                retry_after = 40  # mặc định nếu không đọc được thời gian chờ
                for d in details:
                    if "@type" in d and "RetryInfo" in d["@type"]:
                        delay_str = d.get("retryDelay", "40s")
                        retry_after = int(re.search(r"\d+", delay_str).group(0))
                print(f"[Rate limit] Waiting {retry_after}s before retrying {filename}...")
                time.sleep(retry_after)
            except Exception:
                print("[Rate limit] Waiting 40s (default)...")
                time.sleep(40)
            attempt += 1
            continue

        # ❌ Lỗi khác
        else:
            return None, f"Error {response.status_code}: {response.text}"

    return None, "Max retries reached after repeated 429 errors."


def merge_dot_graphs(dot_list):
    """Hợp nhất nhiều Graphviz DOT code thành 1 biểu đồ lớn."""
    merged = ["digraph G {"]
    for dot in dot_list:
        inner = re.search(r"\{(.*)\}", dot, re.DOTALL)
        if inner:
            merged.append(inner.group(1).strip())
    merged.append("}")
    return "\n".join(merged)


# ======== ROUTES ========

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    """Nhận dữ liệu folder upload từ frontend, mỗi file xử lý riêng."""
    data = request.get_json()
    files = data.get("files", {})

    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    allowed_ext = (".py", ".html", ".css", ".js")
    valid_files = {
        name: content for name, content in files.items()
        if name.lower().endswith(allowed_ext)
    }

    if not valid_files:
        return jsonify({"error": "No valid code files (.py, .html, .css, .js) found"}), 400

    dot_results = {}
    file_jsons = {}
    errors = {}

    # --- Gửi từng file tới Gemini ---
    for filename, code in valid_files.items():
        dot_code, err = send_to_gemini(filename, code)
        if err:
            file_jsons[filename] = {"error": err}
            errors[filename] = err
        else:
            dot_results[filename] = dot_code
            file_jsons[filename] = {"dot_code": dot_code, "status": "success"}

    # --- Nếu không file nào thành công ---
    if not dot_results:
        return jsonify({
            "error": "All files failed to process.",
            "details": errors
        }), 500

    # --- Hợp nhất toàn bộ sơ đồ ---
    merged_dot = merge_dot_graphs(dot_results.values())

    try:
        dot = graphviz.Source(merged_dot, format="svg")
        svg_data = dot.pipe(format="svg").decode("utf-8")

        # --- Trả JSON mới (theo từng file) ---
        return jsonify({
            "json_response": {
                "files": file_jsons,
                "summary": {
                    "processed": len(dot_results),
                    "failed": len(errors)
                }
            },
            "dot_code": merged_dot,
            "diagram": svg_data
        })

    except Exception as e:
        return jsonify({
            "error": f"Graphviz render error: {str(e)}", 
            "error": f"Graphviz render error: {str(e)}",
            "dot_code": merged_dot
        }), 500


if __name__ == '__main__':
    app.run(debug=True)