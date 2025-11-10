document.getElementById("generateBtn").addEventListener("click", async () => {
  const generateBtn = document.getElementById("generateBtn");
  const fileInput = document.getElementById("fileInput");
  const files = fileInput.files;

  if (!files.length) {
    alert("Please select a folder containing code files!");
    return;
  }

  // === Hiển thị trạng thái "Generating..." ===
  generateBtn.classList.add("generating");
  generateBtn.textContent = "Generating...";
  generateBtn.disabled = true;

  // === Xóa kết quả cũ trước khi generate ===
  document.getElementById("jsonOutput").innerHTML = "";
  document.getElementById("dotOutput").textContent = "";
  document.getElementById("diagramOutput").innerHTML = "";

  // === Đọc toàn bộ file trong thư mục ===
  const fileContents = {};
  for (const file of files) {
    const text = await file.text();
    fileContents[file.webkitRelativePath] = text;
  }

  try {
    // === Gửi yêu cầu đến Flask backend ===
    const response = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ files: fileContents }),
    });

    const data = await response.json();

    // === Kiểm tra lỗi ===
    if (data.error) {
      document.getElementById("jsonOutput").textContent = "";
      document.getElementById("dotOutput").textContent = "Error: " + data.error;
      document.getElementById("diagramOutput").innerHTML = "";
      return;
    }

    // === Hiển thị JSON cho từng file ===
    const jsonOutput = document.getElementById("jsonOutput");
    jsonOutput.innerHTML = "";

    const filesData = data.json_response.files;
    for (const [filename, info] of Object.entries(filesData)) {
      const section = document.createElement("div");
      section.innerHTML = `
        <h3 class="text-lg font-bold mt-3 mb-1 text-pink-400">${filename}</h3>
        <pre class="bg-gray-800 p-3 rounded-lg text-left text-sm">${JSON.stringify(
          info,
          null,
          2
        )}</pre>
      `;
      jsonOutput.appendChild(section);
    }

    // === Hiển thị DOT & Diagram ===
    document.getElementById("dotOutput").textContent = data.dot_code;
    document.getElementById("diagramOutput").innerHTML = data.diagram;

    // === Kích hoạt nút tải JSON ===
    const jsonBlob = new Blob([JSON.stringify(data.json_response, null, 2)], {
      type: "application/json",
    });
    const jsonUrl = URL.createObjectURL(jsonBlob);

    document.getElementById("downloadJsonBtn").onclick = () => {
      const a = document.createElement("a");
      a.href = jsonUrl;
      a.download = "diagram_data.json";
      a.click();
      URL.revokeObjectURL(jsonUrl);
    };

    // === Kích hoạt nút tải Diagram (SVG) ===
    const svgBlob = new Blob([data.diagram], { type: "image/svg+xml" });
    const svgUrl = URL.createObjectURL(svgBlob);

    document.getElementById("downloadDiagramBtn").onclick = () => {
      const a = document.createElement("a");
      a.href = svgUrl;
      a.download = "diagram.svg";
      a.click();
      URL.revokeObjectURL(svgUrl);
    };
  } catch (error) {
    console.error("Error:", error);
    alert("Something went wrong while processing the folder!");
  } finally {
    // === Trả về trạng thái bình thường ===
    generateBtn.classList.remove("generating");
    generateBtn.textContent = "Generate Diagram";
    generateBtn.disabled = false;
  }
});

// === Popup Zoom Diagram ===
document.getElementById("diagramOutput").addEventListener("click", () => {
  const modal = document.getElementById("diagramModal");
  const modalDiagram = document.getElementById("modalDiagram");
  const diagramHTML = document.getElementById("diagramOutput").innerHTML;

  if (!diagramHTML.trim()) return;

  modalDiagram.innerHTML = diagramHTML;
  modal.classList.remove("hidden");
  modal.classList.add("flex");
});

document.getElementById("closeModalBtn").addEventListener("click", () => {
  const modal = document.getElementById("diagramModal");
  modal.classList.add("hidden");
  modal.classList.remove("flex");
});

document.getElementById("diagramModal").addEventListener("click", (e) => {
  if (e.target.id === "diagramModal") {
    e.target.classList.add("hidden");
    e.target.classList.remove("flex");
  }
});
