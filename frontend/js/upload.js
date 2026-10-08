/* KitchenIQ — Upload JS */
const API = window.API_URL;
const token = localStorage.getItem('token');

if (!token) window.location.href = 'login.html';

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const uploadBtn = document.getElementById('uploadBtn');
const alertBox = document.getElementById('alertBox');

let selectedFile = null;

function showAlert(type, msg) {
    alertBox.innerHTML = `
        <div class="kiq-alert kiq-alert-${type}" style="margin-bottom: 16px;">
            <i class="fa-solid fa-${type === 'success' ? 'circle-check' : 'circle-exclamation'}"></i>
            <div>${msg}</div>
        </div>`;
}

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag'));

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag');
    if (e.dataTransfer.files.length) {
        handleFile(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length) handleFile(fileInput.files[0]);
});

function handleFile(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
        showAlert('danger', 'Only CSV files are allowed.');
        return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = (file.size / 1024).toFixed(1) + ' KB';
    fileInfo.style.display = 'block';
}

uploadBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="kiq-spinner"></span> Uploading...';

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const res = await fetch(API + '/api/upload/csv', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token },
            body: formData,
        });
        const data = await res.json();

        if (!res.ok) throw new Error(data.error || 'Upload failed');

        showAlert('success',
            `<strong>${data.message}</strong><br>
             Created: ${data.created}, Failed: ${data.failed}`);

        setTimeout(() => window.location.href = 'dashboard.html', 1500);
    } catch (err) {
        showAlert('danger', err.message);
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Upload';
    }
});