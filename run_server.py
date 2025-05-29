from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess
import os
import signal
import socket

status_info = {"status": "unknown", "message": "No status reported yet"}
log_messages = []


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status_info).encode())
        elif self.path == '/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"logs": log_messages}).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html_content = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Jetson Control</title>
                <style>
                    body {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        padding: 20px;
                        font-family: Arial, sans-serif;
                    }
                    h1, h2 {
                        text-align: center;
                        font-size: 5em;
                    }
                    #status {
                        margin-bottom: 50px;
                        font-size: 3em;
                    }
                    button {
                        font-size: 4em;
                        padding: 10px 30px;
                        margin-bottom: 40px;
                        cursor: pointer;
                    }
                    textarea {
                        width: 80%;
                        max-width: 600px;
                        margin-bottom: 20px;
                    }
                </style>
            </head>
            <body>
                <h1>Jetson script</h1>
                <div id="status">Loading...</div>
                <button onclick="restartCode()">Start Code</button>
                <button onclick="recordVideo()">Record</button>
                <button onclick="stopRecording()">Stop all</button>
                <h2>Logs</h2>
                <textarea id="logs" rows="20" cols="100" readonly>Loading...</textarea>
                <script>
                    function fetchStatus() {
                        fetch('/status')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('status').innerText = `Status: ${data.status}`;
                        });
                    }

                    function fetchLogs() {
                        fetch('/logs')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('logs').value = data.logs.join('\\n');
                        });
                    }

                    function restartCode() {
                        fetch('/restart', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            alert(data.message);
                            fetchStatus();
                            fetchLogs();
                        });
                    }
                    
                    function recordVideo() {
                        fetch('/record', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            alert(data.message);
                            fetchStatus();
                            fetchLogs();
                        });
                    }
                    
                    function stopRecording() {
                        fetch('/stop_recording', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            alert(data.message);
                            fetchStatus();
                            fetchLogs();
                        });
                    }
                    
                    function stopCode() {
                        fetch('/stop', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            alert(data.message);
                            fetchStatus();
                            fetchLogs();
                        });
                    }

                    fetchStatus();
                    fetchLogs();
                    setInterval(fetchStatus, 1000);
                    setInterval(fetchLogs, 1000);
                </script>
            </body>
            </html>
            '''
            self.wfile.write(html_content.encode())

    def do_POST(self):
        if self.path == '/restart':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                # Kill the existing process if it's running
                result = subprocess.run(['pgrep','-f','main.py'], stdout=subprocess.PIPE, text=True)
                if result.stdout:
                    pid = int(result.stdout.strip())
                    os.kill(pid, signal.SIGTERM)

                # Start the script again
                subprocess.Popen(['python3', 'main.py'])
                response = {'message': 'Script restarted successfully!'}
            except Exception as e:
                response = {'message': f'Error restarting script: {e}'}
                print(f"Error restarting script: {e}")

            self.wfile.write(json.dumps(response).encode())

        elif self.path == '/stop':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                # Kill the existing process if it's running
                result = subprocess.run(['pgrep','-f','main.py'], stdout=subprocess.PIPE, text=True)
                if result.stdout:
                    pid = int(result.stdout.strip())
                    os.kill(pid, signal.SIGTERM)
                response = {'message': 'Script stopped successfully!'}
            except Exception as e:
                response = {'message': f'Error stopping script: {e}'}
                print(f"Error stopping script: {e}")

            self.wfile.write(json.dumps(response).encode())

        elif self.path == '/record':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                # trigger recording
                result = subprocess.run(['pgrep','-f','SVO_record.py'], stdout=subprocess.PIPE, text=True)
                if result.stdout:
                    pid = int(result.stdout.strip())
                    os.kill(pid, signal.SIGTERM)
                subprocess.Popen(['python3', 'SVO_record.py'])
                response = {'message': 'Recording started successfully!'}
            except Exception as e:
                response = {'message': f'Error starting recording {e}'}
                print(f"Error starting recording: {e}")

            self.wfile.write(json.dumps(response).encode())

        elif self.path == '/stop_recording':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                # trigger recording
                result = subprocess.run(['pgrep','-f','SVO_record.py'], stdout=subprocess.PIPE, text=True)
                if result.stdout:
                    pid = int(result.stdout.strip())
                    os.kill(pid, signal.SIGUSR1)
                response = {'message': 'Recording stopped successfully!'}

                result = subprocess.run(['pgrep', '-f', 'main.py'], stdout=subprocess.PIPE, text=True)
                if result.stdout:
                    pid = int(result.stdout.strip())
                    os.kill(pid, signal.SIGTERM)
                response = {'message': 'Detection stopped successfully!'}

            except Exception as e:
                response = {'message': f'Error while stopping {e}'}
                print(f"Error while stopping: {e}")

            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/report_status':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            global status_info
            status_info = data
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Status updated successfully"}).encode())

        elif self.path == '/report_log':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            global log_messages
            log_messages.append(data['log'])
            # Keep only the last 100 log messages
            log_messages = log_messages[-100:]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Log updated successfully"}).encode())

    def log_message(self, format, *args):
        return

def run(server_class=HTTPServer, handler_class=MyHandler, port=8000):
    server_address = ('0.0.0.0', port)
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.0.0.1', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        pass
    finally:
        s.close()

    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on http://{local_ip}:{port}')
    httpd.serve_forever()


if __name__ == '__main__':
    run()
