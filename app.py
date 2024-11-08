from flask import Flask, request, render_template, jsonify
import pandas as pd
import numpy as np
import os
import json

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

OUTPUT_JSON_PATH = 'output_matches.json'

REQUIRED_COLUMNS = ['Nama', 'Usia', 'Berat', 'Tinggi']

def validate_csv_columns(df):
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"CSV file is missing the following columns: {', '.join(missing_columns)}")

def load_and_classify_data(file_path):
    df = pd.read_csv(file_path)
    validate_csv_columns(df)

    conditions = [
        (df['Usia'] >= 12) & (df['Usia'] <= 14),
        (df['Usia'] >= 15) & (df['Usia'] <= 17),
        (df['Usia'] > 17)
    ]
    categories = ['Cadet', 'Junior', 'Senior']
    df['Kelas'] = np.select(conditions, categories, default='Unknown')
    return df

def find_opponents(df, category, match_type):
    group = df[df['Kelas'] == category]
    if match_type == 'Festival':
        weight_diff, height_diff, age_diff = 3, 5, 2
    elif match_type == 'Prestasi':
        weight_diff, height_diff, age_diff = 5, 10, 3
    else:
        raise ValueError("Invalid match type")

    matches = []
    for _, participant in group.iterrows():
        potential_opponents = group[
            (abs(group['Berat'] - participant['Berat']) <= weight_diff) &
            (abs(group['Tinggi'] - participant['Tinggi']) <= height_diff) &
            (abs(group['Usia'] - participant['Usia']) <= age_diff) &
            (group['Nama'] != participant['Nama'])
        ]

        if not potential_opponents.empty:
            opponent = potential_opponents.iloc[0]
            matches.append({
                'Peserta': participant['Nama'],
                'Lawan': opponent['Nama'],
                'Berat Peserta': int(participant['Berat']),
                'Berat Lawan': int(opponent['Berat']),
                'Tinggi Peserta': int(participant['Tinggi']),
                'Tinggi Lawan': int(opponent['Tinggi']),
                'Usia Peserta': int(participant['Usia']),
                'Usia Lawan': int(opponent['Usia'])
            })
        else:
            matches.append({
                'Peserta': participant['Nama'],
                'Lawan': "dummy",
                'Berat Peserta': int(participant['Berat']),
                'Berat Lawan': None,
                'Tinggi Peserta': int(participant['Tinggi']),
                'Tinggi Lawan': None,
                'Usia Peserta': int(participant['Usia']),
                'Usia Lawan': None
            })

    return matches

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    try:
        file = request.files['file']
        match_type = request.form['matchType']

        if not file or not match_type:
            return jsonify({"error": "Missing file or matchType"}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({"error": "Uploaded file is not a CSV"}), 400

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        df = load_and_classify_data(file_path)
        categories = ['Cadet', 'Junior', 'Senior']
        all_matches = {}

        for category in categories:
            matches = find_opponents(df, category, match_type)
            all_matches[category] = matches

        # Simpan hasil ke file JSON
        with open(OUTPUT_JSON_PATH, 'w') as json_file:
            json.dump(all_matches, json_file, indent=4)

        os.remove(file_path)  # Bersihkan file CSV yang diunggah
        return jsonify({"message": "Processing complete, results saved in output_matches.json", "data": all_matches})

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/bracket')
def bracket():
    return render_template('bracket.html')

@app.route('/get_matches')
def get_matches():
    with open('output_matches.json', 'r') as f:
        data = json.load(f)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
