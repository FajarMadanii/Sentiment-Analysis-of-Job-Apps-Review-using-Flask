document.addEventListener("DOMContentLoaded", function () {
    let fileInput = document.getElementById("file-input");
    let fileNameDisplay = document.getElementById("file-name");
    let uploadForm = document.getElementById("upload-form");
    let loading = document.getElementById("loading");
    let errorMessage = document.getElementById("error-message");
    let resultSection = document.getElementById("result-section");
    let chartSection = document.getElementById("chart-section");

    // Sembunyikan hasil prediksi & chart saat pertama kali load
    resultSection.style.display = "none";
    chartSection.style.display = "none";

    fileInput.addEventListener("change", function () {
        fileNameDisplay.textContent = this.files.length ? this.files[0].name : "Tidak ada file dipilih";
    });

    uploadForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        let file = fileInput.files[0];
        if (!file) {
            errorMessage.style.display = "block";
            errorMessage.innerText = "Pilih file CSV terlebih dahulu!";
            return;
        }

        errorMessage.style.display = "none";
        loading.style.display = "block";

        resultSection.style.display = "none";
        chartSection.style.display = "none";

        let formData = new FormData();
        formData.append("file", file);

        try {
            let response = await fetch("/upload", {
                method: "POST",
                body: formData
            });

            let data = await response.json();
            loading.style.display = "none";

            if (data.error) {
                errorMessage.style.display = "block";
                errorMessage.innerText = data.error;
                return;
            }

            displayResults(data.predictions);
            updateChart(data.sentiment_counts);
            updateTrendChart(data.predictions);

            const keywords = extractKeywordsBySentimentAndMonth(data.predictions);
            renderKeywordTable(keywords);
            document.getElementById("keyword-table-section").style.display = "block";

            resultSection.style.display = "block";
            chartSection.style.display = "block";

        } catch (error) {
            console.error("Error:", error);
            loading.style.display = "none";
            errorMessage.style.display = "block";
            errorMessage.innerText = "Terjadi kesalahan saat memproses file.";
        }
    });

    document.getElementById("filter-sentiment").addEventListener("change", function () {
        let filterValue = this.value;
        let rows = document.querySelectorAll("#result-table tbody tr");

        rows.forEach(row => {
            let sentiment = row.getAttribute("data-sentiment");
            row.style.display = (filterValue === "all" || sentiment === filterValue) ? "" : "none";
        });
    });

    document.getElementById("title-input").addEventListener("input", function () {
        let titleText = this.value.trim();
        let titleDisplay = document.getElementById("analysis-title");

        if (titleText) {
            titleDisplay.textContent = titleText;
            titleDisplay.style.display = "block";
        } else {
            titleDisplay.style.display = "none";
        }
    });

    function displayResults(predictions) {
        let tableBody = document.querySelector("#result-table tbody");
        tableBody.innerHTML = "";

        predictions.forEach(row => {
            let tr = document.createElement("tr");
            tr.setAttribute("data-sentiment", row.sentiment);
            tr.innerHTML = `
                <td>${row.content}</td>
                <td>${row.score}</td>
                <td>${row.date}</td>
                <td>${row.sentiment}</td>
            `;
            tableBody.appendChild(tr);
        });
    }

    function updateChart(sentimentCounts) {
        let ctx = document.getElementById("sentiment-chart").getContext("2d");

        if (window.sentimentChart) {
            window.sentimentChart.destroy();
        }

        window.sentimentChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["Positif", "Netral", "Negatif"],
                datasets: [{
                    label: "Jumlah Sentimen",
                    data: [sentimentCounts.positif || 0, sentimentCounts.netral || 0, sentimentCounts.negatif || 0],
                    backgroundColor: ["green", "yellow", "red"]
                }]
            },
            options: { responsive: true, plugins: { legend: { display: false } } }
        });
    }

    function processMonthlyTrend(predictions) {
        const trendData = {};

        predictions.forEach(item => {
            let dateParts = item.date.split("-");
            if (dateParts.length !== 3) return;

            let yearMonth = `${dateParts[2]}-${dateParts[1]}`;

            if (!trendData[yearMonth]) {
                trendData[yearMonth] = { positif: 0, netral: 0, negatif: 0 };
            }

            let sentiment = item.sentiment.toLowerCase();
            if (["positif", "netral", "negatif"].includes(sentiment)) {
                trendData[yearMonth][sentiment]++;
            }
        });

        let sortedMonths = Object.keys(trendData).sort();
        let labels = sortedMonths;
        let positifData = [], netralData = [], negatifData = [];

        sortedMonths.forEach(m => {
            positifData.push(trendData[m].positif);
            netralData.push(trendData[m].netral);
            negatifData.push(trendData[m].negatif);
        });

        return { labels, positifData, netralData, negatifData };
    }

    function updateTrendChart(predictions) {
        const canvas = document.getElementById("trend-chart");
        if (!canvas) {
            console.warn("Canvas trend-chart tidak ditemukan.");
            return;
        }

        const ctx = canvas.getContext("2d");

        if (window.trendChart) {
            window.trendChart.destroy();
        }

        const { labels, positifData, netralData, negatifData } = processMonthlyTrend(predictions);

        window.trendChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Positif",
                        data: positifData,
                        borderColor: "green",
                        backgroundColor: "rgba(0,128,0,0.1)",
                        fill: true,
                        tension: 0.3,
                    },
                    {
                        label: "Netral",
                        data: netralData,
                        borderColor: "orange",
                        backgroundColor: "rgba(255,165,0,0.1)",
                        fill: true,
                        tension: 0.3,
                    },
                    {
                        label: "Negatif",
                        data: negatifData,
                        borderColor: "red",
                        backgroundColor: "rgba(255,0,0,0.1)",
                        fill: true,
                        tension: 0.3,
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: true } },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: "Jumlah Ulasan" } },
                    x: { title: { display: true, text: "Bulan (YYYY-MM)" } }
                }
            }
        });
    }
});

function extractKeywordsBySentimentAndMonth(predictions, topN = 20) {
    // Struktur data: { "YYYY-MM": { positif: {word: count}, netral: {}, negatif: {} } }
    const keywordData = {};

    predictions.forEach(item => {
        // Ubah tanggal menjadi format YYYY-MM
        let dateParts = item.date.split("-");
        if (dateParts.length !== 3) return;
        const yearMonth = `${dateParts[2]}-${dateParts[1]}`;

        if (!keywordData[yearMonth]) {
            keywordData[yearMonth] = {
                positif: {},
                netral: {},
                negatif: {}
            };
        }

        const sentiment = item.sentiment.toLowerCase();
        if (!["positif", "netral", "negatif"].includes(sentiment)) return;

        // Tokenisasi sederhana, bisa disesuaikan dengan preprocessing-mu
        let words = item.content.toLowerCase().match(/\b\w+\b/g);
        if (!words) return;

        words.forEach(word => {
            if (word.length <= 2) return; // abaikan kata sangat pendek

            if (!keywordData[yearMonth][sentiment][word]) {
                keywordData[yearMonth][sentiment][word] = 0;
            }
            keywordData[yearMonth][sentiment][word]++;
        });
    });

    // Ambil top N kata kunci per sentimen tiap bulan
    const results = [];
    Object.keys(keywordData).sort().forEach(month => {
        const monthData = keywordData[month];
        const row = { month: month };

        ["positif", "netral", "negatif"].forEach(sent => {
            const wordsCount = monthData[sent];
            // Sort words by frequency desc, ambil topN
            const topWords = Object.entries(wordsCount)
                .sort((a,b) => b[1] - a[1])
                .slice(0, topN)
                .map(wc => wc[0])
                .join(", ");
            row[sent] = topWords || "-";
        });

        results.push(row);
    });

    return results;
}

function renderKeywordTable(keywords) {
    const tbody = document.querySelector("#keyword-table tbody");
    tbody.innerHTML = "";

    if (!keywords.length) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;">Tidak ada data kata kunci</td></tr>`;
        return;
    }

    keywords.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${row.month}</td>
            <td>${row.positif}</td>
            <td>${row.netral}</td>
            <td>${row.negatif}</td>
        `;
        tbody.appendChild(tr);
    });
}

