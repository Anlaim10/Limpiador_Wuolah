/* ==========================================================================
   WUOLAH CLEANER PRO - REACTIVE FRONTEND LOGIC
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM ELEMENTS ---
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const filesList = document.getElementById('files-list');
    const localFilesCount = document.getElementById('local-files-count');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const overwriteToggle = document.getElementById('overwrite-toggle');
    
    const btnCleanSelected = document.getElementById('btn-clean-selected');
    const btnOpenFolder = document.getElementById('btn-open-folder');
    const btnChangeFolder = document.getElementById('btn-change-folder');
    const btnRefresh = document.getElementById('btn-refresh');
    const btnClearConsole = document.getElementById('btn-clear-console');
    
    const activeFolderDisplay = document.getElementById('active-folder-display');
    const consoleOutput = document.getElementById('console-output');
    const autoscrollCheckbox = document.getElementById('autoscroll-checkbox');
    
    // Stats Cards Elements
    const statFiles = document.getElementById('stat-files');
    const statPages = document.getElementById('stat-pages');
    const statWatermarks = document.getElementById('stat-watermarks');
    const statSize = document.getElementById('stat-size');

    let localFiles = [];
    let isProcessing = false;

    // --- INITIALIZATION ---
    fetchLocalFiles();
    updateStats();
    setupSSE();

    // Listen to overwrite toggle changes for real-time console feedback
    overwriteToggle.addEventListener('change', (e) => {
        if (e.target.checked) {
            appendConsoleLine("[SISTEMA] Modo Sobrescribir: ACTIVO. Los archivos originales del proyecto serán reemplazados quirúrgicamente.");
        } else {
            appendConsoleLine("[SISTEMA] Modo Sobrescribir: INACTIVO. Las copias limpias se guardarán en la subcarpeta '/Limpiados'.");
        }
    });

    // --- SSE LOG STREAMING CONNECTION ---
    function setupSSE() {
        const eventSource = new EventSource('/api/stream-logs');
        
        eventSource.onmessage = (event) => {
            const data = event.data;
            
            // Skip keep-alive ping events
            if (data === '[PING]') return;
            
            appendConsoleLine(data);
            
            // Handle job lifecycle logs to trigger interface reactions
            if (data.includes('[START]')) {
                isProcessing = true;
                setControlsDisabled(true);
            } else if (data.includes('[FINISHED]')) {
                isProcessing = false;
                setControlsDisabled(false);
                fetchLocalFiles();
                updateStats();
            } else if (data.includes('[PROGRESS]')) {
                // If a file finishes processing, pull files and stats dynamically
                fetchLocalFiles();
                updateStats();
            }
        };

        eventSource.onerror = (err) => {
            console.error("SSE connection error, retrying...", err);
            // Reconnection is automatically handled by the browser for EventSource
        };
    }

    // --- CONSOLE RENDERER & CLASS MAPPER ---
    function appendConsoleLine(message) {
        const line = document.createElement('div');
        line.className = 'console-line';
        
        // Match specific brackets to apply appropriate coloring classes
        if (message.startsWith('[SISTEMA]') || message.startsWith('[START]')) {
            line.classList.add('system');
        } else if (message.startsWith('[INFO]')) {
            line.classList.add('info');
        } else if (message.startsWith('[ERROR]')) {
            line.classList.add('error');
        } else if (message.startsWith('[AD]')) {
            line.classList.add('ad');
        } else if (message.startsWith('[BORDER]')) {
            line.classList.add('border');
        } else if (message.startsWith('[WATERMARK]')) {
            line.classList.add('watermark');
        } else if (message.startsWith('[TEXT]')) {
            line.classList.add('text');
        } else if (message.startsWith('[SUCCESS]') || message.startsWith('[FINISHED]')) {
            line.classList.add('success');
        } else if (message.startsWith('[PROGRESS]')) {
            line.classList.add('success');
        }
        
        line.textContent = message;
        consoleOutput.appendChild(line);
        
        // Auto scroll to bottom if checkbox checked
        if (autoscrollCheckbox.checked) {
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }
    }

    // --- CONTROLS DISABLER ---
    function setControlsDisabled(disabled) {
        btnCleanSelected.disabled = disabled || getSelectedFiles().length === 0;
        btnRefresh.disabled = disabled;
        fileInput.disabled = disabled;
        selectAllCheckbox.disabled = disabled;
        overwriteToggle.disabled = disabled;
        
        // Adjust drag and drop zone appearance if disabled
        if (disabled) {
            dropZone.style.opacity = '0.5';
            dropZone.style.pointerEvents = 'none';
        } else {
            dropZone.style.opacity = '1';
            dropZone.style.pointerEvents = 'all';
        }
    }

    // --- FETCH LOCAL FILES ---
    async function fetchLocalFiles() {
        if (isProcessing) return;
        
        try {
            const response = await fetch('/api/local-files');
            const data = await response.json();
            
            if (data.files) {
                localFiles = data.files;
                renderLocalFiles();
            }
            if (data.active_workspace) {
                activeFolderDisplay.textContent = data.active_workspace;
                activeFolderDisplay.title = data.active_workspace;
            }
        } catch (err) {
            appendConsoleLine(`[ERROR] No se pudo obtener la lista de archivos: ${err.message}`);
        }
    }

    // --- RENDER LOCAL FILES LIST ---
    function renderLocalFiles() {
        filesList.innerHTML = '';
        selectAllCheckbox.checked = false;
        
        if (localFiles.length === 0) {
            filesList.innerHTML = `
                <div class="empty-list-state">
                    <i class="fa-solid fa-face-smile-wink"></i>
                    <p>No se encontraron archivos PDF en el directorio de trabajo.</p>
                </div>
            `;
            localFilesCount.textContent = '0 archivos';
            btnCleanSelected.disabled = true;
            return;
        }
        
        localFilesCount.textContent = `${localFiles.length} archivo${localFiles.length > 1 ? 's' : ''}`;
        
        localFiles.forEach(file => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.dataset.filename = file.name;
            
            item.innerHTML = `
                <div class="file-info-col">
                    <label class="checkbox-container">
                        <input type="checkbox" class="file-checkbox" data-filename="${file.name}">
                        <span class="checkmark"></span>
                        <div class="pdf-icon-wrapper"><i class="fa-solid fa-file-pdf"></i></div>
                        <span class="file-name" title="${file.name}">${file.name}</span>
                    </label>
                </div>
                <div class="file-meta-col">
                    <span class="file-size">${file.size_mb} MB</span>
                    ${file.is_cleaned ? 
                        '<span class="clean-badge cleaned"><i class="fa-solid fa-circle-check"></i> Limpio</span>' : 
                        '<span class="clean-badge pending"><i class="fa-regular fa-circle"></i> Pendiente</span>'
                    }
                </div>
            `;
            
            filesList.appendChild(item);
        });
        
        // Re-attach checkbox events
        document.querySelectorAll('.file-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const item = e.target.closest('.file-item');
                if (e.target.checked) {
                    item.classList.add('selected');
                } else {
                    item.classList.remove('selected');
                }
                updateCleanButtonState();
            });
        });
        
        updateCleanButtonState();
    }

    // --- GET SELECTED FILES ---
    function getSelectedFiles() {
        const checkboxes = document.querySelectorAll('.file-checkbox:checked');
        return Array.from(checkboxes).map(cb => cb.dataset.filename);
    }

    // --- UPDATE CLEAN BUTTON STATE ---
    function updateCleanButtonState() {
        const selected = getSelectedFiles();
        btnCleanSelected.disabled = isProcessing || selected.length === 0;
        
        // Count how many are selected to update button label
        if (selected.length > 0) {
            btnCleanSelected.innerHTML = `<i class="fa-solid fa-bolt"></i> Limpiar Seleccionados (${selected.length})`;
        } else {
            btnCleanSelected.innerHTML = `<i class="fa-solid fa-bolt"></i> Limpiar Seleccionados`;
        }
    }

    // --- SELECT ALL CHECKBOX ---
    selectAllCheckbox.addEventListener('change', (e) => {
        const checked = e.target.checked;
        document.querySelectorAll('.file-checkbox').forEach(cb => {
            cb.checked = checked;
            const item = cb.closest('.file-item');
            if (checked) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
        updateCleanButtonState();
    });

    // --- CLEAN SELECTED BUTTON EVENT ---
    btnCleanSelected.addEventListener('click', async () => {
        const selected = getSelectedFiles();
        if (selected.length === 0 || isProcessing) return;
        
        setControlsDisabled(true);
        
        try {
            const response = await fetch('/api/clean-local', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    files: selected,
                    overwrite: overwriteToggle.checked
                })
            });
            
            const data = await response.json();
            if (data.error) {
                appendConsoleLine(`[ERROR] ${data.error}`);
                setControlsDisabled(false);
            }
        } catch (err) {
            appendConsoleLine(`[ERROR] No se pudo conectar con el backend: ${err.message}`);
            setControlsDisabled(false);
        }
    });

    // --- OPEN FOLDER BUTTON EVENT ---
    btnOpenFolder.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/open-folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cleaned_dir: !overwriteToggle.checked // if not overwriting, open 'Limpiados' folder
                })
            });
            const data = await response.json();
            if (data.error) {
                appendConsoleLine(`[ERROR] No se pudo abrir la carpeta en Linux: ${data.error}`);
            } else {
                appendConsoleLine(`[INFO] Abriendo carpeta en el explorador de Linux.`);
            }
        } catch (err) {
            appendConsoleLine(`[ERROR] Error al intentar abrir la carpeta: ${err.message}`);
        }
    });

    // --- CHANGE ACTIVE FOLDER BUTTON EVENT ---
    btnChangeFolder.addEventListener('click', async () => {
        if (isProcessing) return;
        
        try {
            const response = await fetch('/api/change-folder', {
                method: 'POST'
            });
            const data = await response.json();
            if (data.success) {
                // Instantly fetch files from the new active directory
                fetchLocalFiles();
                updateStats();
            } else if (data.error) {
                appendConsoleLine(`[ERROR] No se pudo cambiar la carpeta activa: ${data.error}`);
            }
        } catch (err) {
            appendConsoleLine(`[ERROR] Error al cambiar la carpeta: ${err.message}`);
        }
    });

    // --- DRAG AND DROP EVENTS ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('dragover');
        }, false);
    });

    dropZone.addEventListener('drop', async (e) => {
        if (isProcessing) return;
        
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length === 0) return;
        
        // Filter out non-PDF files
        const pdfFiles = Array.from(files).filter(f => f.name.endsWith('.pdf'));
        if (pdfFiles.length === 0) {
            appendConsoleLine("[ERROR] Solo se admiten archivos en formato PDF.");
            return;
        }
        
        setControlsDisabled(true);
        
        const formData = new FormData();
        pdfFiles.forEach(file => {
            formData.append('files[]', file);
        });
        formData.append('overwrite', overwriteToggle.checked);
        
        try {
            const response = await fetch('/api/upload-and-clean', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (data.error) {
                appendConsoleLine(`[ERROR] ${data.error}`);
                setControlsDisabled(false);
            }
        } catch (err) {
            appendConsoleLine(`[ERROR] Error en la subida drag & drop: ${err.message}`);
            setControlsDisabled(false);
        }
    });

    // --- REFRESH BUTTON EVENT ---
    btnRefresh.addEventListener('click', () => {
        if (isProcessing) return;
        fetchLocalFiles();
        updateStats();
        appendConsoleLine("[INFO] Lista de archivos actualizada.");
    });

    // --- CLEAR CONSOLE EVENT ---
    btnClearConsole.addEventListener('click', () => {
        consoleOutput.innerHTML = `
            <div class="console-line system">[SISTEMA] Consola limpiada por el usuario. Listo para procesar.</div>
        `;
    });

    // --- UPDATE GLOBAL STATISTICS ---
    async function updateStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            // Render with gorgeous visual numbers updates
            animateStatValue(statFiles, data.files_processed);
            animateStatValue(statPages, data.pages_removed);
            animateStatValue(statWatermarks, parseInt(data.borders_removed) + parseInt(data.watermarks_removed));
            animateStatValue(statSize, parseFloat(data.total_size_saved_mb), true);
            
        } catch (err) {
            console.error("Failed to fetch statistics", err);
        }
    }

    // Gorgeous stats counter animation
    function animateStatValue(element, targetValue, isFloat = false) {
        const startValue = isFloat ? parseFloat(element.textContent) : parseInt(element.textContent);
        if (startValue === targetValue) return;
        
        const duration = 800; // ms
        const startTime = performance.now();
        
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Ease out quad formula
            const easeProgress = progress * (2 - progress);
            
            const currentValue = startValue + (targetValue - startValue) * easeProgress;
            
            if (isFloat) {
                element.textContent = currentValue.toFixed(2);
            } else {
                element.textContent = Math.floor(currentValue);
            }
            
            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                if (isFloat) {
                    element.textContent = targetValue.toFixed(2);
                } else {
                    element.textContent = targetValue;
                }
            }
        }
        
        requestAnimationFrame(update);
    }
});
