import os
import sys
import socket
import threading
import json
import time
import datetime
from pathlib import Path
from flask import request, jsonify

try:
    import paramiko
except ImportError:
    paramiko = None
    print("Warning: paramiko is not installed. App 8 SSH features will not function.")

# Dynamically inject backend routes into the master Flask app
if '__main__' in sys.modules and hasattr(sys.modules['__main__'], 'app'):
    app = sys.modules['__main__'].app

    @app.route('/api/app8/check', methods=['POST'])
    def app8_check_availability_route():
        data = request.json
        processor = getattr(sys.modules['__main__'], 'app_processors', {}).get('app8')
        if processor: return processor.run_availability_check(data)
        return jsonify({"status": "error"}), 500

    @app.route('/api/app8/action', methods=['POST'])
    def app8_action_route():
        data = request.json
        processor = getattr(sys.modules['__main__'], 'app_processors', {}).get('app8')
        if processor: return processor.run_action(data)
        return jsonify({"status": "error"}), 500


class App8Processor:
    APP_ID = "app8"
    APP_TITLE = "App 8: Device Manager & SSH"

    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.config_file = Path("Config.txt")

    def log_msg(self, msg):
        self.log_queue.put(f"[APP 8] {msg}")

    def read_config(self):
        devices = []
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = [p.strip() for p in line.split(",")]
                        # Requires Format: DeviceName, LocalIP, Cloud1IP, Cloud2IP, Username, Password
                        if len(parts) >= 6:
                            devices.append({
                                "name": parts[0],
                                "ips": {"local": parts[1], "cloud1": parts[2], "cloud2": parts[3]},
                                "username": parts[4],
                                "password": parts[5]
                            })
        return devices

    def ping_or_ssh_check(self, ip, port=22, timeout=2.0):
        if not ip or ip.lower() in ["none", "", "null"]: return False
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True
        except (socket.timeout, socket.error):
            return False

    def run_availability_check(self, data):
        device_name = data.get("name", "Unknown Device")
        ips = data.get("ips", {})
        
        self.log_msg(f"Starting network availability sweep for {device_name}...")
        results = {}
        
        def check_and_log(label, ip):
            is_up = self.ping_or_ssh_check(ip)
            results[label] = is_up
            status_str = "ONLINE" if is_up else "OFFLINE"
            if is_up:
                self.log_msg(f"-> {device_name} | {label.upper()} ({ip}) : [SUCCESS] {status_str}")
            else:
                self.log_msg(f"-> {device_name} | {label.upper()} ({ip}) : [FAILED] {status_str}")

        threads = []
        for label, ip in ips.items():
            t = threading.Thread(target=check_and_log, args=(label, ip))
            threads.append(t)
            t.start()
            
        for t in threads: t.join()
        return jsonify({"status": "success", "results": results})

    def _download_data(self, action, device, ip, username, password):
        if not paramiko:
            self.log_msg("Error: paramiko module is not installed. Cannot execute SSH.")
            self.log_msg('{"done": true}')
            return
            
        self.log_msg(f"Initiating Download for {action.upper()} Data via {ip} on {device} (User: {username})...")
        
        # Calculate Target Time in UTC
        now_utc = datetime.datetime.utcnow()
        if action == "last_hour":
            # Current Hour Data: Fetch the current UTC hour (no subtraction)
            target_time = now_utc
        elif action == "prev_hour":
            # Previous Hour Data: Fetch the UTC hour immediately prior to the current hour
            target_time = now_utc - datetime.timedelta(hours=1)
        else:
            self.log_msg("Error: Unknown time action.")
            self.log_msg('{"done": true}')
            return

        yyyy = target_time.strftime("%Y")
        mm = target_time.strftime("%m")
        dd = target_time.strftime("%d")
        hh = target_time.strftime("%H")
        
        # Dynamically inject username into the remote path
        remote_dir = f"/home/{username}/Desktop/acc_project/archive/{yyyy}/{mm}/{dd}"
        file_prefix = f"{dd}:{mm}:{yyyy} {hh}"
        
        self.log_msg(f"Target Time (UTC): {target_time.strftime('%Y-%m-%d %H:00:00')}")
        self.log_msg(f"Target Directory: {remote_dir}")

        # Create structured local directories: downloads / Device_Name / YYYY-MM-DD
        safe_device_name = device.replace(' ', '_')
        date_folder = target_time.strftime("%Y-%m-%d")
        local_dir = Path("downloads") / safe_device_name / date_folder
        
        try:
            local_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.log_msg(f"[ERROR] Could not create local directory {local_dir}: {str(e)}")
            self.log_msg('{"done": true}')
            return
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            self.log_msg(f"Establishing SSH connection to {ip}...")
            
            client.connect(
                ip, 
                username=username, 
                password=password, 
                timeout=10,
                auth_timeout=10,
                banner_timeout=10,
                look_for_keys=False,
                allow_agent=False
            ) 
            
            sftp = client.open_sftp()
            
            downloaded = False
            for ext in ['.parquet', '.csv']:
                remote_path = f"{remote_dir}/{file_prefix}{ext}"
                
                # Replace spaces and colons so the OS doesn't reject the filename
                safe_prefix = file_prefix.replace(' ', '_').replace(':', '-')
                local_file_name = f"{safe_device_name}_{safe_prefix}{ext}"
                local_path = str(local_dir / local_file_name)
                
                try:
                    self.log_msg(f"Searching for {remote_path}...")
                    sftp.stat(remote_path)
                    self.log_msg(f"File located! Downloading to {local_path}...")
                except IOError:
                    # File doesn't exist on the remote pi, check the next extension
                    continue
                
                try:
                    sftp.get(remote_path, local_path)
                    self.log_msg(f"[SUCCESS] Download completed: {local_path}")
                    downloaded = True
                    break
                except Exception as e:
                    self.log_msg(f"[ERROR] Failed to save file locally: {str(e)}")
                    break
                    
            if not downloaded:
                self.log_msg(f"[FAILED] No matching CSV or Parquet file found for hour {hh} on {device}.")
                
            sftp.close()
        except Exception as e:
            self.log_msg(f"[ERROR] SSH operation failed: {str(e)}")
        finally:
            client.close()
            self.log_msg(f"Download Sequence Complete for {device}.")
            self.log_msg('{"done": true}') # Instructs frontend Live Status Engine to stop listening

    def run_action(self, data):
        action = data.get("action")
        device_name = data.get("device")
        ip = data.get("ip")
        
        if not ip or ip.lower() in ["none", "null", ""]:
            self.log_msg(f"Error: Invalid IP address selected for {device_name}.")
            return jsonify({"status": "error", "message": "Invalid IP"})
            
        if action == "live":
            self.log_msg(f"Opening Live Recording stream for {device_name} via {ip}:5000...")
            url = f"http://{ip}:5000"
            return jsonify({"status": "success", "url": url})
            
        elif action in ["last_hour", "prev_hour"]:
            # Dynamically fetch credentials for the requested device from config
            devices = self.read_config()
            username, password = None, None
            for d in devices:
                if d['name'] == device_name:
                    username = d.get('username')
                    password = d.get('password')
                    break
                    
            if not username or not password:
                self.log_msg(f"[ERROR] Credentials not found for {device_name} in Config.txt. Ensure it has 6 columns.")
                return jsonify({"status": "error", "message": "Missing credentials"})
                
            # Process SSH in a background thread
            threading.Thread(target=self._download_data, args=(action, device_name, ip, username, password)).start()
            return jsonify({"status": "success"})
            
        return jsonify({"status": "error", "message": "Unknown action"})

    def get_html_template(self):
        devices = self.read_config()
        
        cards_html = ""
        for dev in devices:
            safe_name = dev['name'].replace(' ', '')
            dev_json = json.dumps(dev['ips']).replace('"', '&quot;')
            
            cards_html += f"""
            <div class="app8-card">
                <h3>{dev['name']}</h3>
                
                <div class="app8-ip-row">
                    <span>Local: <span style="opacity:0.7; font-family: monospace;">{dev['ips']['local']}</span></span>
                    <span class="app8-status-badge" id="badge-{safe_name}-local">UNKNOWN</span>
                </div>
                <div class="app8-ip-row">
                    <span>Cloud 1: <span style="opacity:0.7; font-family: monospace;">{dev['ips']['cloud1']}</span></span>
                    <span class="app8-status-badge" id="badge-{safe_name}-cloud1">UNKNOWN</span>
                </div>
                <div class="app8-ip-row">
                    <span>Cloud 2: <span style="opacity:0.7; font-family: monospace;">{dev['ips']['cloud2']}</span></span>
                    <span class="app8-status-badge" id="badge-{safe_name}-cloud2">UNKNOWN</span>
                </div>
                
                <div class="app8-actions">
                    <select id="select-ip-{safe_name}" class="app8-select">
                        <option value="{dev['ips']['local']}">Use Local IP ({dev['ips']['local']})</option>
                        <option value="{dev['ips']['cloud1']}">Use Cloud 1 IP ({dev['ips']['cloud1']})</option>
                        <option value="{dev['ips']['cloud2']}">Use Cloud 2 IP ({dev['ips']['cloud2']})</option>
                    </select>
                    
                    <button class="app8-btn btn-check-avail" onclick="checkDeviceAvailability('{dev['name']}', '{safe_name}', {dev_json}, this)">Check Availability</button>
                    <button class="app8-btn app8-btn-outline" onclick="doAction('live', '{dev['name']}', 'select-ip-{safe_name}')">See Live Recording</button>
                    <button class="app8-btn app8-btn-outline" onclick="doAction('last_hour', '{dev['name']}', 'select-ip-{safe_name}')">Download Current Hour Data</button>
                    <button class="app8-btn app8-btn-outline" onclick="doAction('prev_hour', '{dev['name']}', 'select-ip-{safe_name}')">Download Previous Hour Data</button>
                </div>
            </div>
            """

        return f"""
        <style>
            .app8-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
            .app8-card {{ background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); color: var(--text-color); transition: background-color 0.3s, border-color 0.3s, color 0.3s; }}
            .app8-card h3 {{ margin: 0 0 12px 0; color: #4ade80; font-size: 1.2rem; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; text-align:center; }}
            .app8-ip-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 0.9rem; color: var(--text-color); }}
            .app8-status-badge {{ padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; background: var(--tab-bg); color: var(--text-color); min-width: 60px; text-align: center; }}
            .app8-actions {{ margin-top: 15px; display: flex; flex-direction: column; gap: 8px; }}
            .app8-select {{ width: 100%; padding: 8px; background: var(--input-bg); color: var(--input-text); border: 1px solid var(--border-color); border-radius: 4px; font-size: 0.85rem; transition: background-color 0.3s, color 0.3s, border-color 0.3s; }}
            .app8-btn {{ width: 100%; padding: 10px; background-color: #0e639c; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500; font-size: 0.9rem; transition: 0.2s; }}
            .app8-btn:hover {{ background-color: #1177bb; }}
            .app8-btn-outline {{ background-color: transparent; border: 1px solid #0e639c; color: #0e639c; }}
            body.dark-mode .app8-btn-outline {{ color: #60a5fa; }}
            .app8-btn-outline:hover {{ background-color: rgba(14, 99, 156, 0.2); color: white; }}
            .app8-btn:disabled {{ background-color: #555; cursor: not-allowed; opacity: 0.6; }}
            
            .app8-btn-global {{
                width: 100%; padding: 15px; background-color: #d97706; color: white; font-size: 1.2rem; 
                font-weight: bold; border: none; border-radius: 8px; margin-bottom: 25px; cursor: pointer;
            }}
            .app8-btn-global:hover {{ background-color: #b45309; }}
        </style>

        <div id="form-app8">
            <button class="app8-btn-global" onclick="checkAllStations()">Check Availability of ALL Stations</button>
            <div class="app8-grid">
                {cards_html}
            </div>
        </div>

        <script>
            async function checkAllStations() {{
                const btns = document.querySelectorAll('.btn-check-avail');
                for (let btn of btns) {{
                    btn.click();
                    await new Promise(r => setTimeout(r, 400));
                }}
            }}
            
            async function doAction(action, deviceName, selectId) {{
                const ip = document.getElementById(selectId).value;
                
                // Triggers the existing global Live Status Engine defined in master_app.py
                document.getElementById('log-area').innerHTML = "";
                if (typeof listenToStream === 'function') {{
                    listenToStream();
                }}
                
                try {{
                    const response = await fetch('/api/app8/action', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ action: action, device: deviceName, ip: ip }})
                    }});
                    const data = await response.json();
                    if (data.status === 'success' && data.url) {{
                        window.open(data.url, '_blank');
                    }}
                }} catch (err) {{
                    console.error("Action error:", err);
                }}
            }}

            async function checkDeviceAvailability(name, idSafeName, ips, btn) {{
                const origText = btn.innerText;
                btn.innerText = "Checking...";
                btn.disabled = true;

                const labels = ['local', 'cloud1', 'cloud2'];
                labels.forEach(lbl => {{
                    const badge = document.getElementById(`badge-${{idSafeName}}-${{lbl}}`);
                    if (badge) {{
                        badge.innerText = "TESTING";
                        badge.style.background = "#d97706";
                        badge.style.color = "#fff";
                    }}
                }});

                try {{
                    const response = await fetch('/api/app8/check', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ name: name, ips: ips }})
                    }});
                    
                    const data = await response.json();
                    if (data.status === 'success') {{
                        const res = data.results;
                        labels.forEach(lbl => {{
                            const badge = document.getElementById(`badge-${{idSafeName}}-${{lbl}}`);
                            if (badge) {{
                                const isUp = res[lbl];
                                badge.innerText = isUp ? "ONLINE" : "OFFLINE";
                                badge.style.background = isUp ? "#16a34a" : "#dc2626";
                                badge.style.color = "#fff";
                            }}
                        }});
                    }}
                }} catch (err) {{
                    labels.forEach(lbl => {{
                        const badge = document.getElementById(`badge-${{idSafeName}}-${{lbl}}`);
                        if (badge) {{
                            badge.innerText = "ERROR";
                            badge.style.background = "#dc2626";
                            badge.style.color = "#fff";
                        }}
                    }});
                }} finally {{
                    btn.innerText = origText;
                    btn.disabled = false;
                }}
            }}
        </script>
        """