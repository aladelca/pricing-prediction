document.addEventListener("DOMContentLoaded", () => {
  const urlTextarea = document.getElementById("image-urls-text");
  const fileInput = document.getElementById("image-files");
  const urlCount = document.getElementById("image-url-count");
  const fileCount = document.getElementById("image-file-count");
  const selectedFiles = document.getElementById("selected-files");
  const previewGrid = document.getElementById("upload-preview-grid");

  if (!urlTextarea || !fileInput || !urlCount || !fileCount || !selectedFiles || !previewGrid) {
    return;
  }

  const renderUrlCount = () => {
    const count = urlTextarea.value
      .split(/\n+/)
      .map((entry) => entry.trim())
      .filter(Boolean).length;
    urlCount.textContent = String(count);
  };

  const renderFilePreview = () => {
    const files = Array.from(fileInput.files || []);
    fileCount.textContent = String(files.length);
    selectedFiles.innerHTML = "";
    previewGrid.innerHTML = "";

    files.forEach((file) => {
      const nameChip = document.createElement("span");
      nameChip.className = "selected-file";
      nameChip.textContent = file.name;
      selectedFiles.appendChild(nameChip);

      const preview = document.createElement("figure");
      preview.className = "upload-preview";

      const image = document.createElement("img");
      image.src = URL.createObjectURL(file);
      image.alt = file.name;
      image.addEventListener("load", () => URL.revokeObjectURL(image.src), { once: true });

      const caption = document.createElement("span");
      caption.textContent = file.name;

      preview.appendChild(image);
      preview.appendChild(caption);
      previewGrid.appendChild(preview);
    });
  };

  urlTextarea.addEventListener("input", renderUrlCount);
  fileInput.addEventListener("change", renderFilePreview);
  renderUrlCount();
});
