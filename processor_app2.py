import json, gc, os
import pandas as pd
from pathlib import Path
import concurrent.futures
from processor_shared import process_and_plot_segment, parse_factor

class App2Processor:
    APP_ID = "app2"
    APP_TITLE = "App 2: Visualizing CSV Data"

    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.state = {"is_running": False, "all_stations": [], "config": None}

    def log_msg(self, msg): self.log_queue.put(msg)

    def get_html_template(self):
        return """
        <div style="display: flex; gap: 10px; margin-bottom: 20px; justify-content: flex-end;">
            <button class="btn-secondary" style="width:auto; margin:0;" onclick="exportConfigApp2()">Save Config File (.json)</button>
            <label class="btn-secondary" style="width:auto; margin:0; cursor:pointer;">
                Load Config File (.json)
                <input type="file" id="a2-config-file" style="display:none;" accept=".json,.conf" onchange="importConfigApp2(event)">
            </label>
        </div>
        <div class="grid-layout" id="form-app2">
            <div class="section-card" style="border: 2px solid #28a745;">
                <div class="section-title">Local Direct Setup</div>
                <div class="input-group"><label>Target Directory (Input & Output Area)</label><input type="text" id="a2-target-dir" placeholder="e.g., C:\\My_Direct_Folder"></div>
                <div class="input-group" style="margin-top: 15px;"><label>Custom Plot Title Base (Optional)</label><input type="text" id="a2-custom-title" placeholder="e.g., Earthquake Event 1"></div>
                
                <div class="input-group" style="margin-top: 15px;">
                    <label style="color: #007bff; font-weight: bold;">Change Plotting Unit?</label>
                    <div class="radio-group">
                        <label><input type="radio" name="a2_unit_toggle" class="change-unit" value="y" onchange="document.getElementById('a2_unit_params').style.display='block'"> Yes</label>
                        <label><input type="radio" name="a2_unit_toggle" class="change-unit" value="n" checked onchange="document.getElementById('a2_unit_params').style.display='none'"> No</label>
                    </div>
                    <div id="a2_unit_params" style="display:none; margin-top: 10px; padding: 10px; background: var(--bg-color); border: 2px dashed #007bff; border-radius: 6px;">
                        <div class="inline-inputs">
                            <label style="display:inline; margin-right:5px;">Multiplying Factor:</label>
                            <input type="text" id="a2-unit-factor" placeholder="e.g., 1/9.81" value="1/9.81" style="width: 120px; margin-right: 15px;">
                            <label style="display:inline; margin-right:5px;">New Unit Name:</label>
                            <input type="text" id="a2-unit-name" placeholder="e.g., g" value="g" style="width: 80px;">
                        </div>
                        <small style="display:block; margin-top:5px; color:#17a2b8;">Data columns will be factored and axis titles securely overwritten.</small>
                    </div>
                </div>
            </div>
            <div class="section-card">
                <div class="section-title">Time Range Configuration</div>
                <div class="input-group">
                    <label>Extract & Plot Range (hh:mm:ss)</label>
                    <div class="inline-inputs">
                        <span>From</span>
                        <input type="number" id="a2-sh" class="a2-dt" placeholder="hh" min="0" max="23"> :
                        <input type="number" id="a2-sm" class="a2-dt" placeholder="mm" min="0" max="59"> :
                        <input type="number" id="a2-ss" class="a2-dt" placeholder="ss" min="0" step="any">
                    </div>
                    <div class="inline-inputs" style="margin-top: 10px;">
                        <span>To</span>&nbsp;&nbsp;&nbsp;&nbsp;
                        <input type="number" id="a2-eh" class="a2-dt" placeholder="hh" min="0" max="23"> :
                        <input type="number" id="a2-em" class="a2-dt" placeholder="mm" min="0" max="59"> :
                        <input type="number" id="a2-es" class="a2-dt" placeholder="ss" min="0" step="any">
                    </div>
                    <div class="duration-box" id="a2-duration">Duration: Auto (Full Segment)</div>
                </div>
            </div>
            <div class="section-card">
                <div class="section-title">Filters & Spectrum Config</div>
                <label>Band Pass Filters (Hz)</label>
                <div class="filters-container" id="a2-fc"><div class="filter-row"><input type="number" class="low-cut" placeholder="Low"> to <input type="number" class="high-cut" placeholder="High"></div></div>
                <button type="button" class="btn-small" onclick="addFilterUI('a2-fc')">+ Add Filter</button>
                <label style="margin-top: 10px;">Damping Ratios (%)</label>
                <div class="damping-container" id="a2-dc"><div class="filter-row"><input type="number" class="damping-val" placeholder="e.g. 5" value="0"></div></div>
                <button type="button" class="btn-small" onclick="addDampingUI('a2-dc')">+ Add Damping</button>
            </div>
            <div class="section-card">
                <div class="section-title">Generation Settings</div>
                <div class="settings-grid" id="a2-settings">
                    <div class="input-group" style="grid-column: span 2;">
                        <label>Keep ALL Data as CSVs</label>
                        <div class="radio-group"><label><input type="radio" name="a2_csv" class="keep-csv" value="y"> Y</label><label><input type="radio" name="a2_csv" class="keep-csv" value="n" checked> N</label></div>
                    </div>
                    <div class="input-group"><label>Draw Original Plot</label><div class="radio-group"><label><input type="radio" name="a2_orig" class="draw-orig" value="y" checked> Y</label><label><input type="radio" name="a2_orig" class="draw-orig" value="n"> N</label></div></div>
                    <div class="input-group"><label>Mark Max & Min Values</label><div class="radio-group"><label><input type="radio" name="a2_extrema" class="mark-extrema" value="y"> Y</label><label><input type="radio" name="a2_extrema" class="mark-extrema" value="n" checked> N</label></div></div>
                    <div class="input-group"><label>Filtered Plots</label><div class="radio-group"><label><input type="radio" name="a2_sep" class="sep-plots" value="y" checked> Y</label><label><input type="radio" name="a2_sep" class="sep-plots" value="n"> N</label></div></div>
                    <div class="input-group"><label>Comparison Plots</label><div class="radio-group"><label><input type="radio" name="a2_comp" class="comp-plots" value="y" checked> Y</label><label><input type="radio" name="a2_comp" class="comp-plots" value="n"> N</label></div></div>
                    
                    <div class="input-group">
                        <label>FFT Plots (Freq vs Amp)</label>
                        <div class="radio-group">
                            <label><input type="radio" name="a2_fft" class="fft-plots" value="y" onchange="document.getElementById('a2_fft_axes').style.display='block'"> Y</label>
                            <label><input type="radio" name="a2_fft" class="fft-plots" value="n" checked onchange="document.getElementById('a2_fft_axes').style.display='none'"> N</label>
                        </div>
                        <div id="a2_fft_axes" style="display:none; margin-top: 10px; padding: 10px; background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 6px;">
                            <label style="display:inline; margin-right: 10px;"><input type="checkbox" class="fft-ax-x" value="x" checked> X</label>
                            <label style="display:inline; margin-right: 10px;"><input type="checkbox" class="fft-ax-y" value="y" checked> Y</label>
                            <label style="display:inline;"><input type="checkbox" class="fft-ax-z" value="z" checked> Z</label>
                        </div>
                    </div>

                    <div class="input-group">
                        <label>Response Spectrum Plots</label>
                        <div class="radio-group">
                            <label><input type="radio" name="a2_resp" class="resp-plots" value="y" onchange="document.getElementById('a2_resp_axes').style.display='block'"> Y</label>
                            <label><input type="radio" name="a2_resp" class="resp-plots" value="n" checked onchange="document.getElementById('a2_resp_axes').style.display='none'"> N</label>
                        </div>
                        <div id="a2_resp_axes" style="display:none; margin-top: 10px; padding: 10px; background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 6px;">
                            <label style="display:inline; margin-right: 10px;"><input type="checkbox" class="resp-ax-x" value="x" checked> X</label>
                            <label style="display:inline; margin-right: 10px;"><input type="checkbox" class="resp-ax-y" value="y"> Y</label>
                            <label style="display:inline;"><input type="checkbox" class="resp-ax-z" value="z"> Z</label>
                        </div>
                    </div>
                    
                    <div class="input-group"><label>Save Automatically</label><div class="radio-group"><label><input type="radio" name="a2_save" class="save-plots" value="y"> Y</label><label><input type="radio" name="a2_save" class="save-plots" value="n" checked> N</label></div></div>
                    <div class="input-group"><label>Axis Title Font Size</label><input type="number" id="a2-axis-font" value="12"></div>
                    <div class="input-group"><label>Main Title Font Size</label><input type="number" id="a2-title-font" value="13"></div>
                </div>
            </div>
        </div>
        <button class="btn-large init-btn" onclick="run_app2()">Initialize App 2 Processing</button>
        """

    def get_js_funcs(self):
        return """
        document.querySelectorAll('.a2-dt').forEach(el => el.addEventListener('input', () => {
            calculateDurationExact('a2-sh', 'a2-sm', 'a2-ss', 'a2-eh', 'a2-em', 'a2-es', 'a2-duration');
        }));

        function exportConfigApp2() {
            const pane = document.getElementById('tab-app2');
            const config = {
                "app": "app2",
                "target-dir": document.getElementById('a2-target-dir').value,
                "start-hh": document.getElementById('a2-sh').value,
                "start-mm": document.getElementById('a2-sm').value,
                "start-ss": document.getElementById('a2-ss').value,
                "end-hh": document.getElementById('a2-eh').value,
                "end-mm": document.getElementById('a2-em').value,
                "end-ss": document.getElementById('a2-es').value,
                "change-unit": pane.querySelector('.change-unit:checked')?.value || "n",
                "unit-factor": document.getElementById('a2-unit-factor').value || "1/9.81",
                "unit-name": document.getElementById('a2-unit-name').value || "g",
                "filters": extractFiltersUI('a2-fc'),
                "dampings": extractDampingsUI('a2-dc'),
                "draw-orig": pane.querySelector('.draw-orig:checked')?.value || "y",
                "mark-extrema": pane.querySelector('.mark-extrema:checked')?.value || "n",
                "keep-csv": pane.querySelector('.keep-csv:checked')?.value || "n",
                "sep-plots": pane.querySelector('.sep-plots:checked')?.value || "y",
                "comp-plots": pane.querySelector('.comp-plots:checked')?.value || "y",
                "fft-plots": pane.querySelector('.fft-plots:checked')?.value || "n",
                "fft-ax-x": pane.querySelector('.fft-ax-x')?.checked || false,
                "fft-ax-y": pane.querySelector('.fft-ax-y')?.checked || false,
                "fft-ax-z": pane.querySelector('.fft-ax-z')?.checked || false,
                "resp-plots": pane.querySelector('.resp-plots:checked')?.value || "y",
                "resp-ax-x": pane.querySelector('.resp-ax-x')?.checked || false,
                "resp-ax-y": pane.querySelector('.resp-ax-y')?.checked || false,
                "resp-ax-z": pane.querySelector('.resp-ax-z')?.checked || false,
                "save-plots": pane.querySelector('.save-plots:checked')?.value || "n",
                "axis-font-size": document.getElementById('a2-axis-font').value || "12",
                "title-font-size": document.getElementById('a2-title-font').value || "13",
                "custom_title_base": document.getElementById('a2-custom-title').value || "",
                "updated_titles": window._customTitles || {},
                "notes-comments": ""
            };
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(config, null, 4));
            const a = document.createElement('a');
            a.href = dataStr;
            a.download = "App2_Config.json";
            a.click();
        }

        function importConfigApp2(event) {
            const file = event.target.files[0];
            if(!file) return;
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    let content = e.target.result;
                    let jsonStart = content.indexOf('{');
                    let jsonEnd = content.lastIndexOf('}');
                    if(jsonStart !== -1 && jsonEnd !== -1) content = content.substring(jsonStart, jsonEnd + 1);
                    const conf = JSON.parse(content);
                    
                    const pane = document.getElementById('tab-app2');
                    
                    document.getElementById('a2-target-dir').value = conf['target-dir'] || conf.target_dir || conf['a2-target-dir'] || "";
                    document.getElementById('a2-sh').value = conf['start-hh'] || conf.start_hh || "";
                    document.getElementById('a2-sm').value = conf['start-mm'] || conf.start_mm || "";
                    document.getElementById('a2-ss').value = conf['start-ss'] || conf.start_ss || "";
                    document.getElementById('a2-eh').value = conf['end-hh'] || conf.end_hh || "";
                    document.getElementById('a2-em').value = conf['end-mm'] || conf.end_mm || "";
                    document.getElementById('a2-es').value = conf['end-ss'] || conf.end_ss || "";
                    document.getElementById('a2-axis-font').value = conf['axis-font-size'] || conf.axis_font_size || "12";
                    document.getElementById('a2-title-font').value = conf['title-font-size'] || conf.title_font_size || "13";
                    document.getElementById('a2-custom-title').value = conf['custom_title_base'] || "";
                    document.getElementById('a2-unit-factor').value = conf['unit-factor'] || conf.unit_factor || "1/9.81";
                    document.getElementById('a2-unit-name').value = conf['unit-name'] || conf.unit_name || "g";
                    
                    if(conf.updated_titles) {
                        window._customTitles = Object.assign(window._customTitles || {}, conf.updated_titles);
                    }
                    
                    const fc = document.getElementById('a2-fc');
                    fc.innerHTML = '';
                    if(conf.filters && conf.filters.length > 0) {
                        conf.filters.forEach(f => {
                            fc.innerHTML += `<div class="filter-row"><input type="number" step="0.1" class="low-cut" placeholder="Low" value="${f[0]}"> to <input type="number" step="0.1" class="high-cut" placeholder="High" value="${f[1]}"></div>`;
                        });
                    } else if (conf['low-cut'] !== undefined && conf['high-cut'] !== undefined) {
                        fc.innerHTML += `<div class="filter-row"><input type="number" step="0.1" class="low-cut" placeholder="Low" value="${conf['low-cut']}"> to <input type="number" step="0.1" class="high-cut" placeholder="High" value="${conf['high-cut']}"></div>`;
                    } else addFilterUI('a2-fc');
                    
                    const dc = document.getElementById('a2-dc');
                    dc.innerHTML = '';
                    if(conf.dampings && conf.dampings.length > 0) {
                        conf.dampings.forEach(d => {
                            dc.innerHTML += `<div class="filter-row"><input type="number" step="0.1" class="damping-val" placeholder="e.g. 5" value="${d * 100}"></div>`;
                        });
                    } else if (conf['damping-val'] !== undefined) {
                        dc.innerHTML += `<div class="filter-row"><input type="number" step="0.1" class="damping-val" placeholder="e.g. 5" value="${conf['damping-val']}"></div>`;
                    } else addDampingUI('a2-dc');

                    const setRadio = (cls, val) => {
                        if(val) {
                            const r = pane.querySelector(`.${cls}[value="${val}"]`);
                            if(r) r.checked = true;
                        }
                    };
                    setRadio('change-unit', conf['change-unit'] || conf.change_unit);
                    setRadio('draw-orig', conf['draw-orig'] || conf.draw_orig);
                    setRadio('mark-extrema', conf['mark-extrema'] || conf.mark_extrema);
                    setRadio('keep-csv', conf['keep-csv'] || conf.keep_csv);
                    setRadio('sep-plots', conf['sep-plots'] || conf.sep_plots);
                    setRadio('comp-plots', conf['comp-plots'] || conf.comp_plots);
                    setRadio('fft-plots', conf['fft-plots'] || conf.fft_plots);
                    setRadio('resp-plots', conf['resp-plots'] || conf.resp_plots);
                    setRadio('save-plots', conf['save-plots'] || conf.save_plots);
                    
                    if(conf['change-unit'] === 'y' || conf.change_unit === 'y' || conf.change_unit === true) {
                        document.getElementById('a2_unit_params').style.display='block';
                    } else {
                        document.getElementById('a2_unit_params').style.display='none';
                    }
                    
                    if(conf.hasOwnProperty('fft-ax-x')) pane.querySelector('.fft-ax-x').checked = conf['fft-ax-x'];
                    if(conf.hasOwnProperty('fft-ax-y')) pane.querySelector('.fft-ax-y').checked = conf['fft-ax-y'];
                    if(conf.hasOwnProperty('fft-ax-z')) pane.querySelector('.fft-ax-z').checked = conf['fft-ax-z'];

                    if(conf.hasOwnProperty('resp-ax-x')) pane.querySelector('.resp-ax-x').checked = conf['resp-ax-x'];
                    if(conf.hasOwnProperty('resp-ax-y')) pane.querySelector('.resp-ax-y').checked = conf['resp-ax-y'];
                    if(conf.hasOwnProperty('resp-ax-z')) pane.querySelector('.resp-ax-z').checked = conf['resp-ax-z'];

                    if((conf['fft-plots'] === 'y' || conf.fft_plots === 'y')) document.getElementById('a2_fft_axes').style.display='block';
                    else document.getElementById('a2_fft_axes').style.display='none';

                    if((conf['resp-plots'] === 'y' || conf.resp_plots === 'y')) document.getElementById('a2_resp_axes').style.display='block';
                    else document.getElementById('a2_resp_axes').style.display='none';
                    
                    calculateDurationExact('a2-sh', 'a2-sm', 'a2-ss', 'a2-eh', 'a2-em', 'a2-es', 'a2-duration');
                    document.getElementById('log-area').innerHTML += `> App 2 Config JSON loaded successfully.<br>`;
                } catch(err) { alert("Invalid config file formatting."); }
            };
            reader.readAsText(file);
            document.getElementById('a2-config-file').value = ''; 
        }

        function run_app2() {
            const pane = document.getElementById('tab-app2');
            const payload = {
                target_dir: document.getElementById('a2-target-dir').value,
                start_hh: document.getElementById('a2-sh').value,
                start_mm: document.getElementById('a2-sm').value,
                start_ss: document.getElementById('a2-ss').value,
                end_hh: document.getElementById('a2-eh').value,
                end_mm: document.getElementById('a2-em').value,
                end_ss: document.getElementById('a2-es').value,
                filters: extractFiltersUI('a2-fc'),
                dampings: extractDampingsUI('a2-dc'),
                custom_title_base: document.getElementById('a2-custom-title').value,
                change_unit: pane.querySelector('.change-unit:checked')?.value === 'y',
                unit_factor: document.getElementById('a2-unit-factor').value,
                unit_name: document.getElementById('a2-unit-name').value,
                draw_orig: pane.querySelector('.draw-orig:checked')?.value === 'y',
                mark_extrema: pane.querySelector('.mark-extrema:checked')?.value === 'y',
                keep_csv: pane.querySelector('.keep-csv:checked')?.value === 'y',
                sep_plots: pane.querySelector('.sep-plots:checked')?.value === 'y',
                comp_plots: pane.querySelector('.comp-plots:checked')?.value === 'y',
                fft_plots: pane.querySelector('.fft-plots:checked')?.value === 'y',
                fft_axes: ['x','y','z'].filter(ax => pane.querySelector('.fft-ax-'+ax)?.checked),
                resp_plots: pane.querySelector('.resp-plots:checked')?.value === 'y',
                resp_axes: ['x','y','z'].filter(ax => pane.querySelector('.resp-ax-'+ax)?.checked),
                save_plots: pane.querySelector('.save-plots:checked')?.value === 'y',
                axis_font_size: parseInt(document.getElementById('a2-axis-font').value || 12),
                title_font_size: parseInt(document.getElementById('a2-title-font').value || 13)
            };
            executeAppWorkflow('app2', payload);
        }
        """

    def initialize(self, config):
        target_dir = Path(config['target_dir'])
        if not target_dir.exists():
            self.log_msg("--- APP 2 ERROR: Target Directory does not exist! ---")
            return {"status": "Error"}
            
        self.log_msg("--- APP 2: VISUALIZING CSV/PARQUET DATA ACTIVE ---")
        
        stations = [d.name for d in target_dir.iterdir() if d.is_dir()]
        if not stations: stations = ['Root']
            
        self.log_msg(f"Discovered {len(stations)} valid directories to process.")
        
        sh, sm, ss = config.get('start_hh'), config.get('start_mm'), config.get('start_ss')
        eh, em, es = config.get('end_hh'), config.get('end_mm'), config.get('end_ss')
        
        has_time = all(x not in ["", None] for x in [sh, sm, ss, eh, em, es])
        config['has_time_range'] = has_time
        
        self.state['all_stations'] = stations
        self.state['config'] = config
        return {"status": "Initialized"}

    def start_page_thread(self):
        self.state['is_running'] = True
        config = self.state['config']
        tasks = self.state['all_stations']
        self.state['total'] = len(tasks)
        self.state['progress'] = 0
        
        workers = max(1, (os.cpu_count() or 4) - 2)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(self.process_task, stat, config) for stat in tasks]
            concurrent.futures.wait(futures)

        self.log_msg(json.dumps({"done": True, "has_more": False}))
        self.state['is_running'] = False

    def process_task(self, station, config):
        try:
            target_dir = Path(config['target_dir'])
            station_dir = target_dir if station == 'Root' else target_dir / station
            if not station_dir.exists(): return
            
            dfs = []
            for f in station_dir.glob("*.*"):
                try:
                    if f.suffix.lower() == '.parquet':
                        df_part = pd.read_parquet(f)
                        if df_part.shape[1] >= 4: dfs.append(df_part.iloc[:, 0:4])
                    elif f.suffix.lower() == '.csv':
                        df_part = pd.read_csv(f, sep=None, engine='python', on_bad_lines='skip')
                        if df_part.shape[1] >= 4: dfs.append(df_part.iloc[:, 0:4])
                except Exception as e:
                    self.log_msg(f"[{station}] Skipping unreadable file {f.name}: {e}")
                    
            if not dfs: 
                self.log_msg(f"[{station}] No valid data extracted.")
                return
                
            df = pd.concat(dfs, ignore_index=True)
            df.columns = ['timestamp', 'x', 'y', 'z']
            for col in ['timestamp', 'x', 'y', 'z']: df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.dropna(subset=['timestamp', 'x', 'y', 'z'])
            
            if df.empty:
                self.log_msg(f"[{station}] Data was empty after parsing to numerics.")
                return

            df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s')
            
            if config.get('has_time_range'):
                base_date = df['timestamp_dt'].min().floor('D')
                start_time_dt = base_date + pd.Timedelta(hours=int(config['start_hh']), minutes=int(config['start_mm']), seconds=float(config['start_ss']))
                end_time_dt = base_date + pd.Timedelta(hours=int(config['end_hh']), minutes=int(config['end_mm']), seconds=float(config['end_ss']))
                
                # Handling Midnight Rollover / Day crossing
                if (df['timestamp_dt'].min() - start_time_dt).total_seconds() > 12 * 3600:
                    start_time_dt += pd.Timedelta(days=1)

                if end_time_dt < start_time_dt:
                    end_time_dt += pd.Timedelta(days=1)

                mask = (df['timestamp_dt'] >= start_time_dt) & (df['timestamp_dt'] <= end_time_dt)
                df_segment = df[mask].copy().sort_values('timestamp_dt')
                event_str = base_date.strftime("%Y-%m-%d") + f"_{int(config['start_hh']):02d}-{int(config['start_mm']):02d}-{int(float(config['start_ss'])):02d}"
            else:
                df_segment = df.copy().sort_values('timestamp_dt')
                start_time_dt = df_segment['timestamp_dt'].min()
                end_time_dt = df_segment['timestamp_dt'].max()
                event_str = start_time_dt.strftime("%Y-%m-%d_%H-%M-%S")
            
            if not df_segment.empty:
                if config.get('change_unit'):
                    factor = parse_factor(config.get('unit_factor', '1.0'))
                    df_segment['x'] *= factor
                    df_segment['y'] *= factor
                    df_segment['z'] *= factor
                    self.log_msg(f"[{station}] Applied custom unit factor: {factor} ({config.get('unit_name', 'g')})")
                    
                process_and_plot_segment(df_segment, config, event_str, station, station_dir, start_time_dt, end_time_dt, self.log_msg)
            else:
                self.log_msg(f"[{station}] Data found, but nothing existed inside the requested time window.")
            
            del dfs, df, df_segment; gc.collect()
            
        except Exception as e:
            self.log_msg(f"[{station}] Error: {e}")
        finally:
            self.state['progress'] += 1