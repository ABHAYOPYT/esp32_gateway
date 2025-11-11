# gateway1.py
from flask import Flask, request, jsonify
import openai
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def home():
    return "✅ ESP32 AI Gateway is live!"

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files['file']
    filename = secure_filename(file.filename)
    filepath = f"/tmp/{filename}"
    file.save(filepath)

    print(f"🎧 Received file: {filepath}")

    # Transcribe with Whisper
    try:
        with open(filepath, "rb") as audio_file:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        text = transcript.text
        print(f"Transcribed text: {text}")
    except Exception as e:
        print(f"❌ Whisper error: {e}")
        return jsonify({"error": "Transcription failed", "details": str(e)}), 500

    # Get GPT reply
    try:
        chat = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI assistant responding concisely to user speech."},
                {"role": "user", "content": text}
            ]
        )
        answer = chat.choices[0].message.content
        print(f"AI reply: {answer}")
    except Exception as e:
        print(f"❌ GPT error: {e}")
        return jsonify({"error": "GPT failed", "details": str(e)}), 500

    return jsonify({"transcription": text, "response": answer})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


