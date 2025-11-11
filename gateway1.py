# gateway1.py
import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from google import genai              # Imports the main library
from google.genai.errors import APIError

app = Flask(__name__)

# --- CONFIGURATION AND INITIALIZATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    # Forces an immediate, clear crash if the environment variable is missing
    print("FATAL ERROR: GEMINI_API_KEY environment variable not found. Server cannot start.")
    exit(1) 

# **CRITICAL FIX**: The new way to initialize and authenticate the client
try:
    # Create a client object, passing the API key directly.
    # All subsequent API calls will use this client.
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"FATAL ERROR: Could not create Gemini client. Error: {e}")
    exit(1)


# Directory to temporarily save the file (Render uses /tmp)
UPLOAD_FOLDER = '/tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
GEMINI_MODEL = "gemini-2.5-flash" # Excellent model for transcription and fast responses


@app.route('/upload', methods=['POST'])
def upload_audio():
    """
    Receives audio file from ESP32, transcribes it via Gemini, and returns the text.
    Uses the modern genai.Client() methods for stability.
    """
    
    # Initialize variables to None for safe cleanup in the 'finally' block
    audio_file_uploaded_to_gemini = None 
    temp_filepath = None
    
    try:
        # 1. Check for the file from the multipart form
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # 2. Save the incoming audio file temporarily
        filename = secure_filename(file.filename or "uploaded_audio.wav")
        temp_filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(temp_filepath)
        print(f"✅ File received and saved to: {temp_filepath}")
        
        # --- GEMINI API CALL START ---
        
        # 3. Upload the file to the Gemini service using the client object
        print("Uploading audio file to Gemini service...")
        audio_file_uploaded_to_gemini = client.files.upload(file=temp_filepath)
        
        # 4. Ask Gemini to transcribe
        print("Requesting transcription from Gemini...")
        
        # Use the client to get the model
        model = client.models.get(model_name=GEMINI_MODEL) 

        # The prompt guides the model to perform only transcription
        response = model.generate_content(
            contents=[
                "Please transcribe the following audio file. Return only the text of the speech, and do not add any extra commentary or introductory phrases.", 
                audio_file_uploaded_to_gemini
            ]
        )
        
        transcription_text = response.text.strip()
        
        # --- GEMINI API CALL END ---

        # 5. Return the transcription to the ESP32 (Raw text is expected by client)
        print(f"Transcription complete. Response text: {transcription_text}")
        return transcription_text, 200

    except APIError as e:
        error_message = f"Gemini API Error: {e}"
        print(f"❌ {error_message}")
        return jsonify({"error": "Transcription failed", "details": error_message}), 500
        
    except Exception as e:
        error_message = f"Internal Server Error: {e}"
        print(f"❌ {error_message}")
        return jsonify({"error": "Server error", "details": error_message}), 500

    finally:
        # 6. CRITICAL CLEANUP: Delete the local temp file and the file uploaded to Gemini
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            print(f"Cleaned up local file: {temp_filepath}")
            
        if audio_file_uploaded_to_gemini:
             # Use client.files.delete for cleanup
             try:
                 client.files.delete(name=audio_file_uploaded_to_gemini.name)
                 print(f"Cleaned up Gemini uploaded file: {audio_file_uploaded_to_gemini.name}")
             except Exception as e:
                 print(f"Warning: Failed to delete Gemini file: {e}")


# Standard Flask way to run the application
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
