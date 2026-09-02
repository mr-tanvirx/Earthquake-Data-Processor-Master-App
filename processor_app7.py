# processor_app7.py

import json, threading, os, shutil
import pandas as pd
import numpy as np
from pathlib import Path
import concurrent.futures

class App7Processor:
    APP_ID = "app7"
    APP_TITLE = "App 7: EQ Auto Scanner"

    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.state = {"is_running": False, "cancel": False, "progress": 0}

    def log_msg(self, msg):
        self.log_queue.put(msg)

    def get_html_template(self):
        return """
        <div class="grid-layout" id="form-app7">
            <div class="section-card" style="border: 2px solid #e83e8c;">
                <div class="section-title">Earthquake Detection Scanner</div>
                <div class="input-group">
                    <label>Target Station Archive Directory</label>
                    <input type="text" id="a7-target-dir" placeholder="e.g., G:\\Data archive">
                </div>
                <div class="input-group" style="margin-top: 15px;">
                    <label>Archive Structure Format</label>
                    <select id="a7-format">
                        <option value="archive" selected>Data Archive (Station/archive/YYYY/MM/DD/file.parquet)</option>
                        <option value="might_have_eq">Might Have EQ (Date_Time/Station/file.parquet)</option>
                    </select>
                </div>
                
                <div style="display: flex; gap: 15px; margin-top: 15px; flex-wrap: wrap;">
                    <div class="input-group" style="flex: 1; min-width: 150px;">
                        <label>Scan Only These Axes</label>
                        <div style="display: flex; gap: 10px; margin-top: 5px;">
                            <label><input type="checkbox" id="a7-ax-x" checked> X</label>
                            <label><input type="checkbox" id="a7-ax-y" checked> Y</label>
                            <label><input type="checkbox" id="a7-ax-z" checked> Z</label>
                        </div>
                    </div>
                    <div class="input-group" style="flex: 1; min-width: 180px;">
                        <label>Threshold Mode</label>
                        <select id="a7-thresh-mode" onchange="updateA7ThreshMode()">
                            <option value="unified" selected>Unified (Same for all axes)</option>
                            <option value="individual">Individual (Separate for X, Y, Z)</option>
                        </select>
                    </div>
                    <div class="input-group" style="flex: 1; min-width: 180px;">
                        <label>Trigger Condition</label>
                        <select id="a7-axis-logic">
                            <option value="any" selected>Any selected axis met</option>
                            <option value="all">All selected axes met</option>
                        </select>
                    </div>
                </div>

                <div class="input-group" style="margin-top: 15px;">
                    <label>Output Directory for Detected EQs</label>
                    <input type="text" id="a7-out-dir" placeholder="e.g., C:\\Archive\\EQ_Found">
                </div>
                
                <div class="input-group" style="margin-top: 15px; background: rgba(0,0,0,0.1); padding: 10px; border-radius: 5px;">
                    <label>Output Artifacts</label>
                    <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-top: 5px;">
                        <label><input type="checkbox" id="a7-opt-config" checked> Gen App 2 Config</label>
                        <label><input type="checkbox" id="a7-opt-copy" checked> Copy Original Data</label>
                        <label><input type="checkbox" id="a7-opt-extract" checked> Extract Segment (CSV)</label>
                    </div>
                </div>
                
                <div style="display: flex; gap: 15px; margin-top: 15px; flex-wrap: wrap;">
                    <div class="input-group" style="flex: 1; min-width: 200px;">
                        <label>Scan Mode</label>
                        <select id="a7-mode" onchange="updateA7Mode()">
                            <option value="v1" selected>V1 (Phase 1 Only - Low Certainty)</option>
                            <option value="v2">V2 (Phase 1 & 2 - Medium Certainty)</option>
                            <option value="v3">V3 (Phase 1, 2 & 3 - High Certainty)</option>
                        </select>
                    </div>
                    <div class="input-group" style="flex: 1; min-width: 200px;">
                        <label>Pre-Filter Data Before Scan</label>
                        <select id="a7-filter">
                            <option value="none">None</option>
                            <option value="filt_0_20" selected>Bandpass 0-20 Hz (Removes Local Noise)</option>
                            <option value="filt_0_10">Bandpass 0-10 Hz</option>
                        </select>
                    </div>
                    <div class="input-group" style="flex: 1; min-width: 150px;">
                        <label>Sensor Bias Correction</label>
                        <div style="margin-top: 5px;">
                            <label title="Subtract the most frequent value (Mode) to center the baseline to 0."><input type="checkbox" id="a7-baseline-mode" checked> Auto-Center to 0 (Mode Average)</label>
                        </div>
                    </div>
                </div>
                
                <div class="input-group" style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 120px;">
                        <label>Extract Sec Before</label>
                        <input type="number" id="a7-ext-before" value="30" title="Seconds prior to trigger to extract">
                    </div>
                    <div style="flex: 1; min-width: 120px;">
                        <label>Extract Sec After</label>
                        <input type="number" id="a7-ext-after" value="60" title="Seconds after trigger to extract">
                    </div>
                    <div style="flex: 1; min-width: 120px;">
                        <label>Event Lockout (Sec)</label>
                        <input type="number" id="a7-lockout" value="10" title="Ignore new triggers for this many seconds">
                    </div>
                    <div style="flex: 1; min-width: 120px;">
                        <label>Discard File If Triggers ></label>
                        <input type="number" id="a7-discard-limit" value="20" title="Discard hour if an axis triggers more than this amount. Set to 0 to disable.">
                    </div>
                </div>
            </div>

            <div class="section-card" style="border: 2px solid #e83e8c;">
                <div class="section-title">Detection Parameters</div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <div class="input-group" style="flex:1; min-width: 150px;">
                        <label>Phase 1</label>
                        <div style="display:flex; gap:5px; margin-top:5px;">
                            <input type="number" step="0.01" id="a7-p1-tx" value="0.05" title="Threshold X (ms-2)" style="width:100%; flex:1;">
                            <input type="number" step="0.01" id="a7-p1-ty" value="0.05" title="Threshold Y (ms-2)" style="display:none; width:100%; flex:1;">
                            <input type="number" step="0.01" id="a7-p1-tz" value="0.05" title="Threshold Z (ms-2)" style="display:none; width:100%; flex:1;">
                        </div>
                        <input type="number" id="a7-p1-count" value="5" title="Count limit" style="margin-top:5px;">
                        <input type="number" step="0.1" id="a7-p1-win" value="0.5" title="Window (sec)" style="margin-top:5px;">
                    </div>
                    <div class="input-group" style="flex:1; min-width: 150px; opacity:0.4; pointer-events:none;" id="a7-p2-group">
                        <label>Phase 2</label>
                        <div style="display:flex; gap:5px; margin-top:5px;">
                            <input type="number" step="0.01" id="a7-p2-tx" value="0.03" title="Threshold X (ms-2)" style="width:100%; flex:1;">
                            <input type="number" step="0.01" id="a7-p2-ty" value="0.03" title="Threshold Y (ms-2)" style="display:none; width:100%; flex:1;">
                            <input type="number" step="0.01" id="a7-p2-tz" value="0.03" title="Threshold Z (ms-2)" style="display:none; width:100%; flex:1;">
                        </div>
                        <input type="number" id="a7-p2-count" value="10" title="Count limit" style="margin-top:5px;">
                        <input type="number" step="0.1" id="a7-p2-win" value="0.5" title="Window (sec)" style="margin-top:5px;">
                    </div>
                    <div class="input-group" style="flex:1; min-width: 150px; opacity:0.4; pointer-events:none;" id="a7-p3-group">
                        <label>Phase 3</label>
                        <div style="display:flex; gap:5px; margin-top:5px;">
                            <input type="number" step="0.01" id="a7-p3-tx" value="0.02" title="Threshold X (ms-2)" style="width:100%; flex:1;">
                            <input type="number" step="0.01" id="a7-p3-ty" value="0.02" title="Threshold Y (ms-2)" style="display:none; width:100%; flex:1;">
                            <input type="number" step="0.01" id="a7-p3-tz" value="0.02" title="Threshold Z (ms-2)" style="display:none; width:100%; flex:1;">
                        </div>
                        <input type="number" id="a7-p3-count" value="20" title="Count limit" style="margin-top:5px;">
                        <input type="number" step="0.1" id="a7-p3-win" value="0.4" title="Window (sec)" style="margin-top:5px;">
                    </div>
                </div>
                <button class="btn-large init-btn" onclick="run_app7()" style="margin-top: 20px;">Start Auto-Scan</button>
                <button class="btn-large cancel-btn" onclick="cancel_app7()" style="margin-top: 10px; display:none;" id="a7-cancel-btn">Stop Scan</button>
            </div>
        </div>
        """

    def get_js_funcs(self):
        return """
        function updateA7Mode() {
            const mode = document.getElementById('a7-mode').value;
            document.getElementById('a7-p2-group').style.opacity = (mode === 'v2' || mode === 'v3') ? '1' : '0.4';
            document.getElementById('a7-p2-group').style.pointerEvents = (mode === 'v2' || mode === 'v3') ? 'auto' : 'none';
            document.getElementById('a7-p3-group').style.opacity = (mode === 'v3') ? '1' : '0.4';
            document.getElementById('a7-p3-group').style.pointerEvents = (mode === 'v3') ? 'auto' : 'none';
        }
        
        function updateA7ThreshMode() {
            const isInd = document.getElementById('a7-thresh-mode').value === 'individual';
            const display = isInd ? 'block' : 'none';
            ['p1', 'p2', 'p3'].forEach(p => {
                document.getElementById(`a7-${p}-ty`).style.display = display;
                document.getElementById(`a7-${p}-tz`).style.display = display;
            });
        }
        
        function run_app7() {
            const target_dir = document.getElementById('a7-target-dir').value;
            const out_dir = document.getElementById('a7-out-dir').value;
            if(!target_dir || !out_dir) { alert("Please provide Target and Output directories."); return; }
            
            const tMode = document.getElementById('a7-thresh-mode').value;
            const getT = (p, ax) => parseFloat(document.getElementById(`a7-${p}-t${tMode==='unified'?'x':ax}`).value);
            
            const payload = {
                action: 'scan',
                app_id: 'app7',
                target_dir: target_dir,
                out_dir: out_dir,
                format: document.getElementById('a7-format').value,
                axes: { x: document.getElementById('a7-ax-x').checked, y: document.getElementById('a7-ax-y').checked, z: document.getElementById('a7-ax-z').checked },
                thresh_mode: tMode,
                axis_logic: document.getElementById('a7-axis-logic').value,
                discard_limit: parseInt(document.getElementById('a7-discard-limit').value) || 0,
                baseline_mode: document.getElementById('a7-baseline-mode').checked,
                opt_config: document.getElementById('a7-opt-config').checked,
                opt_copy: document.getElementById('a7-opt-copy').checked,
                opt_extract: document.getElementById('a7-opt-extract').checked,
                mode: document.getElementById('a7-mode').value,
                filter: document.getElementById('a7-filter').value,
                ext_before: parseFloat(document.getElementById('a7-ext-before').value),
                ext_after: parseFloat(document.getElementById('a7-ext-after').value),
                lockout: parseFloat(document.getElementById('a7-lockout').value),
                p1: [getT('p1','x'), getT('p1','y'), getT('p1','z'), parseInt(document.getElementById('a7-p1-count').value), parseFloat(document.getElementById('a7-p1-win').value)],
                p2: [getT('p2','x'), getT('p2','y'), getT('p2','z'), parseInt(document.getElementById('a7-p2-count').value), parseFloat(document.getElementById('a7-p2-win').value)],
                p3: [getT('p3','x'), getT('p3','y'), getT('p3','z'), parseInt(document.getElementById('a7-p3-count').value), parseFloat(document.getElementById('a7-p3-win').value)]
            };
            
            document.querySelector('#form-app7 .init-btn').style.display = 'none';
            document.getElementById('a7-cancel-btn').style.display = 'block';
            executeAppAction('app7', payload);
        }
        
        function cancel_app7() {
            executeAppAction('app7', { action: 'cancel' }, true);
        }
        """

    def run_custom_action(self, action, config):
        if action == 'cancel':
            self.state['cancel'] = True
            return
            
        if self.state['is_running']: return
        self.state['is_running'] = True
        self.state['cancel'] = False
        self.state['progress'] = 0
        threading.Thread(target=self._run_scan, args=(config,), daemon=True).start()

    def _get_station_name(self, file_path, fmt):
        try:
            if fmt == 'might_have_eq':
                return file_path.parts[-2]
            else:
                if len(file_path.parts) >= 6: return file_path.parts[-6]
                return file_path.parent.name
        except:
            return file_path.parent.name

    def _normalize_dataframe_columns(self, df):
        df.columns = [str(c).lower().strip() for c in df.columns]
        if 'timestamp' not in df.columns:
            time_cols = [c for c in df.columns if 'time' in c or 'date' in c]
            if time_cols:
                df.rename(columns={time_cols[0]: 'timestamp'}, inplace=True)
            else:
                df.rename(columns={df.columns[0]: 'timestamp'}, inplace=True)
                
        missing_axes = [ax for ax in ['x', 'y', 'z'] if ax not in df.columns]
        if missing_axes and len(df.columns) >= 4:
            df.rename(columns={df.columns[1]: 'x', df.columns[2]: 'y', df.columns[3]: 'z'}, inplace=True)
            
        return df

    def _apply_robust_timestamp(self, df):
        if 'timestamp' not in df.columns: return df
        if pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp_dt'] = df['timestamp']
            return df
            
        try:
            ts_numeric = pd.to_numeric(df['timestamp'])
            if ts_numeric.max() > 1e11: 
                unit = 'ms' if ts_numeric.max() < 1e15 else 'ns'
                df['timestamp_dt'] = pd.to_datetime(ts_numeric, unit=unit)
            else: 
                df['timestamp_dt'] = pd.to_datetime(ts_numeric, unit='s')
        except (ValueError, TypeError):
            df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
            
        df.dropna(subset=['timestamp_dt'], inplace=True)
        return df

    def _detect_earthquakes(self, df, mode, axes, p1, p2, p3, lockout_sec, discard_limit, axis_logic, baseline_mode):
        fs = 100
        lockout_points = int(lockout_sec * fs)
        axis_triggers_dict = {}
        
        for i, axis in enumerate(['x', 'y', 'z']):
            if not axes.get(axis, True) or axis not in df.columns: continue
            
            s = df[axis].values
            
            if baseline_mode:
                s_series = pd.Series(s).round(4)
                mode_vals = s_series.mode()
                bias = mode_vals.iloc[0] if not mode_vals.empty else np.median(s)
                s = s - bias
                
            t1, c1, w1_sec = p1[i], p1[3], p1[4]
            w1 = int(w1_sec * fs)
            
            exceed_p1 = (np.abs(s) >= t1).astype(int)
            cumsum_p1 = np.insert(np.cumsum(exceed_p1), 0, 0)
            roll_sum_p1 = cumsum_p1[w1:] - cumsum_p1[:-w1]
            
            p1_idx = np.where(roll_sum_p1 >= c1)[0] + w1 - 1 
            
            valid_idx = []
            for idx in p1_idx:
                start_p1 = idx - w1 + 1
                if mode in ['v2', 'v3']:
                    t2, c2, w2_sec = p2[i], p2[3], p2[4]
                    w2 = int(w2_sec * fs)
                    start_p2 = idx + 1
                    end_p2 = start_p2 + w2
                    if end_p2 > len(s): continue
                    
                    count_p2 = np.sum(np.abs(s[start_p2:end_p2]) >= t2)
                    if count_p2 < c2: continue
                    
                    if mode == 'v3':
                        t3, c3, w3_sec = p3[i], p3[3], p3[4]
                        w3 = int(w3_sec * fs)
                        start_p3 = end_p2
                        end_p3 = start_p3 + w3
                        if end_p3 > len(s): continue
                        
                        count_p3 = np.sum(np.abs(s[start_p3:end_p3]) >= t3)
                        if count_p3 < c3: continue
                        
                valid_idx.append(start_p1)
                
            axis_events = []
            last_trig = -999999
            for idx in valid_idx:
                if idx - last_trig > lockout_points:
                    axis_events.append(idx)
                    last_trig = idx
            
            if discard_limit > 0 and len(axis_events) >= discard_limit:
                return [] 
                
            axis_triggers_dict[axis] = axis_events

        final_triggers = []
        
        if axis_logic == 'all':
            sel_axes = [ax for ax in ['x', 'y', 'z'] if axes.get(ax, True) and ax in axis_triggers_dict]
            if not sel_axes: return []
            
            primary_ax = sel_axes[0]
            for t_idx in axis_triggers_dict[primary_ax]:
                joint_trigger = True
                for other_ax in sel_axes[1:]:
                    match_found = any(abs(t_idx - o_idx) <= lockout_points for o_idx in axis_triggers_dict[other_ax])
                    if not match_found:
                        joint_trigger = False
                        break
                
                if joint_trigger:
                    final_triggers.append((t_idx, 'all'))
                    
            deduped = []
            last_ev = -999999
            for idx, ax in final_triggers:
                if idx - last_ev > lockout_points:
                    deduped.append((idx, ax))
                    last_ev = idx
            return deduped

        else: 
            combined = []
            for ax, evs in axis_triggers_dict.items():
                for idx in evs:
                    combined.append((idx, ax))
            combined.sort(key=lambda x: x[0])
            
            deduped = []
            last_ev = -999999
            for idx, ax in combined:
                if idx - last_ev > lockout_points:
                    deduped.append((idx, ax))
                    last_ev = idx
            return deduped

    def _scan_file(self, file_path, config):
        if self.state.get('cancel'): return []
        try:
            log_name = f"{file_path.parent.name}/{file_path.name}"
            self.log_msg(f"Searching: {log_name}...")
            
            df = pd.read_parquet(file_path) if file_path.suffix == '.parquet' else pd.read_csv(file_path)
            if df.empty: return []

            df = self._normalize_dataframe_columns(df)
            df = self._apply_robust_timestamp(df)
            if df.empty: return []
            
            df.reset_index(drop=True, inplace=True)
            
            df_filt = df.copy()
            filt_type = config['filter']
            if filt_type in ['filt_0_10', 'filt_0_20']:
                from scipy.signal import butter, filtfilt
                
                cutoff = 10 if filt_type == 'filt_0_10' else 20
                b, a = butter(4, cutoff / 50.0, btype='low')
                    
                for ax in ['x', 'y', 'z']:
                    if ax in df_filt.columns:
                        s = df_filt[ax].fillna(0).values
                        df_filt[ax] = filtfilt(b, a, s)
                        
            lockout_sec = float(config.get('lockout', 10))
            discard_limit = int(config.get('discard_limit', 0))
            axis_logic = config.get('axis_logic', 'any')
            baseline_mode = config.get('baseline_mode', True)
            
            triggers = self._detect_earthquakes(df_filt, config['mode'], config['axes'], config['p1'], config['p2'], config['p3'], lockout_sec, discard_limit, axis_logic, baseline_mode)
            
            res = []
            station = self._get_station_name(file_path, config['format'])
            for idx, axis in triggers:
                trigger_time = df.iloc[idx]['timestamp_dt']
                res.append({'time': trigger_time, 'axis': axis, 'file': file_path, 'station': station})
            return res
        except Exception as e:
            self.log_msg(f"Error reading {file_path.name}: {e}")
            return []

    def _run_scan(self, config):
        try:
            target_dir = Path(config['target_dir']).resolve()
            out_dir = Path(config['out_dir']).resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
            
            opt_config = config.get('opt_config', True)
            opt_copy = config.get('opt_copy', True)
            opt_extract = config.get('opt_extract', True)
            
            ext_before = float(config.get('ext_before', 30))
            ext_after = float(config.get('ext_after', 60))
            
            valid_files = sorted(list(target_dir.rglob("*.parquet")) + list(target_dir.rglob("*.csv")))
            if not valid_files:
                self.log_msg("No parquet or csv files found in the specified directory.")
                return
                
            total = len(valid_files)
            workers = max(1, (os.cpu_count() or 4) - 2)
            self.log_msg(f"Found {total} files. Starting multi-threaded scan using {workers} CPU threads...")
            
            all_triggers = []
            lock = threading.Lock()
            
            def worker_wrapper(file):
                if self.state.get('cancel'): return []
                res = self._scan_file(file, config)
                
                with lock:
                    self.state['progress'] += 1
                    prog = self.state['progress']
                
                self.log_msg(json.dumps({"progress": prog, "total": total, "log": f"Scanned {prog}/{total} files"}))
                    
                for tr in res:
                    self.log_msg(f"<strong style='color:#28a745;'>EQ TRIGGER! {tr['time']} | Axis: {tr['axis'].upper()} | Station: {tr['station']}</strong>")
                
                return res

            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                results = list(executor.map(worker_wrapper, valid_files))

            for r in results:
                all_triggers.extend(r)
                
            if self.state.get('cancel'):
                self.log_msg("Scan cancelled by user.")
                return
                
            if not all_triggers:
                self.log_msg("Scan complete. No earthquakes detected.")
                return
                
            self.log_msg("Clustering adjacent triggers...")
            merged_events = []
            
            station_triggers = {}
            for tr in all_triggers:
                stat = tr['station']
                if stat not in station_triggers: station_triggers[stat] = []
                station_triggers[stat].append(tr)
                
            for stat, trs in station_triggers.items():
                trs.sort(key=lambda x: x['time'])
                stat_merged = []
                for tr in trs:
                    if not stat_merged:
                        stat_merged.append(tr)
                    else:
                        last = stat_merged[-1]
                        if (tr['time'] - last['time']).total_seconds() > max(ext_before, ext_after):
                            stat_merged.append(tr)
                merged_events.extend(stat_merged)
                
            merged_events.sort(key=lambda x: x['time'])

            station_files = {}
            for f in valid_files:
                stat = self._get_station_name(f, config['format'])
                if stat not in station_files: station_files[stat] = []
                station_files[stat].append(f)

            self.log_msg(f"Total unique events extracted: {len(merged_events)}")
            from processor_shared import process_and_plot_segment
            
            for i, event in enumerate(merged_events):
                if self.state.get('cancel'): break
                try:
                    t_ev = event['time']
                    axis = event['axis']
                    stat = event['station']
                    
                    safe_stat = "".join(c if c.isalnum() or c in " _-" else "_" for c in stat)
                    
                    stat_list = station_files.get(stat, [])
                    if not stat_list: continue
                    
                    f_idx = stat_list.index(event['file'])
                    files_to_load = []
                    if f_idx > 0: files_to_load.append(stat_list[f_idx-1])
                    files_to_load.append(stat_list[f_idx])
                    if f_idx < len(stat_list) - 1: files_to_load.append(stat_list[f_idx+1])
                    
                    try:
                        rel_parent = event['file'].parent.relative_to(target_dir)
                        event_out_dir = out_dir / rel_parent
                    except Exception:
                        event_out_dir = out_dir / safe_stat
                    
                    event_out_dir.mkdir(parents=True, exist_ok=True)
                    
                    if opt_copy:
                        try:
                            for f in files_to_load:
                                if f.exists():
                                    try:
                                        f_rel = f.parent.relative_to(target_dir)
                                        f_dest_dir = out_dir / f_rel
                                    except Exception:
                                        f_dest_dir = out_dir / safe_stat
                                        
                                    f_dest_dir.mkdir(parents=True, exist_ok=True)
                                    f_dest = f_dest_dir / f.name
                                    if not f_dest.exists():
                                        shutil.copy2(f, f_dest)
                        except Exception as e:
                            self.log_msg(f"File copy error for {stat}: {e}")

                    if opt_config:
                        try:
                            start_dt = t_ev - pd.Timedelta(seconds=ext_before)
                            end_dt = t_ev + pd.Timedelta(seconds=ext_after)
                            
                            date_str = t_ev.strftime('%Y-%m-%d')
                            time_str = t_ev.strftime('%H-%M-%S')
                            config_filename = f"{date_str}_{time_str}_UTC_{safe_stat}.json"
                            
                            filt_val = config.get('filter', 'filt_0_20')
                            app2_filters = []
                            if filt_val == 'filt_0_10':
                                app2_filters = [[0, 10]]
                            elif filt_val == 'filt_0_20':
                                app2_filters = [[0, 20]]
                                
                            new_target_dir = str(event_out_dir.resolve()) if opt_copy else str(event['file'].parent.resolve())
                                
                            app2_config = {
                                "app": "app2",
                                "target-dir": new_target_dir,
                                "start-hh": start_dt.strftime("%H"),
                                "start-mm": start_dt.strftime("%M"),
                                "start-ss": start_dt.strftime("%S"),
                                "end-hh": end_dt.strftime("%H"),
                                "end-mm": end_dt.strftime("%M"),
                                "end-ss": end_dt.strftime("%S"),
                                "filters": app2_filters,
                                "dampings": [0],
                                "draw-orig": "y",
                                "keep-csv": "n",
                                "sep-plots": "y",
                                "comp-plots": "n",
                                "fft-plots": "n",
                                "fft-ax-x": True,
                                "fft-ax-y": True,
                                "fft-ax-z": True,
                                "resp-plots": "n",
                                "resp-ax-x": True,
                                "resp-ax-y": False,
                                "resp-ax-z": False,
                                "save-plots": "n",
                                "axis-font-size": "12",
                                "title-font-size": "13",
                                "custom_title_base": f"Auto EQ Det ({config['mode'].upper()}): {stat} Trig",
                                "updated_titles": {},
                                "notes-comments": ""
                            }
                            
                            with open(event_out_dir / config_filename, 'w') as f:
                                json.dump(app2_config, f, indent=4)
                        except Exception as e:
                            self.log_msg(f"Config generation error for {stat}: {e}")

                    if opt_extract:
                        try:
                            dfs = []
                            for f in files_to_load:
                                if f.exists():
                                    df_part = pd.read_parquet(f) if f.suffix == '.parquet' else pd.read_csv(f)
                                    df_part = self._normalize_dataframe_columns(df_part)
                                    df_part = self._apply_robust_timestamp(df_part)
                                    if not df_part.empty:
                                        dfs.append(df_part)
                                        
                            if dfs:
                                df_comb = pd.concat(dfs, ignore_index=True)
                                
                                mask = (df_comb['timestamp_dt'] >= t_ev - pd.Timedelta(seconds=ext_before)) & (df_comb['timestamp_dt'] <= t_ev + pd.Timedelta(seconds=ext_after))
                                df_eq = df_comb[mask].copy().sort_values('timestamp_dt')
                                
                                if not df_eq.empty:
                                    event_str = f"EQ_{t_ev.strftime('%Y-%m-%d_%H-%M-%S')}_{safe_stat}"
                                    
                                    extract_dir = event_out_dir / "Extracted_EQs"
                                    extract_dir.mkdir(exist_ok=True)
                                    
                                    df_eq.drop(columns=['timestamp_dt'], inplace=True, errors='ignore')
                                    df_eq.to_csv(extract_dir / f"{event_str}.csv", index=False)
                                    
                                    df_eq = self._apply_robust_timestamp(df_eq)
                                        
                                    plot_config = {
                                        'axes_to_plot': ['x', 'y', 'z'],
                                        'sep_plots': True,
                                        'comp_plots': False,
                                        'resp_plots': False,
                                        'fft_plots': False,
                                        'custom_title': f"Auto EQ Det ({config['mode'].upper()}): {stat} Trig"
                                    }
                                    
                                    process_and_plot_segment(df_eq, plot_config, event_str, stat, extract_dir, df_eq['timestamp_dt'].min(), df_eq['timestamp_dt'].max(), self.log_msg)
                        except Exception as e:
                            self.log_msg(f"Extraction error for {stat}: {e}")

                except Exception as e:
                    self.log_msg(f"Error processing individual trigger cluster for {stat}: {e}")

                self.log_msg(json.dumps({"log": f"Exported & Mirrored {i+1}/{len(merged_events)}", "progress": i+1, "total": len(merged_events)}))
                
            self.log_msg("Scan & Artifact Generation Complete.")
            
        except Exception as e:
            self.log_msg(f"Fatal Error in Scan: {e}")
        finally:
            ui_reset_hack = "<img src='x' style='display:none;' onerror=\"document.querySelector('#form-app7 .init-btn').style.display='block'; document.getElementById('a7-cancel-btn').style.display='none'; this.remove();\">"
            self.log_msg(ui_reset_hack)
            self.log_msg(json.dumps({"done": True, "action": "reset_btn", "btn_selector": "#form-app7 .init-btn", "cancel_selector": "#a7-cancel-btn"}))
            self.state['is_running'] = False