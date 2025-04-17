let allScrapedData = []; // Simpan semua data global

document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("scrape-btn")?.addEventListener("click", handleScrape);
    document.getElementById("download-btn")?.addEventListener("click", downloadCSV);
});

async function handleScrape() {
    const platform = document.getElementById("platform").value;
    const startDate = document.getElementById("start_date").value;
    const endDate = document.getElementById("end_date").value;

    const loading = document.getElementById("loading");
    const errorMessage = document.getElementById("error-message");
    const resultSection = document.getElementById("result-section");
    const downloadBtn = document.getElementById("download-btn");

    if (!platform || !startDate || !endDate) {
        alert("Harap pilih platform dan isi rentang tanggal.");
        return;
    }

    resultSection.style.display = "none";
    downloadBtn.style.display = "none";
    errorMessage.style.display = "none";
    loading.style.display = "block";

    try {
        const response = await fetch("/scrape", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ platform, start_date: startDate, end_date: endDate })
        });

        const data = await response.json();
        loading.style.display = "none";

        if (data.error) {
            errorMessage.style.display = "block";
            errorMessage.innerText = data.error;
            return;
        }

        allScrapedData = [];
        let uniqueReviews = new Map(); // Gunakan Map agar penyaringan lebih efisien

        data.reviews.forEach(row => {
            let content = row.content?.trim() || "Tidak ada ulasan";
            let date = row.date || "Tidak ada tanggal";
            let score = row.score ?? "N/A"; 

            let uniqueKey = `${content}_${date}_${score}`;
            if (!uniqueReviews.has(uniqueKey)) {
                uniqueReviews.set(uniqueKey, { content, date, score });
            }
        });

        allScrapedData = Array.from(uniqueReviews.values());

        // 🔥 Urutkan berdasarkan tanggal dari paling lama ke terbaru
        allScrapedData.sort((a, b) => {
            let dateA = parseDate(a.date);
            let dateB = parseDate(b.date);
            return dateA - dateB;
        });

        displayScrapedResults(allScrapedData);

        resultSection.style.display = "block";
        downloadBtn.style.display = "block";
    } catch (error) {
        console.error("Error:", error);
        loading.style.display = "none";
        errorMessage.style.display = "block";
        errorMessage.innerText = "Terjadi kesalahan saat mengambil data.";
    }
}

function parseDate(dateStr) {
    let parts = dateStr.split("-");
    if (parts.length === 3) {
        return new Date(parts[2], parts[1] - 1, parts[0]); // Format: dd-mm-yyyy
    }
    return new Date(); // Jika gagal, pakai tanggal sekarang
}

function displayScrapedResults(reviews) {
    const tableBody = document.querySelector("#result-table tbody");
    if (!tableBody) return;

    tableBody.innerHTML = ""; 

    reviews.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${row.content}</td>
            <td>${row.score}</td>
            <td>${row.date}</td>
        `;
        tableBody.appendChild(tr);
    });
}

// 🔥 FIX: Download CSV dengan format yang lebih aman
function downloadCSV() {
    if (allScrapedData.length === 0) {
        alert("Tidak ada data untuk diunduh!");
        return;
    }

    let csvRows = ["content,date,score"];
    allScrapedData.forEach(row => {
        let safeContent = row.content.replace(/"/g, '""'); // Escape tanda kutip
        csvRows.push(`"${safeContent}","${row.date}","${row.score}"`);
    });

    let blob = new Blob([csvRows.join("\n")], { type: "text/csv" });
    let url = URL.createObjectURL(blob);
    let link = document.createElement("a");

    link.href = url;
    link.download = "scraped_data.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}
