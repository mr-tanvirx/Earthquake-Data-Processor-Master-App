import json, os, threading
import pandas as pd
from pathlib import Path
import concurrent.futures

class App4Processor:
    APP_ID = "app4"
    APP_TITLE = "App 4: Batch Converter (Parquet <-> CSV)"

    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.state = {"is_running": False, "config": None}

    def log_msg(self, msg):
        self.log_queue.put(msg)

    def initialize(self, config):
        self.state['config'] = config or {}
        return {"status": "Initialized"}

    def start_page_thread(self):
        config = self.state.get('config', {})
        action = config.get('action')
        self.run_custom_action(action, config)

    def get_html_template(self):
        return """
        <div class="grid-layout">
            <div class="section-card">
                <div class="section-title">Parquet <-> CSV Batch Converter</div>
                <div class="input-group">
                    <label>Input Directory (Location of files to convert)</label>
                    <input type="text" id="app4-input-dir" placeholder="e.g., C:\\My_Data">
                </div>
                <div class="input-group">
                    <label>Output Directory (Where to save converted files)</label>
                    <input type="text" id="app4-output-dir" placeholder="e.g., C:\\My_Converted_Data">
                    <small>Directory structure is maintained automatically.</small>
                </div>
                <button class="btn-large init-btn" onclick="run_app4('p2c')" style="margin-bottom: 10px;">Convert Parquets TO CSV</button>
                <button class="btn-large init-btn" onclick="run_app4('c2p')" style="background-color: #17a2b8;">Convert CSVs TO Parquet</button>
            </div>
        </div>
        """

    def get_js_funcs(self):
        return """
        function run_app4(direction) {
            const payload = {
                action: direction,
                input_dir: document.getElementById('app4-input-dir').value,
                output_dir: document.getElementById('app4-output-dir').value
            };
            executeAppAction('app4', payload);
        }
        """

    def run_custom_action(self, action, config):
        self.state['is_running'] = True
        input_dir = config.get("input_dir")
        output_dir = config.get("output_dir")
        
        if not input_dir or not output_dir:
            self.log_msg("Error: Input and Output directories are required.")
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            return

        in_path = Path(input_dir)
        out_path = Path(output_dir)

        if not in_path.exists() or not in_path.is_dir():
            self.log_msg(f"Error: Input directory {input_dir} not found.")
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            return

        out_path.mkdir(parents=True, exist_ok=True)
        
        if action == 'p2c':
            files = list(in_path.rglob("*.parquet"))
            ext_target = '.csv'
            self.log_msg(f"Discovered {len(files)} PARQUET files. Beginning multi-threaded conversion to CSV...")
        elif action == 'c2p':
            files = list(in_path.rglob("*.csv"))
            ext_target = '.parquet'
            self.log_msg(f"Discovered {len(files)} CSV files. Beginning multi-threaded conversion to PARQUET...")
        else:
            self.log_msg("Error: Invalid action passed.")
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            return

        if not files:
            self.log_msg(f"No corresponding files found in the input directory to convert.")
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            return
        
        lock = threading.Lock()
        self.state['progress'] = 0
        self.state['total'] = len(files)
        workers = max(1, (os.cpu_count() or 4) - 2)

        def convert_task(file):
            try:
                rel_path = file.relative_to(in_path)
                dest = out_path / rel_path.with_suffix(ext_target)
                dest.parent.mkdir(parents=True, exist_ok=True)
                
                if action == 'p2c':
                    df = pd.read_parquet(file)
                    df.to_csv(dest, index=False)
                elif action == 'c2p':
                    df = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip')
                    df.to_parquet(dest, index=False)
                
                with lock:
                    self.state['progress'] += 1
                    prog = self.state['progress']
                
                self.log_msg(json.dumps({"log": f"Converted: {file.name} -> {dest.name}", "progress": prog, "total": len(files)}))
            except Exception as e:
                self.log_msg(f"Error converting {file.name}: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(convert_task, files)

        self.log_msg(f"Conversion complete. All files saved to {output_dir}")
        self.log_msg(json.dumps({"done": True, "has_more": False, "progress": len(files), "total": len(files)}))
        self.state['is_running'] = False