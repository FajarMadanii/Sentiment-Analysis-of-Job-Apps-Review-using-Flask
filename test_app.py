import io
import re
import pytest
from unittest.mock import patch
from app import app, model, tfidf, text_preprocessor, process_uploaded_file, scrape_reviews

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# ======== Test fungsi process_uploaded_file ========
def test_process_uploaded_file():
    csv_content = "content,date,score\nBagus,2023-06-01,5\nKurang,2023-06-02,2\n"
    file = io.StringIO(csv_content)
    result = process_uploaded_file(file, model, tfidf, text_preprocessor)
    assert "predictions" in result
    assert "sentiment_counts" in result
    assert isinstance(result["predictions"], list)
    assert isinstance(result["sentiment_counts"], dict)

def test_process_uploaded_file_empty_file():
    file = io.StringIO("")
    file.seek(0)  # Pastikan pointer file di awal
    with pytest.raises(ValueError, match=re.escape("File CSV kosong atau tidak memiliki data")):
        process_uploaded_file(file, model, tfidf, text_preprocessor)

def test_process_uploaded_file_missing_column():
    csv_content = "content,date\nData,2023-01-01"
    file = io.StringIO(csv_content)
    with pytest.raises(ValueError, match=re.escape("Kolom score tidak ditemukan")):
        process_uploaded_file(file, model, tfidf, text_preprocessor)

def test_process_uploaded_file_all_empty_after_clean():
    csv_content = "content,date,score\nabc,2023-01-01,5\nxyz,2023-01-02,4\n"
    file = io.StringIO(csv_content)
    with patch.object(text_preprocessor, 'transform', return_value=["", ""]):
        with pytest.raises(ValueError, match=re.escape("Semua data kosong setelah preprocessing")):
            process_uploaded_file(file, model, tfidf, text_preprocessor)

# ======== Test fungsi scrape_reviews ========
def test_scrape_reviews_valid():
    from datetime import datetime
    # Mock reviews function untuk mengembalikan beberapa review valid
    def fake_reviews(app_id, lang, country, sort, count, continuation_token=None):
        return ([
            {
                "content": "Bagus aplikasinya",
                "score": 5,
                "at": datetime(2023, 6, 1)
            },
            {
                "content": "Kurang memuaskan",
                "score": 2,
                "at": datetime(2023, 6, 2)
            }
        ], None)
    
    with patch("app.reviews", side_effect=fake_reviews):
        reviews_result = scrape_reviews("linkedin", "2023-06-01", "2023-06-30")
        assert isinstance(reviews_result, list)
        assert len(reviews_result) == 2
        assert all("content" in r and "date" in r and "score" in r for r in reviews_result)

def test_scrape_reviews_invalid_platform():
    with pytest.raises(ValueError, match=re.escape("Platform tidak didukung")):
        scrape_reviews("unknown_platform", "2023-01-01", "2023-12-31")

def test_scrape_reviews_loop_break():
    from datetime import datetime
    # Review dengan tanggal sebelum start_date, harus break dan return empty list
    def fake_reviews(app_id, lang, country, sort, count, continuation_token=None):
        return ([
            {
                "content": "Review lama",
                "score": 1,
                "at": datetime(2022, 12, 31)
            }
        ], None)
    
    with patch("app.reviews", side_effect=fake_reviews):
        result = scrape_reviews("linkedin", "2023-01-01", "2023-12-31")
        assert result == []

# ======== Test route upload_file ========
def test_upload_file_success(client):
    csv_content = "content,date,score\nBagus,2023-06-01,5\nKurang,2023-06-02,2\n"
    data = {
        "file": (io.BytesIO(csv_content.encode('utf-8')), "test.csv")
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    json_data = response.get_json()
    assert "predictions" in json_data
    assert "sentiment_counts" in json_data

def test_upload_file_no_file(client):
    response = client.post("/upload", data={})
    assert response.status_code == 400
    assert b"File tidak ditemukan" in response.data

def test_upload_file_unexpected_exception(client):
    with patch("app.process_uploaded_file", side_effect=Exception("Error tak terduga")):
        csv_content = "content,date,score\nBagus,2023-06-01,5\n"
        data = {
            "file": (io.BytesIO(csv_content.encode('utf-8')), "test.csv")
        }
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        assert response.status_code == 500
        assert b"Terjadi kesalahan saat memproses file" in response.data

# ======== Test route scrape_data ========
def test_scrape_route_get(client):
    response = client.get("/scrape")
    assert response.status_code == 200
    assert b"form" in response.data  # cek ada form di halaman

def test_scrape_route_post_success(client):
    from datetime import datetime
    def fake_reviews(app_id, lang, country, sort, count, continuation_token=None):
        return ([{
            "content": "Bagus aplikasinya",
            "score": 5,
            "at": datetime(2023, 6, 1)
        }], None)

    with patch("app.reviews", side_effect=fake_reviews):
        data = {
            "platform": "linkedin",
            "start_date": "2023-06-01",
            "end_date": "2023-06-30"
        }
        response = client.post("/scrape", json=data)
        assert response.status_code == 200
        json_data = response.get_json()
        assert "reviews" in json_data
        assert isinstance(json_data["reviews"], list)

def test_scrape_route_post_missing_input(client):
    data = {
        "platform": "linkedin",
        # missing start_date and end_date
    }
    response = client.post("/scrape", json=data)
    assert response.status_code == 400
    assert b"Semua input wajib diisi" in response.data

def test_scrape_route_post_invalid_platform(client):
    data = {
        "platform": "unknown_platform",
        "start_date": "2023-06-01",
        "end_date": "2023-06-30"
    }
    response = client.post("/scrape", json=data)
    assert response.status_code == 400
    assert b"Platform tidak didukung" in response.data

def test_scrape_route_post_exception(client):
    with patch("app.scrape_reviews", side_effect=Exception("Error scraping")):
        data = {
            "platform": "linkedin",
            "start_date": "2023-06-01",
            "end_date": "2023-06-30"
        }
        response = client.post("/scrape", json=data)
        assert response.status_code == 500
        assert b"Gagal mengambil data" in response.data
