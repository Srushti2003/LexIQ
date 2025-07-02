const form = document.getElementById("searchForm");
const resultsDiv = document.getElementById("results");

form.addEventListener("submit", async function (e) {
  e.preventDefault();

  const query = document.getElementById("queryInput").value;
  resultsDiv.innerHTML = "🔍 Searching...";

  const res = await fetch("/search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ query: query })
  });

  const data = await res.json();
  resultsDiv.innerHTML = "";

  if (!data.length) {
    resultsDiv.innerHTML = "<p>No cases found.</p>";
    return;
  }

  data.forEach(item => {
    const div = document.createElement("div");
    div.className = "case-card";
    div.innerHTML = `
      <h3>${item.title}</h3>
      <p><strong>Court:</strong> ${item.court}</p>
      <p><strong>Date:</strong> ${item.date}</p>
      <a href="https://indiankanoon.org/doc/${item.doc_id}/" target="_blank" rel="noopener noreferrer" class="view-case-btn">View Case</a>
    `;
    resultsDiv.appendChild(div);
  });
});

document.getElementById("uploadForm").addEventListener("submit", async function (e) {
  e.preventDefault();
  const fileInput = document.getElementById("fileInput");
  const output = document.getElementById("uploadSummaryOutput");

  if (fileInput.files.length === 0) return;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  output.innerHTML = "<p>⏳ Processing and summarizing...</p>";

  const res = await fetch("/summarize-file", {
    method: "POST",
    body: formData
  });

  const data = await res.json();
  if (data.summary) {
    output.innerHTML = `<h3>📝 Summary:</h3><p>${data.summary}</p>`;
  } else {
    output.innerHTML = `<p>Error: ${data.error}</p>`;
  }
});

// Section & Act Tagging + Similar Case Suggestions
const analyzeForm = document.getElementById("analyzeForm");
const analyzeResults = document.getElementById("analyzeResults");

if (analyzeForm) {
  analyzeForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    const fileInput = document.getElementById("analyzeFileInput");
    if (fileInput.files.length === 0) return;
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    analyzeResults.innerHTML = "<p>⏳ Analyzing document...</p>";
    const res = await fetch("/analyze-file", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.error) {
      analyzeResults.innerHTML = `<p>Error: ${data.error}</p>`;
      return;
    }
    let html = "";
    if (data.sections && data.sections.length) {
      html += `<h4>🏷️ Extracted Sections & Acts:</h4><ul>`;
      data.sections.forEach(s => {
        html += `<li>${s}</li>`;
      });
      html += `</ul>`;
    } else {
      html += `<p>No legal sections or acts found.</p>`;
    }
    analyzeResults.innerHTML = html;
  });
}

// Legal Argument Generator
const argumentForm = document.getElementById("argumentForm");
const argumentResults = document.getElementById("argumentResults");

if (argumentForm) {
  argumentForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    const input = document.getElementById("argumentInput").value.trim();
    if (!input) return;
    argumentResults.innerHTML = "<p>⏳ Generating arguments...</p>";
    const res = await fetch("/generate-arguments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input })
    });
    const data = await res.json();
    if (data.error) {
      argumentResults.innerHTML = `<p>Error: ${data.error}</p>`;
      return;
    }
    if (data.arguments && data.arguments.length) {
      let html = `<h4>Suggested Arguments/Defenses:</h4><ul>`;
      data.arguments.forEach(arg => {
        html += `<li>${arg}</li>`;
      });
      html += `</ul>`;
      argumentResults.innerHTML = html;
    } else {
      argumentResults.innerHTML = `<p>No arguments generated.</p>`;
    }
  });
}

// Case Trend Analytics
const trendForm = document.getElementById("trendForm");
const trendResults = document.getElementById("trendResults");

if (trendForm) {
  trendForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    const input = document.getElementById("trendInput").value.trim();
    if (!input) return;
    trendResults.innerHTML = "<p>⏳ Generating trend analytics...</p>";
    const res = await fetch("/case-trends", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input })
    });
    // Try to display as image or HTML
    const data = await res.json();
    if (data.error) {
      trendResults.innerHTML = `<p>Error: ${data.error}</p>`;
      return;
    }
    if (data.image_url) {
      trendResults.innerHTML = `<img src="${data.image_url}" alt="Case Trend Chart" style="max-width:100%;">`;
    } else if (data.html) {
      trendResults.innerHTML = data.html;
    } else {
      trendResults.innerHTML = `<p>No trend data available.</p>`;
    }
  });
}

// Client Brief Generator
const briefForm = document.getElementById("briefForm");
const briefResults = document.getElementById("briefResults");

if (briefForm) {
  briefForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    const fileInput = document.getElementById("briefFileInput");
    if (!fileInput.files || fileInput.files.length === 0) return;
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    briefResults.innerHTML = "<p>⏳ Generating client brief...</p>";
    const res = await fetch("/client-brief", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.error) {
      briefResults.innerHTML = `<p>Error: ${data.error}</p>`;
      return;
    }
    if (data.brief) {
      briefResults.innerHTML = `<h4>Client Brief:</h4><div style='background:#f9fbfd;padding:15px;border-radius:8px;'>${data.brief}</div>`;
    } else {
      briefResults.innerHTML = `<p>No brief generated.</p>`;
    }
  });
}

// --- Copy to Clipboard and Download as PDF (with unique IDs) ---
function enableCopyAndDownload(outputId, copyBtnId, downloadBtnId) {
  const output = document.getElementById(outputId);
  const copyBtn = document.getElementById(copyBtnId);
  const downloadBtn = document.getElementById(downloadBtnId);
  if (!output || !copyBtn || !downloadBtn) return;
  copyBtn.disabled = false;
  downloadBtn.disabled = false;
  copyBtn.onclick = () => {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = output.innerHTML;
    const text = tempDiv.textContent || tempDiv.innerText || '';
    navigator.clipboard.writeText(text.trim());
    copyBtn.innerText = '✅ Copied!';
    setTimeout(() => { copyBtn.innerText = '📋 Copy to Clipboard'; }, 1200);
  };
  downloadBtn.onclick = () => {
    const jsPDF = window.jspdf.jsPDF;
    const doc = new jsPDF();
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = output.innerHTML;
    const text = tempDiv.textContent || tempDiv.innerText || '';
    doc.setFont('helvetica');
    doc.setFontSize(13);
    doc.text(text.trim(), 10, 20, { maxWidth: 180 });
    doc.save('output.pdf');
  };
}

// Call this after each output is updated
function enableActionsAfterUpdate(outputId, copyBtnId, downloadBtnId) {
  setTimeout(() => enableCopyAndDownload(outputId, copyBtnId, downloadBtnId), 300);
}

// Patch each output area after update
// Summarization
const uploadFormEl = document.getElementById('uploadForm');
if (uploadFormEl) {
  uploadFormEl.addEventListener('submit', function () {
    enableActionsAfterUpdate('uploadSummaryOutput', 'summaryCopyBtn', 'summaryDownloadBtn');
  });
}
// Section & Act Tagging
const analyzeFormEl = document.getElementById('analyzeForm');
if (analyzeFormEl) {
  analyzeFormEl.addEventListener('submit', function () {
    enableActionsAfterUpdate('analyzeResults', 'analyzeCopyBtn', 'analyzeDownloadBtn');
  });
}
// Argument Generator
const argumentFormEl = document.getElementById('argumentForm');
if (argumentFormEl) {
  argumentFormEl.addEventListener('submit', function () {
    enableActionsAfterUpdate('argumentResults', 'argumentCopyBtn', 'argumentDownloadBtn');
  });
}
// Trend Analytics
const trendFormEl = document.getElementById('trendForm');
if (trendFormEl) {
  trendFormEl.addEventListener('submit', function () {
    enableActionsAfterUpdate('trendResults', 'trendCopyBtn', 'trendDownloadBtn');
  });
}
// Client Brief
const briefFormEl = document.getElementById('briefForm');
if (briefFormEl) {
  briefFormEl.addEventListener('submit', function () {
    enableActionsAfterUpdate('briefResults', 'briefCopyBtn', 'briefDownloadBtn');
  });
}

