import os
import uuid
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv

# 1. Setup
load_dotenv()
app = Flask(__name__)
CORS(app)

# 2. Path Handling for Windows/Linux
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads") if os.name == 'nt' else "/tmp"
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
        if "resume" not in request.files or "job_description" not in request.form:
            return jsonify({"error": "Missing file or description"}), 400

        resume_file = request.files["resume"]
        jd_text = request.form.get("job_description")

        unique_name = f"{uuid.uuid4()}.pdf"
        temp_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        resume_file.save(temp_path)

        # Upload to Gemini File API
        uploaded_file = client.files.upload(file=temp_path)

        prompt = f"""
        Act as a professional ATS. Analyze the resume against this Job Description:
        {jd_text}

        Return ONLY a JSON object with these keys:
        - "score": (integer 0-100)
        - "matching_skills": (list of top 4 matching skills)
        - "missing_skills": (list of top 4 missing/required skills)
        - "advice": (list of 3 specific improvement tips)
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, uploaded_file],
            config={'response_mime_type': 'application/json'}
        )


        # Parse string to dictionary to avoid double-encoding
        return jsonify(json.loads(response.text))

    except Exception as e:
        print(f"Server Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    app.run(debug=True, port=8080)
