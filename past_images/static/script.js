const referenceInput = document.getElementById('referenceInput');
const targetsInput = document.getElementById('targetsInput');
const referenceLabel = document.getElementById('referenceLabel');
const targetsLabel = document.getElementById('targetsLabel');
const fileList = document.getElementById('fileList');
const uploadForm = document.getElementById('uploadForm');
const submitBtn = document.getElementById('submitBtn');
const status = document.getElementById('status');
const spinner = document.getElementById('spinner');

let modelCheckInterval = null;

// Check if models are loaded on page load
async function checkModelsReady() {
    try {
        const response = await fetch('/health');
        const health = await response.json();

        if (health.models_loaded) {
            status.className = 'status success';
            status.textContent = 'Ready! Upload images to begin.';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Process Images';
            if (modelCheckInterval) {
                clearInterval(modelCheckInterval);
                modelCheckInterval = null;
            }
        } else {
            status.className = 'status processing';
            status.textContent = 'Loading AI models... This may take 2-3 minutes on first load.';
            submitBtn.disabled = true;
            submitBtn.textContent = 'Loading models...';
        }
    } catch (error) {
        status.className = 'status error';
        status.textContent = 'Connection error. Please refresh the page.';
        submitBtn.disabled = true;
    }
}

// Start checking models on page load
window.addEventListener('DOMContentLoaded', () => {
    checkModelsReady();
    modelCheckInterval = setInterval(checkModelsReady, 5000); // Check every 5 seconds
});

referenceInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
        referenceLabel.textContent = `Selected: ${e.target.files[0].name}`;
        referenceLabel.classList.add('has-file');
    }
});

targetsInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
        targetsLabel.textContent = `Selected: ${e.target.files[0].name}`;
        targetsLabel.classList.add('has-file');

        // Re-enable submit if models are loaded
        checkModelsReady();
    }
});

uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append('reference', referenceInput.files[0]);

    for (let i = 0; i < targetsInput.files.length; i++) {
        formData.append('targets', targetsInput.files[i]);
    }

    submitBtn.disabled = true;
    spinner.style.display = 'block';
    status.className = 'status processing';
    status.textContent = 'Processing image with SAM + LaMa... This may take 1-2 minutes.';

    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            status.className = 'status success';

            let html = `<div style="text-align: center;">
                <div style="font-size: 1.2em; margin-bottom: 10px;">✓ Processing Complete!</div>
            </div>`;

            if (result.results && result.results.length > 0) {
                html += '<div style="margin-top: 20px;">';
                result.results.forEach((res, idx) => {
                    if (res.url) {
                        html += `<div style="margin: 10px 0;">
                            <a href="${res.url}" class="download-link" download="${res.output}">
                                Download ${res.original}
                            </a>
                        </div>`;
                    } else if (res.error) {
                        html += `<div style="margin: 10px 0; color: #c92a2a;">
                            ${res.original}: ${res.error}
                        </div>`;
                    }
                });
                html += '</div>';
            }

            status.innerHTML = html;
            submitBtn.disabled = false;
            spinner.style.display = 'none';
        } else {
            throw new Error(result.detail || 'Failed to process images');
        }
    } catch (error) {
        status.className = 'status error';
        status.textContent = `Error: ${error.message}`;
        submitBtn.disabled = false;
        spinner.style.display = 'none';
    }
});
