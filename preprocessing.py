from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from nltk.tokenize import word_tokenize
import re
from sklearn.base import BaseEstimator, TransformerMixin
import json

# Inisialisasi stemmer
factory_stemmer = StemmerFactory()
stemmer = factory_stemmer.create_stemmer()

# Inisialisasi stopword remover dan ambil list stopwords-nya
factory_stopwords = StopWordRemoverFactory()
stopwords_id = set(factory_stopwords.get_stop_words())

# Load slang dictionary (sama seperti sebelumnya)
with open('preprocessing/slang_words.txt', 'r', encoding='utf-8') as file:
    slang_dict = json.load(file)

class TextPreprocessor(BaseEstimator, TransformerMixin):
    def clean_text(self, text):
        if not isinstance(text, str):
            return ""
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip().lower()
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        return text

    def normalize_slang(self, text):
        tokens = text.split()
        normalized_tokens = [slang_dict.get(token, token) for token in tokens]
        return ' '.join(normalized_tokens)

    def tokenize_text(self, text):
        return word_tokenize(text)

    def remove_stopwords(self, tokens):
        return [word for word in tokens if word not in stopwords_id]

    def stemming_tokens(self, tokens):
        return [stemmer.stem(token) for token in tokens]

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_cleaned = [self.clean_text(text) for text in X]
        X_normalized = [self.normalize_slang(text) for text in X_cleaned]
        X_tokens = [self.tokenize_text(text) for text in X_normalized]
        X_no_stopwords = [self.remove_stopwords(tokens) for tokens in X_tokens]
        X_stemmed = [self.stemming_tokens(tokens) for tokens in X_no_stopwords]

        # Hapus stopwords lagi setelah stemming
        X_final = [self.remove_stopwords(tokens) for tokens in X_stemmed]

        return [' '.join(tokens) for tokens in X_final]
