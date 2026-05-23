import json, gc, shutil
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import concurrent.futures
from processor_shared import process_multi_compare

class App5Processor:
    APP_ID = "app5"
    APP_TITLE = "App 5: Compare Plots"

    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.state = {"is_running": False, "config": None}

    def log_msg(self, msg): self.log_queue.put(msg)

    def get_html_template(self):
        return """
        <div class="grid-layout" style="grid-template-columns: 1fr;">
            <div class="section-card" style="border: 2px solid #17a2b8;">
                <div class="section-title">Compare Profiles Builder</div>
                <div class="input-group"><label>Output Directory for Comparative Plots</label><input type="text" id="a5-out-dir" placeholder="C:\\EQ_Compare_Outputs"></div>
                <div id="compare-rows-container"></div>
                <button class="btn-secondary" onclick="addCompareRow()" style="background: #17a2b8; margin-top: 15px;">+ Add Event for Comparison</button>
            </div>
        </div>
        <div class="grid-layout">
            <div class="section-card">
                <div class="section-title">Filters & Spectrum Config (Applied Globally)</div>
                <label>Band Pass Filters (Hz)</label>
                <div class="filters-container" id="a5-fc"><div class="filter-row"><input type="number" class="low-cut" placeholder="Low"> to <input type="number" class="high-cut" placeholder="High"></div></div>
                <button type="button" class="btn-small" onclick="addFilterUI('a5-fc')">+ Add Filter</button>
                <label style="margin-top: 10px;">Damping Ratios (%)</label>
                <div class="damping-container" id="a5-dc"><div class="filter-row"><input type="number" class="damping-val" placeholder="e.g. 5" value="0"></div></div>
                <button type="button" class="btn-small" onclick="addDampingUI('a5-dc')">+ Add Damping</button>
            </div>
            <div class="section-card">
                <div class="section-title">Generation Settings</div>
                <div class="settings-grid" id="a5-settings">
                    <div class="input-group"><label>Draw Original Plot</label><div class="radio-group"><label><input type="radio" name="a5_orig" class="draw-orig" value="y" checked> Y</label><label><input type="radio" name="a5_orig" class="draw-orig" value="n"> N</label></div></div>
                    <div class="input-group"><label>Filtered Plots</label><div class="radio-group"><label><input type="radio" name="a5_sep" class="sep-plots" value="y" checked> Y</label><label><input type="radio" name="a5_sep" class="sep-plots" value="n"> N</label></div></div>
                    <div class="input-group"><label>Comparison Plots (Orig vs Filt)</label><div class="radio-group"><label><input type="radio" name="a5_comp" class="comp-plots" value="y" checked> Y</label><label><input type="radio" name="a5_comp" class="comp-plots" value="n"> N</label></div></div>
                    <div class="input-group">
                        <label>Response Spectrum Plots</label>
                        <div class="radio-group">
                            <label><input type="radio" name="a5_resp" class="resp-plots" value="y" onchange="document.getElementById('a5_resp_axes').style.display='block'"> Y</label>
                            <label><input type="radio" name="a5_resp" class="resp-plots" value="n" checked onchange="document.getElementById('a5_resp_axes').style.display='none'"> N</label>
                        </div>
                        <div id="a5_resp_axes" style="display:none; margin-top: 10px; padding: 10px; background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 6px;">
                            <label style="display:inline; margin-right: 10px;"><input type="checkbox" class="resp-ax-x" value="x" checked> X</label>
                            <label style="display:inline; margin-right: 10px;"><input type="checkbox" class="resp-ax-y" value="y"> Y</label>
                            <label style="display:inline;"><input type="checkbox" class="resp-ax-z" value="z"> Z</label>
                        </div>
                    </div>
                    <div class="input-group"><label>Save Automatically</label><div class="radio-group"><label><input type="radio" name="a5_save" class="save-plots" value="y"> Y</label><label><input type="radio" name="a5_save" class="save-plots" value="n" checked> N</label></div></div>
                    <div class="input-group"><label>Axis Title Font Size</label><input type="number" id="a5-axis-font" value="12"></div>
                </div>
            </div>
        </div>
        <button class="btn-large init-btn" onclick="run_app5()">Generate Comparison Plots</button>
        """

    def get_js_funcs(self):
        return """
        let compareRowCount = 0;
        function addCompareRow() {
            compareRowCount++;
            const id = compareRowCount;
            const container = document.getElementById('compare-rows-container');
            const row = document.createElement('div');
            row.className = 'compare-row';
            row.id = `cmp-row-${id}`;
            row.innerHTML = `
                <button class="remove-row-btn" onclick="document.getElementById('cmp-row-${id}').remove()">X Remove</button>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <strong style="color:var(--text-color);">Profile ${id}</strong>
                    <div style="font-size:0.85em;">
                        Load Config (from App 2): <input type="file" accept=".conf,.json" id="cmp-file-${id}" style="width:200px;" onchange="loadConfigToRow(${id})">
                    </div>
                </div>
                <div class="input-group"><label>Label/Name</label><input type="text" class="cmp-name" placeholder="e.g. Station A Data"></div>
                <div class="input-group"><label>Source Directory</label><input type="text" class="cmp-dir" placeholder="Folder path"></div>
                <div class="inline-inputs" style="margin-bottom:8px;">
                    <span>Start:</span>
                    <input type="number" id="c${id}-sh" class="cmp-dur-trig" placeholder="hh" step="any"> :
                    <input type="number" id="c${id}-sm" class="cmp-dur-trig" placeholder="mm" step="any"> :
                    <input type="number" id="c${id}-ss" class="cmp-dur-trig" placeholder="ss" step="any">
                </div>
                <div class="inline-inputs" style="margin-bottom:8px;">
                    <span>End:&nbsp;&nbsp;</span>
                    <input type="number" id="c${id}-eh" class="cmp-dur-trig" placeholder="hh" step="any"> :
                    <input type="number" id="c${id}-em" class="cmp-dur-trig" placeholder="mm" step="any"> :
                    <input type="number" id="c${id}-es" class="cmp-dur-trig" placeholder="ss" step="any">
                </div>
                <div class="inline-inputs" style="margin-bottom:8px; background: var(--tab-bg); padding: 8px; border-radius: 6px;">
                    <label style="margin: 0; margin-right: 15px; cursor:pointer;"><input type="checkbox" class="cmp-inv"> Multiply Data by -1</label>
                    <label style="margin: 0; cursor:pointer;"><input type="checkbox" class="cmp-swap"> Swap X & Y Axes</label>
                </div>
                <div class="duration-box" id="c${id}-duration">Duration: Auto (Full Segment)</div>
            `;
            container.appendChild(row);
            row.querySelectorAll('.cmp-dur-trig').forEach(el => el.addEventListener('input', () => {
                calculateDurationExact(`c${id}-sh`, `c${id}-sm`, `c${id}-ss`, `c${id}-eh`, `c${id}-em`, `c${id}-es`, `c${id}-duration`);
            }));
        }

        function loadConfigToRow(id) {
            const file = document.getElementById(`cmp-file-${id}`).files[0];
            if(!file) return;
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    let content = e.target.result;
                    let jsonStart = content.indexOf('{');
                    let jsonEnd = content.lastIndexOf('}');
                    if(jsonStart !== -1 && jsonEnd !== -1) content = content.substring(jsonStart, jsonEnd + 1);
                    const conf = JSON.parse(content);
                    const row = document.getElementById(`cmp-row-${id}`);
                    
                    row.querySelector('.cmp-dir').value = conf['target-dir'] || conf.target_dir || conf['a2-target-dir'] || "";
                    document.getElementById(`c${id}-sh`).value = conf['start-hh'] || conf.start_hh || "";
                    document.getElementById(`c${id}-sm`).value = conf['start-mm'] || conf.start_mm || "";
                    document.getElementById(`c${id}-ss`).value = conf['start-ss'] || conf.start_ss || "";
                    document.getElementById(`c${id}-eh`).value = conf['end-hh'] || conf.end_hh || "";
                    document.getElementById(`c${id}-em`).value = conf['end-mm'] || conf.end_mm || "";
                    document.getElementById(`c${id}-es`).value = conf['end-ss'] || conf.end_ss || "";
                    
                    calculateDurationExact(`c${id}-sh`, `c${id}-sm`, `c${id}-ss`, `c${id}-eh`, `c${id}-em`, `c${id}-es`, `c${id}-duration`);
                    document.getElementById('log-area').innerHTML += `> Profile ${id} loaded time and directory bounds from JSON.<br>`;
                } catch(err) { alert("Invalid config file format."); }
            };
            reader.readAsText(file);
            document.getElementById(`cmp-file-${id}`).value = ''; 
        }

        function run_app5() {
            const pane = document.getElementById('tab-app5');
            const cmpConfigs = [];
            document.querySelectorAll('.compare-row').forEach(row => {
                const id = row.id.replace('cmp-row-', '');
                cmpConfigs.push({
                    name: row.querySelector('.cmp-name').value || `Profile ${id}`,
                    target_dir: row.querySelector('.cmp-dir').value,
                    start_hh: document.getElementById(`c${id}-sh`).value,
                    start_mm: document.getElementById(`c${id}-sm`).value,
                    start_ss: document.getElementById(`c${id}-ss`).value,
                    end_hh: document.getElementById(`c${id}-eh`).value,
                    end_mm: document.getElementById(`c${id}-em`).value,
                    end_ss: document.getElementById(`c${id}-es`).value,
                    invert: row.querySelector('.cmp-inv').checked,
                    swap_xy: row.querySelector('.cmp-swap').checked
                });
            });
            const payload = {
                output_dir: document.getElementById('a5-out-dir').value || "C:/EQ_Compare_Outputs",
                compare_configs: cmpConfigs,
                filters: extractFiltersUI('a5-fc'),
                dampings: extractDampingsUI('a5-dc'),
                draw_orig: pane.querySelector('.draw-orig:checked')?.value === 'y',
                sep_plots: pane.querySelector('.sep-plots:checked')?.value === 'y',
                comp_plots: pane.querySelector('.comp-plots:checked')?.value === 'y',
                resp_plots: pane.querySelector('.resp-plots:checked')?.value === 'y',
                resp_axes: ['x','y','z'].filter(ax => pane.querySelector('.resp-ax-'+ax)?.checked),
                save_plots: pane.querySelector('.save-plots:checked')?.value === 'y',
                axis_font_size: parseInt(document.getElementById('a5-axis-font').value || 12)
            };
            executeAppWorkflow('app5', payload);
        }

        window.addEventListener('DOMContentLoaded', () => {
            addCompareRow();
            addCompareRow();
        });
        """

    def initialize(self, config):
        self.log_msg("--- APP 5: MULTI-EVENT COMPARISON ACTIVE ---")
        configs = config.get('compare_configs', [])
        if len(configs) < 2:
            self.log_msg("> Warning: Minimum 2 events required for comparison.")
            return {"status": "Error"}
        self.state['config'] = config
        return {"status": "Initialized"}

    def start_page_thread(self):
        self.state['is_running'] = True
        config = self.state['config']
        configs = config.get('compare_configs', [])
        self.state['total'] = 1
        self.state['progress'] = 0
        
        data_list = []
        target_save_dir = Path(config.get('output_dir', 'C:/EQ_Compare_Outputs'))
        target_save_dir.mkdir(parents=True, exist_ok=True)
        
        duration_tracker = None
        duration_mismatch = False
        
        for idx, conf in enumerate(configs):
            try:
                name = conf.get('name', f"Profile {idx+1}")
                tdir = Path(conf['target_dir'])
                
                sh, sm, ss = conf.get('start_hh'), conf.get('start_mm'), conf.get('start_ss')
                eh, em, es = conf.get('end_hh'), conf.get('end_mm'), conf.get('end_ss')
                has_time = all(x not in ["", None] for x in [sh, sm, ss, eh, em, es])

                if has_time:
                    start_sec = float(sh)*3600 + float(sm)*60 + float(ss)
                    end_sec = float(eh)*3600 + float(em)*60 + float(es)
                    dur = end_sec - start_sec
                    if duration_tracker is None: duration_tracker = dur
                    elif dur != duration_tracker: duration_mismatch = True
                
                dfs = []
                if tdir.exists():
                    for f in tdir.glob("*.*"):
                        try:
                            if f.suffix.lower() == '.parquet':
                                df_part = pd.read_parquet(f)
                                if df_part.shape[1] >= 4: dfs.append(df_part.iloc[:, 0:4])
                            elif f.suffix.lower() == '.csv':
                                df_part = pd.read_csv(f, sep=None, engine='python', on_bad_lines='skip')
                                if df_part.shape[1] >= 4: dfs.append(df_part.iloc[:, 0:4])
                        except Exception: pass
                        
                if not dfs:
                    self.log_msg(f"[{name}] Missing/Invalid directory data. Skipping.")
                    continue
                    
                df = pd.concat(dfs, ignore_index=True)
                df.columns = ['timestamp', 'x', 'y', 'z']
                for col in ['timestamp', 'x', 'y', 'z']: df[col] = pd.to_numeric(df[col], errors='coerce')
                df = df.dropna().sort_values('timestamp')
                df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s')
                
                if has_time:
                    base_date = df['timestamp_dt'].min().floor('D')
                    start_time_dt = base_date + pd.Timedelta(seconds=start_sec)
                    end_time_dt = base_date + pd.Timedelta(seconds=end_sec)
                    mask = (df['timestamp_dt'] >= start_time_dt) & (df['timestamp_dt'] <= end_time_dt)
                    df_segment = df[mask].copy()
                else:
                    df_segment = df.copy()
                    start_time_dt = df_segment['timestamp_dt'].min()
                
                if not df_segment.empty:
                    # Apply specific transformations
                    if conf.get('swap_xy'):
                        temp_x = df_segment['x'].copy()
                        df_segment['x'] = df_segment['y']
                        df_segment['y'] = temp_x
                        self.log_msg(f"[{name}] Swapped X and Y axes.")
                        
                    if conf.get('invert'):
                        df_segment['x'] *= -1
                        df_segment['y'] *= -1
                        df_segment['z'] *= -1
                        self.log_msg(f"[{name}] Multiplied data by -1.")
                        
                    df_segment['relative_time'] = (df_segment['timestamp_dt'] - start_time_dt).dt.total_seconds()
                    dt = np.nanmedian(np.diff(df_segment['timestamp'].values))
                    if np.isnan(dt) or dt <= 0: dt = 0.01
                    data_list.append({'name': name, 'df': df_segment, 'dt': dt})
                else:
                    self.log_msg(f"[{name}] Empty segment within requested bounds.")
                del dfs, df; gc.collect()
            except Exception as e:
                self.log_msg(f"Error loading {conf.get('name')}: {e}")

        if duration_mismatch:
            self.log_msg('<strong style="color: #ff4444;">>>> CRITICAL WARNING: Time range durations are not equal across loaded profiles! Timelines will stretch incorrectly. (Plotting Anyway)</strong>')
            
        if len(data_list) > 1:
            timestamp_mark = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            process_multi_compare(data_list, config, timestamp_mark, target_save_dir, self.log_msg)
        else:
            self.log_msg("> Failed to plot comparison. Insufficient valid datasets gathered.")
            
        self.state['progress'] = 1
        self.log_msg(json.dumps({"done": True, "has_more": False}))
        self.state['is_running'] = False