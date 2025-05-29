from flask import Flask, request, jsonify, render_template
import joblib
import pandas as pd
from preprocessing import TextPreprocessor
from flask_cors import CORS
from google_play_scraper import reviews, Sort
from datetime import datetime
import time
import logging
import csv

app = Flask(__name__, template_folder="templates")
CORS(app)

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ID aplikasi dari Play Store
APP_IDS = {
    "linkedin": "com.linkedin.android",
    "glints": "com.glints.candidate",
    "indeed": "com.indeed.android.jobsearch"
}

# Load model dan TF-IDF
try:
    model = joblib.load("model/extra_trees_model.joblib")
    tfidf = joblib.load("model/tfidf_vectorizer.joblib")
    text_preprocessor = TextPreprocessor()
    logger.info("Model dan vectorizer berhasil dimuat.")
except Exception as e:
    logger.error(f"Error loading model/vectorizer: {e}")
    model, tfidf, text_preprocessor = None, None, None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Tidak ada file yang diupload"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nama file kosong"}), 400

    try:
        df = pd.read_csv(file, sep=",", quoting=csv.QUOTE_MINIMAL, on_bad_lines="skip", encoding="utf-8", engine="python")
        if df.empty:
            return jsonify({"error": "File CSV kosong atau tidak memiliki data"}), 400

        # Validasi kolom wajib
        required_columns = {"content", "date", "score"}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            return jsonify({"error": f"Kolom {', '.join(missing_columns)} tidak ditemukan"}), 400

        # Preprocessing teks
        df["clean_text"] = text_preprocessor.transform(df["content"].astype(str))
        df = df[df["clean_text"].str.strip() != ""]

        if df.empty:
            return jsonify({"error": "Semua data kosong setelah preprocessing!"}), 400

        # Prediksi sentimen
        X_tfidf = tfidf.transform(df["clean_text"])
        predictions_raw = model.predict(X_tfidf)

        # Pastikan label sentimen lowercase supaya seragam
        predictions = [p.lower() for p in predictions_raw]
        df["sentiment"] = predictions

        # Hitung jumlah tiap sentimen
        sentiment_counts = {
            "positif": int((df["sentiment"] == "positif").sum()),
            "netral": int((df["sentiment"] == "netral").sum()),
            "negatif": int((df["sentiment"] == "negatif").sum())
        }

        # Ambil kolom yang diperlukan untuk frontend
        result = df[["content", "date", "score", "sentiment"]].to_dict(orient="records")

        return jsonify({"predictions": result, "sentiment_counts": sentiment_counts})

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return jsonify({"error": "Terjadi kesalahan saat memproses file"}), 500

@app.route("/scrape", methods=["GET", "POST"])
def scrape_data():
    if request.method == "GET":
        return render_template("scrape.html")

    try:
        data = request.json
        platform = data.get("platform")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if not platform or platform not in APP_IDS:
            return jsonify({"error": "Platform tidak valid atau tidak didukung!"})

        if not start_date or not end_date:
            return jsonify({"error": "Tanggal mulai dan akhir harus diisi!"})

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        all_reviews = []
        seen_reviews = set()
        continuation_token = None

        while True:
            raw_reviews, continuation_token = reviews(
                APP_IDS[platform],
                lang="id",
                country="id",
                sort=Sort.NEWEST,
                count=200,
                continuation_token=continuation_token
            )

            for r in raw_reviews:
                if "content" in r and r["content"].strip() and "score" in r and r["score"] and "at" in r:
                    review_date = r["at"]
                    review_tuple = (r["content"].strip(), review_date.strftime("%d-%m-%Y"), r["score"])

                    if review_date < start_dt:
                        continuation_token = None
                        break

                    if start_dt <= review_date <= end_dt and review_tuple not in seen_reviews:
                        seen_reviews.add(review_tuple)
                        all_reviews.append({
                            "content": r["content"],
                            "date": review_date.strftime("%d-%m-%Y"),
                            "score": r["score"]
                        })

            if not continuation_token:
                break

            time.sleep(1)

        all_reviews.sort(key=lambda x: datetime.strptime(x["date"], "%d-%m-%Y"))

        return jsonify({"reviews": all_reviews})

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        return jsonify({"error": "Gagal mengambil data, coba lagi nanti."})

if __name__ == "__main__":
    app.run(debug=True)
