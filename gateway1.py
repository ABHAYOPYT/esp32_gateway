# gateway1.py
import os
import io 
import time
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

# --- CRITICAL IMPORTS FOR GEMINI ---
# Ensure 'google-genai' is in your requirements.txt
try:
    from google import genai
    from google.genai.errors import APIError
except ImportError:
    print("FATAL ERROR: 'google-genai' library not found. Check requirements.txt and deploy logs.")
    exit(1)

app = Flask(__name__)

# --- CONFIGURATION AND INITIALIZATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("FATAL ERROR: GEMINI_API_KEY environment variable not found. Server cannot start.")
    exit(1) 

# Configure the Gemini Client
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"FATAL ERROR: Could not configure Gemini client. Error: {e}")
    exit(1)

# Define a temporary folder for file storage (Render uses /tmp)
UPLOAD_FOLDER = '/tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
GEMINI_MODEL = "gemini-2.5-flash" # Excellent model for transcription and fast responses


@app.route('/upload', methods=['POST'])
def upload_audio():
    """
    Receives audio file from ESP32, transcribes it via Gemini, and returns the text.
    Uses robust file handling to prevent silent server crashes (500 errors).
    """
    
    # Initialize variables to None for safe cleanup in the 'finally' block
    audio_file_uploaded_to_gemini = None 
    temp_filepath = None
    
    try:
        # 1. Check for the file from the multipart form
        if 'file' not in request.files:
            print("❌ ERROR: No 'file' part in the request.")
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        if file.filename == '':
            print("❌ ERROR: No selected file name.")
            return jsonify({"error": "No selected file"}), 400

        # 2. Save the incoming audio file temporarily
        filename = secure_filename(file.filename or "uploaded_audio.wav")
        temp_filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        file.save(temp_filepath)
        print(f"✅ File received and saved to: {temp_filepath}")
        
        # --- GEMINI API CALL START ---
        
        # 3. Upload the file to the Gemini service
        print("Uploading audio file to Gemini service...")
        # This function uploads the file and returns a handle to it
        audio_file_uploaded_to_gemini = genai.upload_file(file=temp_filepath)
        
        # 4. Ask Gemini to transcribe
        print("Requesting transcription from Gemini...")
        model = genai.GenerativeModel(model_name=GEMINI_MODEL) 

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
        # Catches errors specific to the Gemini API (e.g., file size, invalid key, rate limit)
        error_message = f"Gemini API Error: {e}"
        print(f"❌ {error_message}")
        return jsonify({"error": "Transcription failed", "details": error_message}), 500
        
    except Exception as e:
        # Catches all other internal server errors
        error_message = f"Internal Server Error: {e}"
        print(f"❌ {error_message}")
        return jsonify({"error": "Server error", "details": error_message}), 500

    finally:
        # 6. CRITICAL CLEANUP: Delete the local temp file and the file uploaded to Gemini
        # This block runs whether the 'try' or 'except' block was executed.
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            print(f"Cleaned up local file: {temp_filepath}")
            
        if audio_file_uploaded_to_gemini:
             # Deleting the file from Gemini storage to prevent unnecessary data accumulation
             try:
                 genai.delete_file(name=audio_file_uploaded_to_gemini.name)
                 print(f"Cleaned up Gemini uploaded file: {audio_file_uploaded_to_gemini.name}")
             except Exception as e:
                 print(f"Warning: Failed to delete Gemini file: {e}")


# Standard Flask way to run the application (Render handles the PORT)
if __name__ == '__main__':
    # Render automatically sets the PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
