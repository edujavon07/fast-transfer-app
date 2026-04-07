import os
import socket
import threading
import traceback

# Kivy for Android UI
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.core.window import Window
from kivy.utils import platform

# ==========================================
# 1. FOOLPROOF ENVIRONMENT & IMPORTS
# ==========================================
IMPORT_ERROR = None
app_fastapi = None
DATA_DIR = ""

try:
    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, FileResponse
    import aiofiles
    import pyqrcode
    import png  # Requires the 'pypng' library

    # ==========================================
    # 2. FASTAPI SERVER LOGIC
    # ==========================================
    app_fastapi = FastAPI()

    HTML_GUI = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Fast Transfer</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background-color: #F2F2F7; margin: 0; padding: 20px; }
            .container { background: white; padding: 25px 20px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); max-width: 500px; margin: 0 auto 20px auto; text-align: center; }
            h2 { margin-top: 0; color: #1C1C1E; font-size: 22px; }
            p { color: #8E8E93; font-size: 14px; margin-bottom: 20px; }
            input[type="file"] { display: none; }
            .btn { padding: 14px 20px; border-radius: 12px; font-weight: 600; font-size: 16px; display: block; width: 100%; box-sizing: border-box; cursor: pointer; transition: 0.2s; border: none; margin-bottom: 15px; }
            .btn-gray { background-color: #E5E5EA; color: #007AFF; }
            .btn-blue { background-color: #007AFF; color: white; }
            .btn-blue:disabled { background-color: #A1CFFF; cursor: not-allowed; }
            #statusMessage { margin-top: 15px; font-weight: 500; font-size: 14px; }
            
            .progress-wrapper { display: none; margin-top: 15px; }
            progress { width: 100%; height: 8px; border-radius: 4px; display: block; }
            progress::-webkit-progress-bar { background-color: #E5E5EA; border-radius: 4px; }
            progress::-webkit-progress-value { background-color: #34C759; border-radius: 4px; }
            .progress-text { font-size: 16px; font-weight: bold; color: #007AFF; margin-top: 8px; }
            
            .file-list { text-align: left; margin-top: 20px; }
            .file-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #E5E5EA; }
            .file-name { font-size: 15px; color: #1C1C1E; word-break: break-all; margin-right: 10px; }
            .file-size { font-size: 12px; color: #8E8E93; }
            .download-btn { background-color: #34C759; color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600; white-space: nowrap; }
        </style>
    </head>
    <body>
    <div class="container">
        <h2>Send to Android</h2>
        <p>Select files to send to the phone.</p>
        <label class="btn btn-gray" id="fileLabel">
            <input type="file" id="filePicker" multiple>
            1. Choose Files
        </label>
        <button class="btn btn-blue" id="sendBtn" onclick="startUploadProcess()">2. Send Files</button>
        
        <div class="progress-wrapper" id="progressWrapper">
            <progress id="progressBar" value="0" max="100"></progress>
            <div class="progress-text" id="progressText">0.0%</div>
        </div>
        <div id="statusMessage"></div>
    </div>
    <div class="container">
        <h2>Receive from Android</h2>
        <p>Files currently in Android's selected folder.</p>
        <button class="btn btn-gray" onclick="loadFiles()">↻ Refresh List</button>
        <div class="file-list" id="fileList"></div>
    </div>
    <script>
        const filePicker = document.getElementById('filePicker');
        const sendBtn = document.getElementById('sendBtn');
        const status = document.getElementById('statusMessage');
        const progressWrapper = document.getElementById('progressWrapper');
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        const fileLabel = document.getElementById('fileLabel');

        filePicker.addEventListener('change', function() {
            if(this.files.length > 0) {
                fileLabel.innerText = `✓ ${this.files.length} file(s) selected`;
                fileLabel.appendChild(this); 
            } else {
                fileLabel.innerHTML = `<input type="file" id="filePicker" multiple> 1. Choose Files`;
            }
        });

        // Query the server to see if the file exists and how big it is
        async function getFileStatus(filename) {
            try {
                const res = await fetch(`/status/${encodeURIComponent(filename)}`);
                if (!res.ok) throw new Error("Status check failed");
                const data = await res.json();
                return data.size; // returns 0 if not found
            } catch(e) {
                return null; // Network offline
            }
        }

        // XHR Promise wrapper to get live percentage updates
        function uploadChunk(file, offset, filename, currentFileIndex, totalFiles) {
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                const chunk = file.slice(offset);
                
                xhr.upload.addEventListener("progress", (event) => {
                    if (event.lengthComputable) {
                        const totalUploaded = offset + event.loaded;
                        const percent = ((totalUploaded / file.size) * 100).toFixed(1);
                        
                        // Calculate overall progress across all files
                        const overallPercent = ((currentFileIndex / totalFiles) * 100) + ((totalUploaded / file.size) * (100 / totalFiles));
                        
                        progressBar.value = overallPercent;
                        progressText.innerText = `${percent}% (File ${currentFileIndex + 1} of ${totalFiles})`;
                    }
                });

                xhr.addEventListener("load", () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        resolve();
                    } else {
                        reject(`Server Error ${xhr.status}: ${xhr.responseText}`);
                    }
                });

                xhr.addEventListener("error", () => reject("Network Connection Lost"));
                xhr.addEventListener("abort", () => reject("Upload Aborted"));

                xhr.open("POST", `/upload/${encodeURIComponent(filename)}`);
                xhr.setRequestHeader("X-Resume-Offset", offset.toString());
                xhr.send(chunk);
            });
        }

        async function startUploadProcess() {
            const files = filePicker.files;
            if(files.length === 0) return status.innerText = "Please choose files first!";
            
            sendBtn.disabled = true;
            progressWrapper.style.display = "block";
            status.style.color = "#1C1C1E";
            
            let currentFileIndex = 0;
            
            while(currentFileIndex < files.length) {
                const file = files[currentFileIndex];
                let isUploaded = false;
                
                // Infinite retry loop for the current file
                while(!isUploaded) {
                    try {
                        const serverSize = await getFileStatus(file.name);
                        
                        if (serverSize === null) {
                            status.innerText = `Network dropped! Retrying ${file.name} in 3 seconds...`;
                            status.style.color = "#FF3B30";
                            await new Promise(r => setTimeout(r, 3000));
                            continue;
                        }

                        // File verification: Same size means it's already complete!
                        if (serverSize === file.size) {
                            status.innerText = `Skipping: ${file.name} (Already complete!)`;
                            status.style.color = "#34C759";
                            isUploaded = true;
                            continue;
                        }
                        
                        // Resume logic
                        let offset = 0;
                        if (serverSize > 0 && serverSize < file.size) {
                            offset = serverSize;
                            const offsetMB = (offset / (1024 * 1024)).toFixed(1);
                            status.innerText = `Resuming: ${file.name} from cutoff point (${offsetMB} MB)...`;
                            status.style.color = "#FF9500"; // Orange indicating resume
                        } else {
                            status.innerText = `Sending: ${file.name}`;
                            status.style.color = "#1C1C1E";
                        }

                        // Wait for chunk to finish
                        await uploadChunk(file, offset, file.name, currentFileIndex, files.length);
                        isUploaded = true; // Mark as done to exit retry loop
                        
                    } catch(err) {
                        status.innerText = `Transfer Failed (${err}). Auto-resuming in 3 seconds...`;
                        status.style.color = "#FF3B30";
                        await new Promise(r => setTimeout(r, 3000));
                    }
                }
                currentFileIndex++;
            }
            
            status.innerText = "✅ All files transferred successfully!";
            status.style.color = "#34C759";
            sendBtn.disabled = false;
            fileLabel.innerHTML = `<input type="file" id="filePicker" multiple> 1. Choose Files`;
            setTimeout(loadFiles, 1000); 
        }

        async function loadFiles() {
            const fileList = document.getElementById('fileList');
            fileList.innerHTML = '<p style="text-align:center;">Loading...</p>';
            try {
                const response = await fetch('/files');
                const data = await response.json();
                if(data.files.length === 0) {
                    fileList.innerHTML = '<p style="text-align:center;">No files available.</p>';
                    return;
                }
                fileList.innerHTML = '';
                data.files.forEach(file => {
                    const item = document.createElement('div');
                    item.className = 'file-item';
                    item.innerHTML = `
                        <div>
                            <div class="file-name">${file.name}</div>
                            <div class="file-size">${file.size}</div>
                        </div>
                        <a href="/download/${encodeURIComponent(file.name)}" download class="download-btn">Download</a>
                    `;
                    fileList.appendChild(item);
                });
            } catch(err) {
                fileList.innerHTML = '<p style="text-align:center; color:#FF3B30;">Error loading files.</p>';
            }
        }
        window.onload = loadFiles;
    </script>
    </body>
    </html>
    """

    @app_fastapi.get("/", response_class=HTMLResponse)
    async def home_gui():
        return HTML_GUI
        
    @app_fastapi.get("/status/{filename}")
    async def file_status(filename: str):
        """Allows client to check file size before uploading to enable resuming."""
        global DATA_DIR
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.exists(file_path):
            return {"size": os.path.getsize(file_path)}
        return {"size": 0}

    @app_fastapi.post("/upload/{filename}")
    async def upload_file(filename: str, request: Request):
        global DATA_DIR
        file_path = os.path.join(DATA_DIR, filename)
        
        # Read the resume offset header. If > 0, we append to the file. Otherwise, overwrite.
        offset = int(request.headers.get("X-Resume-Offset", 0))
        mode = 'ab' if offset > 0 else 'wb'
        
        try:
            with open(file_path, mode) as f:
                async for chunk in request.stream():
                    if chunk:
                        f.write(chunk)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    @app_fastapi.get("/files")
    async def list_files():
        global DATA_DIR
        if not os.path.exists(DATA_DIR):
            return {"files": []}
        file_data = []
        for f in os.listdir(DATA_DIR):
            path = os.path.join(DATA_DIR, f)
            if os.path.isfile(path):
                size_mb = os.path.getsize(path) / (1024 * 1024)
                file_data.append({"name": f, "size": f"{size_mb:.1f} MB"})
        return {"files": file_data}

    @app_fastapi.get("/download/{filename}")
    async def download_file(filename: str):
        global DATA_DIR
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.exists(file_path):
            return FileResponse(path=file_path, filename=filename)
        return {"error": "File not found"}

except Exception as e:
    IMPORT_ERROR = traceback.format_exc()


# ==========================================
# 3. ANDROID UI LOGIC (KIVY)
# ==========================================
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class TransferApp(App):
    def build(self):
        global DATA_DIR
        
        # Default starting directory
        if platform == 'android':
            DATA_DIR = os.path.join(self.user_data_dir, "TransferData")
        else:
            DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TransferData")

        self.server_thread = None
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        if IMPORT_ERROR:
            scroll = ScrollView(size_hint=(1, 1))
            error_lbl = Label(
                text=f"CRASH LOG (Missing Dependency):\n\n{IMPORT_ERROR}", 
                font_size='14sp', color=(1, 0.2, 0.2, 1), size_hint_y=None, halign="left", valign="top"
            )
            error_lbl.bind(width=lambda *x: error_lbl.setter('text_size')(error_lbl, (error_lbl.width, None)))
            error_lbl.bind(texture_size=error_lbl.setter('size'))
            scroll.add_widget(error_lbl)
            self.layout.add_widget(scroll)
            return self.layout

        self.title_label = Label(text="Fast Transfer", font_size='28sp', bold=True, size_hint=(1, 0.1))
        self.layout.add_widget(self.title_label)
        
        self.info_label = Label(text="Connect your phone to the same Wi-Fi.", font_size='16sp', halign="center", size_hint=(1, 0.1))
        self.layout.add_widget(self.info_label)

        # The QR Code Image (Empty on startup)
        self.qr_image = Image(size_hint=(1, 0.45))
        self.layout.add_widget(self.qr_image)

        # Current Location Readout
        self.loc_label = Label(text=f"Save Folder:\n{DATA_DIR}", font_size='13sp', halign="center", color=(0.7, 0.7, 0.7, 1), size_hint=(1, 0.15))
        self.loc_label.bind(width=lambda *x: self.loc_label.setter('text_size')(self.loc_label, (self.loc_label.width, None)))
        self.layout.add_widget(self.loc_label)

        # Buttons layout
        btn_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.2))

        self.browse_btn = Button(text="Change Folder", background_color=(0.4, 0.4, 0.4, 1))
        self.browse_btn.bind(on_press=self.show_file_browser)
        btn_layout.add_widget(self.browse_btn)

        self.start_btn = Button(text="Start Server", font_size='20sp', background_color=(0, 0.5, 1, 1))
        self.start_btn.bind(on_press=self.start_server)
        btn_layout.add_widget(self.start_btn)
        
        self.layout.add_widget(btn_layout)
        return self.layout

    def show_file_browser(self, instance):
        # Create a popup UI for picking folders
        content = BoxLayout(orientation='vertical', spacing=10)
        
        # Try to open the public Downloads folder first, fallback to app sandbox
        start_path = "/storage/emulated/0/Download" if os.path.exists("/storage/emulated/0/Download") else self.user_data_dir
        
        filechooser = FileChooserListView(path=start_path, dirselect=True)
        content.add_widget(filechooser)
        
        btn_layout = BoxLayout(size_hint_y=None, height=60, spacing=10)
        cancel_btn = Button(text="Cancel", background_color=(1, 0.3, 0.3, 1))
        select_btn = Button(text="Select Folder", background_color=(0.3, 1, 0.3, 1))
        
        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(select_btn)
        content.add_widget(btn_layout)
        
        popup = Popup(title="Choose Save Location", content=content, size_hint=(0.95, 0.95))
        
        def on_select(btn):
            global DATA_DIR
            # If they tapped a folder, select it. If they just navigated into a folder, select the current path.
            selected = filechooser.selection[0] if filechooser.selection else filechooser.path
            
            # Verify Android allows writing to this folder
            if os.access(selected, os.W_OK):
                DATA_DIR = selected
                self.loc_label.text = f"Save Folder:\n{DATA_DIR}"
                popup.dismiss()
            else:
                self.info_label.text = "Error: Android blocked writing to that folder!"
                popup.dismiss()

        select_btn.bind(on_press=on_select)
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()

    def start_server(self, instance):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
        except Exception as e:
            self.info_label.text = f"Storage Error!\n\n{str(e)}"
            return

        if self.server_thread is None or not self.server_thread.is_alive():
            ip = get_local_ip()
            port = 8080
            url = f"http://{ip}:{port}"
            
            # Generate the QR Code PNG
            try:
                import pyqrcode
                qr = pyqrcode.create(url)
                qr_path = os.path.join(self.user_data_dir, "qr_code.png")
                # scale=6 creates a clean, large enough image for the iPhone to scan easily
                qr.png(qr_path, scale=6) 
                
                # Update UI Image
                self.qr_image.source = qr_path
                self.qr_image.reload()
            except Exception as e:
                self.info_label.text = f"QR Error: {str(e)}"

            self.start_btn.text = "Server is Running"
            self.start_btn.disabled = True
            self.browse_btn.disabled = True # Disable changing folders while active
            self.info_label.text = f"Scan QR code above!"
            
            self.server_thread = threading.Thread(target=self.run_uvicorn, args=(port,), daemon=True)
            self.server_thread.start()

    def run_uvicorn(self, port):
        uvicorn.run(app_fastapi, host="0.0.0.0", port=port, loop="asyncio")

if __name__ == '__main__':
    TransferApp().run()
