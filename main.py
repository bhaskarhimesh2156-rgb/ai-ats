import os
import uuid
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv

# 1. Initialization
load_dotenv()
app = Flask(__name__)
CORS(app)

# 2. Path Handling (Windows/Vercel)
if os.name == 'nt':
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
else:
    UPLOAD_FOLDER = "/tmp"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# 3. API Client
GEMINI_KEY = os.environ.get("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    temp_path = None
    try:
        # Validate Input
        if "resume" not in request.files or "job_description" not in request.form:
            return jsonify({"error": "Missing file or description"}), 400

        resume_file = request.files["resume"]
        jd_text = request.form.get("job_description")

        # Save File Temporarily
        unique_name = f"{uuid.uuid4()}.pdf"
        temp_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        resume_file.save(temp_path)

        # Step 1: Upload to Gemini File API (Advanced Mode)
        # This allows Gemini to "see" the PDF structure for better accuracy
        uploaded_file = client.files.upload(file=temp_path)

        # Step 2: Generate Content
        prompt = f"""
        Act as a professional ATS. Analyze the provided resume against this Job Description:
        {jd_text}

        Return a JSON object with these keys:
        - "score": (number 0-100)
        - "matching_skills": (list of strings)
        - "missing_skills": (list of strings)
        - "advice": (list of 3 specific improvement tips)
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, uploaded_file],
            config={'response_mime_type': 'application/json'}
        )

        return jsonify(response.text)

    except Exception as e:
        print(f"TERMINAL ERROR: {str(e)}")
        return jsonify({"error": "Check terminal for API or File issues"}), 500
    
    finally:
        # Cleanup
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    app.run(debug=True, port=8080)