import os
import sys
import queue
import threading
import subprocess
import webbrowser
from flask import Flask, render_template, jsonify, request, Response
from cleaner import clean_pdf_file

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'wuolah-cleaner-secret'

# Workspace base path (defaults to project path)
WORKSPACE_PATH = "/home/anlaim/Documentos/Proyectos/Limpiador_Wuolah"
CLEANED_DIR_NAME = "Limpiados"
CLEANED_PATH = os.path.join(WORKSPACE_PATH, CLEANED_DIR_NAME)

# Dynamic active workspaces
ACTIVE_WORKSPACE_PATH = WORKSPACE_PATH
ACTIVE_CLEANED_PATH = CLEANED_PATH

# Thread-safe queue for real-time log streaming
log_queue = queue.Queue()

# Global statistics
stats = {
    "files_processed": 0,
    "pages_removed": 0,
    "borders_removed": 0,
    "watermarks_removed": 0,
    "texts_redacted": 0,
    "total_size_saved_mb": 0.0
}

def push_log(message):
    log_queue.put(message)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/local-files', methods=['GET'])
def get_local_files():
    """Scans the active workspace directory for PDF files to display in the UI."""
    pdf_files = []
    try:
        for f in os.listdir(ACTIVE_WORKSPACE_PATH):
            # Scan only PDF files (and ignore potential clean backups from manual runs)
            if f.endswith('.pdf') and not f.endswith('_Clean_Perfect.pdf') and not f.startswith('upload_temp_') and not f.startswith('temp_'):
                full_path = os.path.join(ACTIVE_WORKSPACE_PATH, f)
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                
                # Check if it has a cleaned counterpart
                is_cleaned = False
                cleaned_counterpart = os.path.join(ACTIVE_CLEANED_PATH, f)
                if os.path.exists(cleaned_counterpart):
                    is_cleaned = True
                    
                pdf_files.append({
                    "name": f,
                    "size_mb": f"{size_mb:.2f}",
                    "is_cleaned": is_cleaned,
                    "path": full_path
                })
        # Sort alphabetically
        pdf_files.sort(key=lambda x: x['name'].lower())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    return jsonify({
        "files": pdf_files,
        "active_workspace": ACTIVE_WORKSPACE_PATH
    })

@app.route('/api/change-folder', methods=['POST'])
def change_folder():
    """Opens a native graphical folder selection dialog using Zenity on Linux."""
    global ACTIVE_WORKSPACE_PATH, ACTIVE_CLEANED_PATH
    
    try:
        push_log("[INFO] Abriendo selector de carpeta nativo en tu escritorio Linux...")
        # Run Zenity directory selection dialog
        result = subprocess.run(
            ["zenity", "--file-selection", "--directory", "--title=Seleccionar Carpeta con PDFs de Wuolah", f"--filename={ACTIVE_WORKSPACE_PATH}/"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            selected_path = result.stdout.strip()
            if selected_path and os.path.isdir(selected_path):
                ACTIVE_WORKSPACE_PATH = selected_path
                ACTIVE_CLEANED_PATH = os.path.join(ACTIVE_WORKSPACE_PATH, CLEANED_DIR_NAME)
                os.makedirs(ACTIVE_CLEANED_PATH, exist_ok=True)
                
                push_log(f"[SUCCESS] Carpeta activa de limpieza cambiada a: {ACTIVE_WORKSPACE_PATH}")
                return jsonify({
                    "success": True, 
                    "active_workspace": ACTIVE_WORKSPACE_PATH,
                    "active_cleaned": ACTIVE_CLEANED_PATH
                })
                
        push_log("[INFO] Selección de carpeta cancelada por el usuario.")
        return jsonify({"success": False, "message": "Selección cancelada"})
        
    except Exception as e:
        push_log(f"[ERROR] No se pudo abrir el selector Zenity: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clean-local', methods=['POST'])
def clean_local():
    """Cleans a list of selected local files in a background thread."""
    data = request.json or {}
    filenames = data.get('files', [])
    overwrite = data.get('overwrite', False)
    
    if not filenames:
        return jsonify({"error": "No se han seleccionado archivos para limpiar."}), 400
        
    def process_thread():
        global stats
        push_log(f"[START] Iniciando procesamiento en lote de {len(filenames)} archivos (Sobrescribir: {overwrite})")
        
        for name in filenames:
            input_path = os.path.join(ACTIVE_WORKSPACE_PATH, name)
            if not os.path.exists(input_path):
                push_log(f"[ERROR] El archivo no existe: {name}")
                continue
                
            orig_size = os.path.getsize(input_path)
            
            # Determine output path
            if overwrite:
                output_path = os.path.join(ACTIVE_WORKSPACE_PATH, f"temp_{name}")
            else:
                output_path = os.path.join(ACTIVE_CLEANED_PATH, name)
                
            try:
                # Run the surgical cleaning engine
                result = clean_pdf_file(input_path, output_path, log_callback=push_log)
                
                # If overwrite, replace original with temp
                if overwrite:
                    os.replace(output_path, input_path)
                    final_path = input_path
                else:
                    final_path = output_path
                    
                new_size = os.path.getsize(final_path)
                saved_mb = (orig_size - new_size) / (1024 * 1024)
                if saved_mb < 0: 
                    saved_mb = 0.0 # Prevent negative stats if metadata/compresses are equal
                    
                # Update global stats
                stats["files_processed"] += 1
                stats["pages_removed"] += result["deleted_pages"]
                stats["borders_removed"] += result["borders_removed"]
                stats["watermarks_removed"] += result["watermarks_removed"]
                stats["texts_redacted"] += result["texts_redacted"]
                stats["total_size_saved_mb"] += saved_mb
                
                push_log(f"[PROGRESS] {name} limpiado exitosamente. Ahorrado: {saved_mb:.2f} MB.")
                
            except Exception as e:
                push_log(f"[ERROR] Error al procesar {name}: {str(e)}")
                if overwrite and os.path.exists(os.path.join(ACTIVE_WORKSPACE_PATH, f"temp_{name}")):
                    try:
                        os.remove(os.path.join(ACTIVE_WORKSPACE_PATH, f"temp_{name}"))
                    except:
                        pass
                        
        push_log("[FINISHED] Todos los archivos en lote han sido procesados.")
        
    threading.Thread(target=process_thread).start()
    return jsonify({"status": "processing"})

@app.route('/api/upload-and-clean', methods=['POST'])
def upload_and_clean():
    """Handles drag and drop files uploaded via browser, cleans them, and saves them in the output folder."""
    global stats
    if 'files[]' not in request.files:
        return jsonify({"error": "No se enviaron archivos."}), 400
        
    uploaded_files = request.files.getlist('files[]')
    overwrite = request.form.get('overwrite', 'false') == 'true'
    
    if not uploaded_files or uploaded_files[0].filename == '':
        return jsonify({"error": "No se seleccionaron archivos válidos."}), 400
        
    # We will process them in a background thread to allow instant SSE log streaming
    def process_uploads():
        global stats
        push_log(f"[START] Iniciando procesamiento de {len(uploaded_files)} archivos subidos por Drag & Drop")
        
        for f in uploaded_files:
            original_filename = f.filename
            push_log(f"[INFO] Recibido archivo subido: {original_filename}")
            
            # Save uploaded file temporarily in the active workspace
            temp_input_path = os.path.join(ACTIVE_WORKSPACE_PATH, f"upload_temp_{original_filename}")
            f.save(temp_input_path)
            orig_size = os.path.getsize(temp_input_path)
            
            # Determine output destination
            if overwrite:
                # If overwriting, it replaces the file with the same name in active workspace
                output_path = os.path.join(ACTIVE_WORKSPACE_PATH, original_filename)
            else:
                output_path = os.path.join(ACTIVE_CLEANED_PATH, original_filename)
                
            try:
                # Surgical clean
                result = clean_pdf_file(temp_input_path, output_path, log_callback=push_log)
                
                # Cleanup temp upload file
                os.remove(temp_input_path)
                
                new_size = os.path.getsize(output_path)
                saved_mb = (orig_size - new_size) / (1024 * 1024)
                if saved_mb < 0:
                    saved_mb = 0.0
                    
                # Update stats
                stats["files_processed"] += 1
                stats["pages_removed"] += result["deleted_pages"]
                stats["borders_removed"] += result["borders_removed"]
                stats["watermarks_removed"] += result["watermarks_removed"]
                stats["texts_redacted"] += result["texts_redacted"]
                stats["total_size_saved_mb"] += saved_mb
                
                push_log(f"[PROGRESS] {original_filename} procesado e integrado exitosamente.")
                
            except Exception as e:
                push_log(f"[ERROR] Error al procesar subida {original_filename}: {str(e)}")
                if os.path.exists(temp_input_path):
                    try:
                        os.remove(temp_input_path)
                    except:
                        pass
                        
        push_log("[FINISHED] Todos los archivos arrastrados han sido procesados.")
        
    threading.Thread(target=process_uploads).start()
    return jsonify({"status": "processing"})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Gets the global statistics of PDF cleaning."""
    return jsonify({
        "files_processed": stats["files_processed"],
        "pages_removed": stats["pages_removed"],
        "borders_removed": stats["borders_removed"],
        "watermarks_removed": stats["watermarks_removed"],
        "texts_redacted": stats["texts_redacted"],
        "total_size_saved_mb": f"{stats['total_size_saved_mb']:.2f}"
    })

@app.route('/api/open-folder', methods=['POST'])
def open_folder():
    data = request.json or {}
    use_cleaned_dir = data.get('cleaned_dir', True)
    
    target_path = ACTIVE_CLEANED_PATH if use_cleaned_dir else ACTIVE_WORKSPACE_PATH
    
    if not os.path.exists(target_path):
        os.makedirs(target_path, exist_ok=True)
        
    try:
        # Popen is non-blocking and safe from non-zero exit code crashes
        subprocess.Popen(["xdg-open", target_path])
        return jsonify({"success": True})
    except Exception as e:
        # Fallback to webbrowser module which is extremely reliable for files URI
        try:
            import webbrowser
            webbrowser.open("file://" + os.path.abspath(target_path))
            return jsonify({"success": True})
        except Exception as fallback_err:
            return jsonify({"error": f"OS launch failed: {str(e)}. Fallback failed: {str(fallback_err)}"}), 500

@app.route('/api/stream-logs')
def stream_logs():
    """Streams server side console logs in real time to the frontend UI terminal using Server-Sent Events (SSE)."""
    def event_stream():
        # Yield a connection confirmation immediately
        yield "data: [CONNECTED] Conexión establecida con el servidor de logs.\n\n"
        while True:
            try:
                # Block for 2 seconds waiting for new log messages
                msg = log_queue.get(timeout=2.0)
                yield f"data: {msg}\n\n"
            except queue.Empty:
                # Periodic keep-alive ping to prevent connection timeout
                yield "data: [PING]\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

def start_browser():
    """Automatically launches the user's browser in a background thread once the server starts."""
    time.sleep(1.0)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    # Ensure cleaned folder exists
    os.makedirs(CLEANED_PATH, exist_ok=True)
    
    # Run browser auto-start thread
    import time
    threading.Thread(target=start_browser, daemon=True).start()
    
    # Start the local flask server
    print("Iniciando Limpiador de Wuolah en http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False)
