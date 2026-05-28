const state = {
  models: [],
  currentJobId: null,
  pollTimer: null,
};

const els = {
  apiStatus: document.querySelector("#apiStatus"),
  form: document.querySelector("#generateForm"),
  imageInput: document.querySelector("#imageInput"),
  fileSummary: document.querySelector("#fileSummary"),
  dropzone: document.querySelector("#dropzone"),
  engineSelect: document.querySelector("#engineSelect"),
  formatSelect: document.querySelector("#formatSelect"),
  engineNote: document.querySelector("#engineNote"),
  generateButton: document.querySelector("#generateButton"),
  refreshButton: document.querySelector("#refreshButton"),
  jobStatus: document.querySelector("#jobStatus"),
  jobId: document.querySelector("#jobId"),
  jobMode: document.querySelector("#jobMode"),
  jobEngine: document.querySelector("#jobEngine"),
  jobUpdated: document.querySelector("#jobUpdated"),
  downloadButton: document.querySelector("#downloadButton"),
  deleteButton: document.querySelector("#deleteButton"),
  cleanupButton: document.querySelector("#cleanupButton"),
  storageText: document.querySelector("#storageText"),
  storageMeter: document.querySelector("#storageMeter"),
  errorText: document.querySelector("#errorText"),
};

init();

function init() {
  bindEvents();
  refreshAll();
}

function bindEvents() {
  els.form.addEventListener("submit", onGenerate);
  els.imageInput.addEventListener("change", updateFileSummary);
  els.engineSelect.addEventListener("change", updateEngineSelection);
  els.refreshButton.addEventListener("click", refreshAll);
  els.deleteButton.addEventListener("click", deleteCurrentJob);
  els.cleanupButton.addEventListener("click", cleanupJobs);

  ["dragenter", "dragover"].forEach((eventName) => {
    els.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      els.dropzone.classList.add("dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    els.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      els.dropzone.classList.remove("dragging");
    });
  });

  els.dropzone.addEventListener("drop", (event) => {
    els.imageInput.files = event.dataTransfer.files;
    updateFileSummary();
  });
}

async function refreshAll() {
  await Promise.all([loadModels(), loadStorage(), checkHealth()]);
}

async function checkHealth() {
  try {
    await api("/health");
    setApiStatus("API online", true);
  } catch {
    setApiStatus("API offline", false);
  }
}

async function loadModels() {
  state.models = await api("/v1/models");
  els.engineSelect.replaceChildren(
    ...state.models.map((model) => {
      const option = document.createElement("option");
      option.value = model.name;
      option.textContent = `${model.display_name} (${model.purpose})`;
      return option;
    }),
  );
  updateEngineSelection();
}

async function loadStorage() {
  const storage = await api("/v1/storage");
  const used = formatBytes(storage.used_bytes);
  const max = formatBytes(storage.max_bytes);
  const percent = storage.max_bytes ? Math.min(100, (storage.used_bytes / storage.max_bytes) * 100) : 0;
  els.storageText.textContent = `${used} of ${max}`;
  els.storageMeter.style.width = `${percent}%`;
}

function updateEngineSelection() {
  const model = selectedModel();
  if (!model) {
    els.engineNote.textContent = "No engines are available.";
    return;
  }
  els.engineNote.textContent = [model.description, model.quality_notes, model.storage_notes].filter(Boolean).join(" ");

  const currentFormat = els.formatSelect.value;
  els.formatSelect.replaceChildren(
    ...model.output_formats.map((format) => {
      const option = document.createElement("option");
      option.value = format;
      option.textContent = format.toUpperCase();
      return option;
    }),
  );
  if (model.output_formats.includes(currentFormat)) {
    els.formatSelect.value = currentFormat;
  }
}

function selectedModel() {
  return state.models.find((model) => model.name === els.engineSelect.value);
}

function updateFileSummary() {
  const files = Array.from(els.imageInput.files || []);
  if (!files.length) {
    els.fileSummary.textContent = "PNG, JPEG, or WebP";
    return;
  }
  const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
  els.fileSummary.textContent = `${files.length} selected, ${formatBytes(totalBytes)}`;
}

async function onGenerate(event) {
  event.preventDefault();
  clearError();
  const files = Array.from(els.imageInput.files || []);
  if (!files.length) {
    showError("Select at least one image.");
    return;
  }

  const formData = new FormData();
  files.forEach((file) => formData.append("images", file));
  formData.append("engine", els.engineSelect.value);
  formData.append("output_format", els.formatSelect.value);

  setBusy(true);
  try {
    const accepted = await api("/v1/generations/image-to-3d", {
      method: "POST",
      body: formData,
    });
    state.currentJobId = accepted.id;
    setJobShell(accepted.id);
    startPolling();
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
    await loadStorage();
  }
}

function startPolling() {
  stopPolling();
  pollCurrentJob();
  state.pollTimer = window.setInterval(pollCurrentJob, 1000);
}

function stopPolling() {
  if (state.pollTimer) {
    window.clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

async function pollCurrentJob() {
  if (!state.currentJobId) return;
  try {
    const job = await api(`/v1/generations/${state.currentJobId}`);
    renderJob(job);
    if (["succeeded", "failed"].includes(job.status)) {
      stopPolling();
      await loadStorage();
    }
  } catch (error) {
    stopPolling();
    showError(error.message);
  }
}

function setJobShell(jobId) {
  els.jobId.textContent = jobId;
  els.jobStatus.textContent = "Queued";
  els.jobMode.textContent = "Pending";
  els.jobEngine.textContent = els.engineSelect.value;
  els.jobUpdated.textContent = "Pending";
  els.deleteButton.disabled = false;
  disableDownload();
}

function renderJob(job) {
  els.jobStatus.textContent = job.status;
  els.jobId.textContent = job.id;
  els.jobMode.textContent = job.mode;
  els.jobEngine.textContent = job.engine;
  els.jobUpdated.textContent = new Date(job.updated_at).toLocaleString();
  els.deleteButton.disabled = false;

  if (job.status === "succeeded") {
    els.downloadButton.href = `/v1/generations/${job.id}/artifact`;
    els.downloadButton.classList.remove("disabled");
    els.downloadButton.removeAttribute("aria-disabled");
  } else {
    disableDownload();
  }

  if (job.status === "failed") {
    showError(job.error || "Generation failed.");
  }
}

async function deleteCurrentJob() {
  if (!state.currentJobId) return;
  clearError();
  try {
    await fetch(`/v1/generations/${state.currentJobId}`, { method: "DELETE" });
    stopPolling();
    state.currentJobId = null;
    resetJob();
    await loadStorage();
  } catch (error) {
    showError(error.message);
  }
}

async function cleanupJobs() {
  clearError();
  try {
    await api("/v1/maintenance/cleanup", { method: "POST" });
    await loadStorage();
  } catch (error) {
    showError(error.message);
  }
}

function resetJob() {
  els.jobStatus.textContent = "Idle";
  els.jobId.textContent = "None";
  els.jobMode.textContent = "None";
  els.jobEngine.textContent = "None";
  els.jobUpdated.textContent = "None";
  els.deleteButton.disabled = true;
  disableDownload();
}

function disableDownload() {
  els.downloadButton.href = "#";
  els.downloadButton.classList.add("disabled");
  els.downloadButton.setAttribute("aria-disabled", "true");
}

function setBusy(isBusy) {
  els.generateButton.disabled = isBusy;
  els.generateButton.textContent = isBusy ? "Generating" : "Generate model";
}

function setApiStatus(text, online) {
  els.apiStatus.textContent = text;
  els.apiStatus.style.background = online ? "#e7f2ef" : "#f7e8e7";
  els.apiStatus.style.color = online ? "#0b5f59" : "#9f3a38";
}

function showError(message) {
  els.errorText.textContent = message;
}

function clearError() {
  els.errorText.textContent = "";
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      // Keep the HTTP status message.
    }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unitIndex]}`;
}
