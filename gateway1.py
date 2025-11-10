# gateway.py
from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

# Get your key from Render’s environment variable later
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route("/upload", methods=["POST"])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400

    audio_file = request.files['file']

    print("🔊 Transcribing...")
    transcript = openai.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    text = transcript.text.strip()
    print("🗣️ You said:", text)

    print("🤖 Asking GPT...")
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a concise assistant for an OLED display."},
            {"role": "user", "content": text}
        ]
    )
    answer = response.choices[0].message.content.strip()
    print("💬 AI:", answer)

    return jsonify({"question": text, "answer": answer})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
