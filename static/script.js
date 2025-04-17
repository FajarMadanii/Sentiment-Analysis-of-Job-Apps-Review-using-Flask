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

        // Sembunyikan hasil prediksi & chart sebelum prediksi baru dilakukan
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

            // Tampilkan hasil prediksi & chart setelah data tersedia
            displayResults(data.predictions);
            updateChart(data.sentiment_counts);
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

    // Ambil input title dan tampilkan setelah user mengetik
    document.getElementById("title-input").addEventListener("input", function () {
        let titleText = this.value.trim();
        let titleDisplay = document.getElementById("analysis-title");

        if (titleText) {
            titleDisplay.textContent = titleText;
            titleDisplay.style.display = "block"; // Tampilkan jika ada isi
        } else {
            titleDisplay.style.display = "none"; // Sembunyikan jika kosong
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
    
        // Hancurkan chart lama jika sudah ada
        if (window.sentimentChart) {
            window.sentimentChart.destroy();
        }
    
        // Buat chart baru dengan data terbaru
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
});
