const video = document.getElementById('video');
const canvas = document.getElementById('canvas'); // offscreen only
const captureBtn = document.getElementById('capture');
const generateBtn = document.getElementById('generate');
const printBtn = document.getElementById('print');
const statusEl = document.getElementById('status');
const tray = document.getElementById('tray');

let mediaStream = null;
let lastImages = [];
let lastCaptureDataURL = null;

function setStatus(t, warn=false) {
  statusEl.textContent = t;
  statusEl.classList.toggle('warn', warn);
}
function enable(el, on) { el.disabled = !on; }

async function requestCamera() {
  try {
    setStatus('Requesting camera…');

    // First, request permission with basic constraints
    let constraints = {
      video: {
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      },
      audio: false
    };

    mediaStream = await navigator.mediaDevices.getUserMedia(constraints);

    // After getting permission, enumerate devices to find external camera
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(d => d.kind === 'videoinput');

    console.log('Available cameras:', videoDevices.map(d => d.label));

    // If multiple cameras, try to use an external one
    if (videoDevices.length > 1) {
      const externalCamera = videoDevices.find(d =>
        d.label && (
          d.label.toLowerCase().includes('usb') ||
          d.label.toLowerCase().includes('external') ||
          d.label.toLowerCase().includes('webcam')
        )
      );

      if (externalCamera && externalCamera.deviceId) {
        // Stop current stream and request the external camera
        mediaStream.getTracks().forEach(t => t.stop());

        constraints.video = {
          deviceId: { exact: externalCamera.deviceId },
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        };
        mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
        console.log('Using external camera:', externalCamera.label);
      }
    }

    video.srcObject = mediaStream;
    enable(captureBtn, true);
    setStatus('Ready to capture');
  } catch (e) {
    console.error('Camera error:', e);
    setStatus(`Camera error: ${e.message}`, true);
    enable(captureBtn, false);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  requestCamera();
});
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && !mediaStream) requestCamera();
});

function captureFrame() {
  const vw = video.videoWidth || 1280;
  const vh = video.videoHeight || 720;
  canvas.width = vw;
  canvas.height = vh;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, vw, vh);

  // Convert to blob instead of data URL for efficiency
  canvas.toBlob((blob) => {
    lastCaptureDataURL = blob;

    // Create object URL for preview
    const previewURL = URL.createObjectURL(blob);
    const first = tray.children[0];
    if (first) {
      first.innerHTML = '';
      const img = document.createElement('img');
      img.src = previewURL;
      first.appendChild(img);
    }

    enable(generateBtn, true);
    setStatus('Captured - ready to generate');
  }, 'image/jpeg', 0.95);
}

function renderTrayFromServer(images) {
  // images[0] should be the server-saved original;
  // we replace the first tile with the server URL to keep consistency.
  console.log(`[RENDER] Rendering ${images.length} images`);
  const urls = images.map(x => x.url);
  for (let i = 0; i < 5; i++) {
    const div = tray.children[i];
    if (!div) continue;
    div.innerHTML = '';
    if (urls[i]) {
      const img = document.createElement('img');
      img.src = urls[i] + `?t=${Date.now()}`;
      console.log(`[RENDER] Setting image ${i}: ${urls[i]}`);
      div.appendChild(img);
    }
  }
}

async function generateImages() {
  if (!lastCaptureDataURL) return;
  setStatus('Generating…');
  enable(generateBtn, false);
  enable(printBtn, false);

  // Send as FormData with blob instead of JSON with data URL
  const formData = new FormData();
  formData.append('image', lastCaptureDataURL, 'capture.jpg');

  // Start generation
  const res = await fetch('/api/generate/start', {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    setStatus('Generation failed', true);
    enable(generateBtn, true);
    return;
  }
  const payload = await res.json();
  const sessionId = payload.session_id;
  lastImages = payload.images || [];
  renderTrayFromServer(lastImages);

  setStatus(`Generating… (1/5)`);

  // Poll for progress
  const pollInterval = setInterval(async () => {
    try {
      const statusRes = await fetch(`/api/generate/status/${sessionId}`);
      if (!statusRes.ok) {
        clearInterval(pollInterval);
        setStatus('Generation failed', true);
        enable(generateBtn, true);
        return;
      }

      const status = await statusRes.json();

      console.log(`[POLL] Received status: ${status.completed}/${status.total}, images: ${status.images?.length || 0}`);

      // Always update if we have images (even if same count, URLs might have changed)
      if (status.images && status.images.length > 0) {
        console.log(`[POLL] Updating with ${status.images.length} images`);
        lastImages = status.images;
        renderTrayFromServer(lastImages);
      }

      setStatus(`Generating… (${status.completed}/${status.total})`);

      if (status.status === 'completed') {
        console.log('[POLL] Generation completed');
        clearInterval(pollInterval);
        setStatus('Generated');
        enable(printBtn, true);
      }
    } catch (err) {
      console.error('Polling error:', err);
      clearInterval(pollInterval);
      setStatus('Generation failed', true);
      enable(generateBtn, true);
    }
  }, 1000); // Poll every second
}

async function printImages() {
  if (!lastImages.length) return;
  setStatus('Sending to printer…');
  const res = await fetch('/api/print', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths: lastImages.map(x => x.path) })
  });
  if (!res.ok) {
    setStatus('Print failed', true);
    return;
  }
  setStatus('Print submitted');
}

captureBtn.addEventListener('click', captureFrame);
generateBtn.addEventListener('click', generateImages);
printBtn.addEventListener('click', printImages);

window.addEventListener('beforeunload', () => {
  if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
});
