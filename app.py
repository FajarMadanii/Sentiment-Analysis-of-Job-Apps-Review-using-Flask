from flask import Flask, request, jsonify, render_template
import joblib
import pandas as pd
from pandas.errors import EmptyDataError
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


# ✅ Fungsi proses file upload
def process_uploaded_file(file, model, tfidf, text_preprocessor):
    try:
        df = pd.read_csv(file, sep=",", quoting=csv.QUOTE_MINIMAL, on_bad_lines="skip", encoding="utf-8", engine="python")
    except EmptyDataError:
        raise ValueError("File CSV kosong atau tidak memiliki data")

    if df.empty:
        raise ValueError("File CSV kosong atau tidak memiliki data")

    required_columns = {"content", "date", "score"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Kolom {', '.join(missing_columns)} tidak ditemukan")

    df["clean_text"] = text_preprocessor.transform(df["content"].astype(str))
    df = df[df["clean_text"].str.strip() != ""]

    if df.empty:
        raise ValueError("Semua data kosong setelah preprocessing")

    X_tfidf = tfidf.transform(df["clean_text"])
    predictions_raw = model.predict(X_tfidf)
    predictions = [p.lower() for p in predictions_raw]
    df["sentiment"] = predictions

    sentiment_counts = {
        "positif": int((df["sentiment"] == "positif").sum()),
        "netral": int((df["sentiment"] == "netral").sum()),
        "negatif": int((df["sentiment"] == "negatif").sum())
    }

    result = df[["content", "clean_text", "date", "score", "sentiment"]].to_dict(orient="records")
    return {"predictions": result, "sentiment_counts": sentiment_counts}


# ✅ Fungsi logika scraping
def scrape_reviews(platform, start_date, end_date):
    if platform not in APP_IDS:
        raise ValueError("Platform tidak didukung")

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
    return all_reviews


# ✅ Routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files or request.files["file"].filename == "":
        return jsonify({"error": "File tidak ditemukan atau nama kosong"}), 400

    try:
        file = request.files["file"]
        result = process_uploaded_file(file, model, tfidf, text_preprocessor)
        return jsonify(result)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
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

        if not platform or not start_date or not end_date:
            return jsonify({"error": "Semua input wajib diisi!"}), 400

        result = scrape_reviews(platform, start_date, end_date)
        return jsonify({"reviews": result})
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        return jsonify({"error": "Gagal mengambil data, coba lagi nanti."}), 500


if __name__ == "__main__":
    app.run(debug=True)
