import json
import pandas as pd
from pathlib import Path

class App4Processor:
    APP_ID = "app4"
    APP_TITLE = "App 4: Parquet to CSV"

    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.state = {"is_running": False}

    def log_msg(self, msg):
        self.log_queue.put(msg)

    def get_html_template(self):
        return """
        <div class="grid-layout">
            <div class="section-card">
                <div class="section-title">Parquet to CSV Batch Converter</div>
                <div class="input-group">
                    <label>Input Directory (Contains .parquet files)</label>
                    <input type="text" id="app4-input-dir" placeholder="e.g., C:\\My_Parquets">
                </div>
                <div class="input-group">
                    <label>Output Directory (For .csv files)</label>
                    <input type="text" id="app4-output-dir" placeholder="e.g., C:\\My_CSVs">
                    <small>Directory structure is maintained automatically.</small>
                </div>
                <button class="btn-large init-btn" onclick="run_app4()">Convert All Parquets to CSV</button>
            </div>
        </div>
        """

    def get_js_funcs(self):
        return """
        function run_app4() {
            const payload = {
                action: 'convert',
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
        files = list(in_path.rglob("*.parquet"))
        
        if not files:
            self.log_msg("No parquet files found in the input directory.")
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            return

        self.log_msg(f"Discovered {len(files)} parquet files. Beginning conversion...")
        
        for idx, file in enumerate(files):
            try:
                rel_path = file.relative_to(in_path)
                dest_csv = out_path / rel_path.with_suffix('.csv')
                dest_csv.parent.mkdir(parents=True, exist_ok=True)
                
                df = pd.read_parquet(file)
                df.to_csv(dest_csv, index=False)
                
                progress = idx + 1
                self.log_msg(json.dumps({"log": f"Converted: {file.name}", "progress": progress, "total": len(files)}))
            except Exception as e:
                self.log_msg(f"Error converting {file.name}: {e}")

        self.log_msg(f"Conversion complete. All CSVs saved to {output_dir}")
        self.log_msg(json.dumps({"done": True, "has_more": False, "progress": len(files), "total": len(files)}))
        self.state['is_running'] = False