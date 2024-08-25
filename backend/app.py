import json
import logging
import os
import subprocess
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

UPLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__))
logging.info(f"UPLOAD_FOLDER: {UPLOAD_FOLDER}")


@app.route('/api/recommend', methods=['POST'])
def recommend_source_tables():
    try:
        if 'source_file' not in request.files or 'target_file' not in request.files:
            logging.error("Source file or target file not in request.files")
            return jsonify({'error': 'Source file or target file not provided'}), 400

        source_file = request.files['source_file']
        target_file = request.files['target_file']

        source_file_path = os.path.join(UPLOAD_FOLDER, 'uploaded_source.xlsx')
        target_file_path = os.path.join(UPLOAD_FOLDER, 'uploaded_target.json')

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        logging.info(f"Saving source file to: {source_file_path}")
        logging.info(f"Saving target file to: {target_file_path}")

        source_file.save(source_file_path)
        target_file.save(target_file_path)

        logging.info(f"Source file saved to: {source_file_path}")
        logging.info(f"Target file saved to: {target_file_path}")

        python_executable = sys.executable
        workflow_script = os.path.join(UPLOAD_FOLDER, 'workflow.py')

        logging.info(f"Executing script: {workflow_script}")

        result = subprocess.run([python_executable, workflow_script], capture_output=True, text=True, encoding='utf-8')

        logging.info(f"stdout: {result.stdout}")
        logging.error(f"stderr: {result.stderr}")

        if result.returncode == 0:
            with open(os.path.join(UPLOAD_FOLDER, 'table_analysis.json'), 'r', encoding='utf-8') as f:
                analysis_result = json.load(f)
            return jsonify(analysis_result['union'])
        else:
            logging.error(f"Script execution failed: {result.stderr}")
            return jsonify({'error': 'Failed to execute script'}), 500
    except Exception as e:
        logging.exception("Exception occurred during file processing")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recommend_fields', methods=['POST'])
def recommend_fields():
    try:
        if 'source_file' not in request.files or 'target_file' not in request.files:
            logging.error("Source file or target file not in request.files")
            return jsonify({'error': 'Source file or target file not provided'}), 400

        source_file = request.files['source_file']
        target_file = request.files['target_file']

        source_file_path = os.path.join(UPLOAD_FOLDER, 'uploaded_tables.json')
        target_file_path = os.path.join(UPLOAD_FOLDER, 'uploaded_target.json')

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        logging.info(f"Saving source file to: {source_file_path}")
        logging.info(f"Saving target file to: {target_file_path}")

        source_file.save(source_file_path)
        target_file.save(target_file_path)

        logging.info(f"Source file saved to: {source_file_path}")
        logging.info(f"Target file saved to: {target_file_path}")

        python_executable = sys.executable
        workflow_script = os.path.join(UPLOAD_FOLDER, 'workflow2.py')

        logging.info(f"Executing script: {workflow_script}")

        result = subprocess.run([python_executable, workflow_script], capture_output=True, text=True, encoding='utf-8')

        if result.stdout:
            logging.info(f"stdout: {result.stdout}")
        if result.stderr:
            logging.error(f"stderr: {result.stderr}")

        if result.returncode == 0:
            with open(os.path.join(UPLOAD_FOLDER, 'mapping_fields.json'), 'r', encoding='utf-8') as f:
                mappings_result = json.load(f)
            return jsonify(mappings_result)
        else:
            logging.error(f"Script execution failed: {result.stderr}")
            return jsonify({'error': 'Failed to execute script'}), 500
    except Exception as e:
        logging.exception("Exception occurred during file processing")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate_sql', methods=['POST'])
def generate_sql():
    try:
        field_mappings = request.get_json()
        if not field_mappings:
            return jsonify({'error': 'No field mappings provided'}), 400

        mappings_file_path = os.path.join(UPLOAD_FOLDER, 'field_mappings.json')
        with open(mappings_file_path, 'w', encoding='utf-8') as f:
            json.dump(field_mappings, f, ensure_ascii=False, indent=4)

        python_executable = sys.executable
        workflow_script = os.path.join(UPLOAD_FOLDER, 'workflow3.py')

        logging.info(f"Executing script: {workflow_script}")

        result = subprocess.run([python_executable, workflow_script], capture_output=True, text=True, encoding='utf-8')

        if result.returncode == 0:
            with open(os.path.join(UPLOAD_FOLDER, 'generated_sql.sql'), 'r', encoding='utf-8') as f:
                generated_sql = f.read()
            return jsonify({'sql': generated_sql})
        else:
            logging.error(f"Script execution failed: {result.stderr}")
            return jsonify({'error': 'Failed to execute script'}), 500
    except Exception as e:
        logging.exception("Exception occurred during SQL generation")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000)
