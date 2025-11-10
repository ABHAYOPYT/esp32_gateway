# gateway.py
from flask import Flask, request, jsonify
import openai
import os
app = Flask(__name__)
# Load your OpenAI API key from Render environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def home():
    return "✅ ESP32 AI Gateway is live!"

@app.route('/upload', methods=['POST'])
def upload_audio():
    # 1️⃣ Check if a file is included in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files['file']
    filepath = f"/tmp/{file.filename}"
    file.save(filepath)
    print(f"🎧 Received file: {filepath}")

    # 2️⃣ Transcribe with Whisper
    try:
        with open(filepath, "rb") as audio:
            transcript = openai.Audio.transcriptions.create(
                model="whisper-1",
                file=audio
            )
        question = transcript.text
        print("🎙 User said:", question)
    except Exception as e:
        print("⚠️ Whisper error:", e)
        return jsonify({"error": f"Whisper failed: {str(e)}"}), 500

    # 3️⃣ Get answer from GPT
    try:
        response = openai.Chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI assistant for ESP32 voice project with OLED display."},
                {"role": "user", "content": question}
            ]
        )
        answer = response.choices[0].message.content.strip()
        print("🤖 AI:", answer)
    except Exception as e:
        print("⚠️ GPT error:", e)
        return jsonify({"error": f"GPT failed: {str(e)}"}), 500

    return jsonify({"answer": answer})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)


