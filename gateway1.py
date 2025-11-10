# gateway.py
from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

# Load OpenAI API key from Render environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def home():
    return "✅ ESP32 AI Gateway is live!"

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    audio_file = request.files['file']
    filepath = f"/tmp/{audio_file.filename}"
    audio_file.save(filepath)

    print(f"🎧 Received file: {filepath}")

    try:
        # Step 1: Transcribe audio using Whisper
        with open(filepath, "rb") as f:
            transcript = openai.Audio.transcriptions.create(
                model="whisper-1",
                file=f
            )

        user_text = transcript.text.strip()
        print("📝 Transcription:", user_text)

        # Step 2: Generate AI response using GPT
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for ESP32 projects."},
                {"role": "user", "content": user_text}
            ]
        )

        ai_reply = completion.choices[0].message.content.strip()
        print("🤖 AI Reply:", ai_reply)

        return jsonify({
            "user_text": user_text,
            "ai_reply": ai_reply
        })

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
