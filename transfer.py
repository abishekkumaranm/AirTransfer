import os
import time
import requests
import zipfile
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal

class FileUploader(QThread):
    # Signals to communicate status back to the UI
    progress_updated = pyqtSignal(dict) # Contains: percent, speed, eta, bytes_sent, total_bytes
    finished = pyqtSignal(bool, str)     # success, message

    def __init__(self, filepath, ip, port):
        super().__init__()
        self.filepath = filepath
        self.ip = ip
        self.port = port
        self.running = True

    def run(self):
        if not os.path.exists(self.filepath):
            self.finished.emit(False, "File/Folder does not exist.")
            return

        is_directory = os.path.isdir(self.filepath)
        temp_zip_path = None
        upload_filepath = self.filepath
        
        # Determine upload target filename
        if is_directory:
            filename = os.path.basename(self.filepath) + ".zip"
        else:
            filename = os.path.basename(self.filepath)

        # 1. Zip compression for folder support
        if is_directory:
            try:
                temp_dir = tempfile.gettempdir()
                temp_zip_path = os.path.join(temp_dir, filename)
                print(f"[Transfer] Compressing folder: {self.filepath} -> {temp_zip_path}")
                
                with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(self.filepath):
                        for file in files:
                            full_path = os.path.join(root, file)
                            # Create relative arcname to preserve internal folder structure
                            arcname = os.path.relpath(full_path, os.path.dirname(self.filepath))
                            zipf.write(full_path, arcname)
                
                upload_filepath = temp_zip_path
            except Exception as e:
                self.finished.emit(False, f"Compression failed: {str(e)}")
                return

        # Prepare HTTP Headers
        total_size = os.path.getsize(upload_filepath)
        url = f"http://{self.ip}:{self.port}/upload"
        
        headers = {
            "file-name": filename,
            "is-folder": "true" if is_directory else "false"
        }

        start_time = time.time()
        last_update_time = start_time
        last_bytes_sent = 0
        
        # Generator function to stream the file in chunks and report progress
        def file_chunk_generator():
            nonlocal last_update_time, last_bytes_sent
            bytes_sent = 0
            chunk_size = 64 * 1024  # 64KB chunks
            
            with open(upload_filepath, 'rb') as f:
                while self.running:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    yield chunk
                    bytes_sent += len(chunk)
                    
                    # Calculate metrics every 100ms
                    now = time.time()
                    elapsed = now - last_update_time
                    if elapsed >= 0.1 or bytes_sent == total_size:
                        speed = (bytes_sent - last_bytes_sent) / (1024 * 1024) / (elapsed + 1e-6)
                        overall_elapsed = now - start_time
                        overall_speed = (bytes_sent / (1024 * 1024)) / (overall_elapsed + 1e-6)
                        percent = int((bytes_sent / total_size) * 100)
                        
                        remaining_bytes = total_size - bytes_sent
                        eta = remaining_bytes / (bytes_sent / (overall_elapsed + 1e-6)) if bytes_sent > 0 else 0
                        
                        self.progress_updated.emit({
                            "percent": percent,
                            "speed": round(overall_speed, 2),
                            "eta": int(eta),
                            "bytes_sent": bytes_sent,
                            "total_bytes": total_size
                        })
                        
                        last_update_time = now
                        last_bytes_sent = bytes_sent
                        
            if not self.running:
                raise Exception("Upload cancelled by user.")

        try:
            # Send file as raw binary stream body
            response = requests.post(url, data=file_chunk_generator(), headers=headers, timeout=(5.0, None))
            
            if response.status_code == 200:
                self.finished.emit(True, "File transferred successfully!")
            else:
                self.finished.emit(False, f"Server returned error code {response.status_code}: {response.text}")
                
        except Exception as e:
            if not self.running:
                self.finished.emit(False, "Transfer cancelled.")
            else:
                self.finished.emit(False, f"Network error: {str(e)}")
        finally:
            # Clean up temp ZIP file if created
            if temp_zip_path and os.path.exists(temp_zip_path):
                try:
                    os.remove(temp_zip_path)
                except Exception:
                    pass

    def cancel(self):
        """Cancels the active file upload."""
        self.running = False
        self.wait()
