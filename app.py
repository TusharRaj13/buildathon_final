import os
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson.objectid import ObjectId
import uuid
import base64
import markdown
from llama_deploy import LlamaDeployClient, ControlPlaneConfig
import json
from fpdf import FPDF

app = Flask(__name__)

CORS(app)

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads'
DATA_FOLDER = 'data/output'
IMAGE_FOLDER = 'data/images'
ALLOWED_EXTENSIONS = {'csv', 'pdf'}

# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DATA_FOLDER'] = DATA_FOLDER
app.config['IMAGE_FOLDER'] = IMAGE_FOLDER

# MongoDB configuration
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client['buildathon']
files_collection = db['dataset'] 
query_collection = db['query']
report_collection = db['report']

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", size=12)
        self.cell(0, 10, "100x Buildathon", align="C", ln=True)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", size=10)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


# Function to check file extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Route for file upload
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    file_record = files_collection.find_one({'filename': file.filename})
    if file_record:
        return jsonify({'error': 'File already exist'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Store file metadata in MongoDB
        file_metadata = {
            'filename': filename,
            'upload_time': datetime.now(),
            'path': file_path
        }
        files_collection.insert_one(file_metadata)

        result = subprocess.run(
            ["python", "csv_reader.py", filename], 
            capture_output=True,
            text=True
        )
        stdout_lines = result.stdout.strip().split("\n")
        final_output = stdout_lines[-1] if stdout_lines else "No output"

        return jsonify({'message': f'File uploaded successfully. {final_output}', 'filename': filename}), 201

    return jsonify({'error': 'File type not allowed'}), 400


# Route for file download
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        return send_from_directory(app.config['DATA_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'File not found on server'}), 404
@app.route('/download_csv/<filename>', methods=['GET'])
def download_csv_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'File not found on server'}), 404
@app.route('/download_image/<filename>', methods=['GET'])
def download_image_file(filename):
    try:
        return send_from_directory(app.config['IMAGE_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'File not found on server'}), 404


@app.route('/files', methods=['GET'])
def get_files():
    files = list(files_collection.find({}, {'_id': 0}))
    return jsonify(files)

@app.route('/search', methods=['POST'])
def process_request():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data received'}), 400

    # Validate required fields
    if 'query' not in data or 'filename' not in data:
        return jsonify({'error': 'Missing required fields: query and filename'}), 400

    # Extract fields
    query = data['query']
    filename = data['filename']

    # client = LlamaDeployClient(ControlPlaneConfig())

    # #session = client.get_or_create_session("session_id")
    # session = client.create_session()

    # result = session.run("report_gen_flow", query=query, filename=filename)

    # client.delete_session(session.session_id)
    result = subprocess.run(
        ["python", "workflow_copy.py", query, filename], 
        capture_output=True,
        text=True
    )
    stdout_lines = result.stdout.strip().split("\n")
    final_output = stdout_lines[-1] if stdout_lines else "No output"
    
    return jsonify(json.loads(final_output)), 200

@app.route('/export', methods=['POST'])
def export_report():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data received'}), 400
    
    if 'type' not in data or 'id' not in data:
        return jsonify({'error': 'Missing required fields: type or id'}), 400
    
    type = data['type']
    id = data['id']

    obj_id = ObjectId(id)
    result = report_collection.find_one({'_id': obj_id})
    pages = result["pages"]

    if type == "HTML":
        output_filename = f"{uuid.uuid4()}.html"
        output_html = f"./data/output/{output_filename}"
        
        inner_html = ""
        for page in pages:
            if page["img"] != None:
                img_path = f"./data/images/{page['img']}"
                with open(img_path, "rb") as image_file:
                    base64_img = base64.b64encode(image_file.read()).decode("utf-8")
                    temp_html = f"""
                        <div>
                            <h1>{page["title"]}</h1>
                            <div>{markdown.markdown(page["content"])}</div>
                            <img src="data:image/jpeg;base64,{base64_img}" alt="Example Image"/>
                        </div>
                    """
                    inner_html += temp_html
            else:
                temp_html = f"""
                    <div>
                        <h1>{page["title"]}</h1>
                        <div>{markdown.markdown(page["content"])}</div>
                    </div>
                """
                inner_html += temp_html

        html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>HTML Example</title>
            </head>
            <body>
                <h1>Report</h1>
                {inner_html}
            </body>
            </html>
            """
        with open(output_html, "w") as file:
            file.write(html_content)
        return jsonify({'message': 'Exported successfully', 'filename': output_filename}), 200
    else:
        output_filename = f"{uuid.uuid4()}.pdf"
        output_pdf = f"./data/output/{output_filename}"
        pdf = PDF()
        for page in pages:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, page["title"], 0, 1, 'C')
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, page["content"], markdown=True)
            pdf.ln(10)
            if page['img'] != None:
                img_path = f"./data/images/{page['img']}"
                pdf.image(img_path, x=10, y=pdf.get_y() + 10, w=200)  # Adjust x, y, and w as needed
        pdf.output(output_pdf)
        return jsonify({'message': 'Exported successfully', 'filename': output_filename}), 200

# Health check route
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({'message': 'Welcome to the Flask File Upload, Download, and MongoDB API'})


# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
