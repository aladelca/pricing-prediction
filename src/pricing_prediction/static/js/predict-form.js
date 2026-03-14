document.addEventListener("DOMContentLoaded", () => {
  setupPredictionForm();
  setupFieldGuideSearch();
});

function setupPredictionForm() {
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
}

function setupFieldGuideSearch() {
  const searchInput = document.getElementById("field-guide-search");
  const resultCount = document.getElementById("field-guide-result-count");
  const emptyState = document.getElementById("field-guide-empty");

  if (!searchInput || !resultCount || !emptyState) {
    return;
  }

  const cards = Array.from(document.querySelectorAll("[data-field-guide-card]"));
  const sections = Array.from(document.querySelectorAll("[data-field-guide-section]"));

  const applyFilter = () => {
    const query = searchInput.value.trim().toLowerCase();
    let visibleCount = 0;

    cards.forEach((card) => {
      const searchableText = (card.dataset.searchText || "").toLowerCase();
      const matches = query === "" || searchableText.includes(query);
      card.hidden = !matches;
      if (matches) {
        visibleCount += 1;
      }
    });

    sections.forEach((section) => {
      const visibleCards = section.querySelectorAll("[data-field-guide-card]:not([hidden])");
      section.hidden = visibleCards.length === 0;
    });

    resultCount.textContent = String(visibleCount);
    emptyState.hidden = visibleCount !== 0;
  };

  searchInput.addEventListener("input", applyFilter);
  applyFilter();
}
