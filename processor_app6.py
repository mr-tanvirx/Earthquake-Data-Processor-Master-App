import json, os, threading, re
import pandas as pd
import numpy as np
from pathlib import Path
import concurrent.futures

class App6Processor:
    APP_ID = "app6"
    APP_TITLE = "App 6: RSH to BLCA Converter"

    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.state = {"is_running": False}

    def log_msg(self, msg):
        self.log_queue.put(msg)

    def get_html_template(self):
        return """
        <div class="grid-layout">
            <div class="section-card" style="border: 2px solid #6f42c1;">
                <div class="section-title">Raspberry Shake (miniSEED) to BLCA Parquet Converter</div>
                
                <!-- Internal Sub-Tabs for File Type Selection -->
                <div class="sub-tab-nav" style="display: flex; gap: 5px; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 5px;">
                    <button type="button" class="sub-tab-btn" id="app6-subtab-standard" onclick="switchApp6SubTab('standard')" style="padding: 10px 15px; cursor: pointer; background: #6f42c1; color: white; border: none; border-radius: 6px 6px 0 0; font-weight: bold; transition: 0.2s;">Standard miniSEED (.mseed)</button>
                    <button type="button" class="sub-tab-btn" id="app6-subtab-jday" onclick="switchApp6SubTab('jday')" style="padding: 10px 15px; cursor: pointer; background: var(--tab-bg); color: var(--text-color); border: none; border-radius: 6px 6px 0 0; font-weight: bold; transition: 0.2s;">Julian Day Files (.325 / Day Archives)</button>
                </div>
                
                <input type="hidden" id="app6-file-mode" value="standard">
                
                <div id="app6-jday-note" style="display: none; background: rgba(111, 66, 193, 0.1); border-left: 4px solid #6f42c1; padding: 10px; margin-bottom: 15px; border-radius: 0 6px 6px 0;">
                    <small style="color: var(--text-color); font-weight: 500; display: block;">
                        <strong>Julian Day Mode Active:</strong> Tailored for channel data split by Julian day extensions (e.g., <code>AM.RE038.00.EHZ.D.2025.325</code> as referenced in image_74630a.png). Non-seismic metadata components like <code>.xml</code> are filtered automatically.
                    </small>
                </div>

                <div class="input-group">
                    <label>Input Directory (Location of .mseed or trace folders)</label>
                    <input type="text" id="app6-input-dir" placeholder="e.g., C:\\RS_Data">
                </div>
                <div class="input-group">
                    <label>Output Directory (Destination)</label>
                    <input type="text" id="app6-output-dir" placeholder="e.g., C:\\Converted_Data">
                </div>
                
                <div class="input-group" style="margin-top: 15px; background: var(--tab-bg); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color);">
                    <label style="color: #6f42c1; font-weight: bold;">Output Folder Structure</label>
                    <div class="radio-group" style="flex-direction: column; gap: 8px;">
                        <label><input type="radio" name="app6_struct" class="out-struct" value="blca" checked> <strong>Standard BLCA Archive</strong> (Station/archive/YYYY/MM/DD/data_HH.parquet)</label>
                        <label><input type="radio" name="app6_struct" class="out-struct" value="app1"> <strong>App 1 Custom Root Format</strong> (Event_Date/Station/data_HH.parquet)</label>
                    </div>
                    <small style="display: block; margin-top: 8px;">* Select 'App 1 Custom Root Format' if you are processing FDSNWS downloads and intend to use them in App 1's Custom Directory search.</small>
                </div>
                
                <h3 style="margin-top: 15px; font-size: 1em; color: #6f42c1;">Hardware & Conversion Parameters (V4 / V5 Defaults)</h3>
                <div class="grid-layout" style="margin-bottom: 0;">
                    <div class="input-group">
                        <label>Target Sampling Rate (Hz)</label>
                        <input type="number" id="app6-sampling-rate" value="100">
                    </div>
                    <div class="input-group">
                        <label>MEMS Accel Sensitivity (Counts per m/s²)</label>
                        <input type="number" id="app6-accel-sens" value="396000" step="any">
                        <small>ENE, ENN, ENZ. Use 396000 for V4 or 387000 for V5.</small>
                    </div>
                    <div class="input-group" style="grid-column: span 2;">
                        <label>Geophone Velocity Sensitivity (Counts per m/s)</label>
                        <input type="number" id="app6-geo-sens" value="469000000" step="any">
                        <small>EHZ channel. Script mathematically differentiates this to m/s² automatically.</small>
                    </div>
                </div>
                <button class="btn-large init-btn" onclick="run_app6()" style="background-color: #6f42c1; margin-top: 15px;">Convert miniSEED Data</button>
            </div>
        </div>
        """

    def get_js_funcs(self):
        return """
        function switchApp6SubTab(mode) {
            const btnStandard = document.getElementById('app6-subtab-standard');
            const btnJday = document.getElementById('app6-subtab-jday');
            const noteBox = document.getElementById('app6-jday-note');
            const modeInput = document.getElementById('app6-file-mode');
            
            if (mode === 'standard') {
                btnStandard.style.background = '#6f42c1';
                btnStandard.style.color = 'white';
                btnJday.style.background = 'var(--tab-bg)';
                btnJday.style.color = 'var(--text-color)';
                noteBox.style.display = 'none';
                modeInput.value = 'standard';
            } else {
                btnJday.style.background = '#6f42c1';
                btnJday.style.color = 'white';
                btnStandard.style.background = 'var(--tab-bg)';
                btnStandard.style.color = 'var(--text-color)';
                noteBox.style.display = 'block';
                modeInput.value = 'jday';
            }
        }

        function run_app6() {
            const pane = document.getElementById('tab-app6');
            const payload = {
                action: 'convert',
                file_mode: document.getElementById('app6-file-mode').value,
                input_dir: document.getElementById('app6-input-dir').value,
                output_dir: document.getElementById('app6-output-dir').value,
                out_struct: pane.querySelector('.out-struct:checked')?.value || 'blca',
                sampling_rate: parseFloat(document.getElementById('app6-sampling-rate').value || 100),
                accel_sens: parseFloat(document.getElementById('app6-accel-sens').value || 396000),
                geo_sens: parseFloat(document.getElementById('app6-geo-sens').value || 469000000)
            };
            executeAppAction('app6', payload);
        }
        """

    def run_custom_action(self, action, config):
        self.state['is_running'] = True
        try:
            import obspy
        except ImportError:
            self.log_msg('<strong style="color:red;">Error: "obspy" library is not installed.</strong>')
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            return

        file_mode = config.get("file_mode", "standard")
        input_dir = config.get("input_dir")
        output_dir = config.get("output_dir")
        out_struct = config.get("out_struct", "blca")
        target_sr = config.get("sampling_rate", 100.0)
        accel_sens = config.get("accel_sens", 396000.0)
        geo_sens = config.get("geo_sens", 469000000.0)
        
        if accel_sens == 0: accel_sens = 1.0
        if geo_sens == 0: geo_sens = 1.0

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
        
        if file_mode == "jday":
            self.log_msg(f"Scanning {input_dir} for Julian Day structured channel archive traces...")
        else:
            self.log_msg(f"Scanning {input_dir} for miniSEED data...")

        groups = {}
        files = [f for f in in_path.rglob("*") if f.is_file()]
        
        for f in files:
            app1_match = re.search(r"(?:AM_)?([A-Z0-9]+)_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.mseed", f.name)
            
            if out_struct == 'app1' and app1_match:
                stat = app1_match.group(1)
                evt_str = app1_match.group(2)
                groups.setdefault((stat, evt_str, 'app1_mode'), []).append(f)
                continue

            parts = f.name.split('.')
            if len(parts) >= 7 and parts[-1].isdigit() and parts[-2].isdigit() and len(parts[-2]) == 4:
                stat, year, jday = parts[1], parts[-2], parts[-1]
                if out_struct == 'app1':
                    groups.setdefault((stat, f"{year}_{jday}", 'app1_mode'), []).append(f)
                else:
                    groups.setdefault((stat, year, jday), []).append(f)
            else:
                try:
                    st_head = obspy.read(str(f), headonly=True)
                    if st_head:
                        stat = st_head[0].stats.station
                        if out_struct == 'app1':
                            evt_str = st_head[0].stats.starttime.strftime("%Y-%m-%d_%H-%M-%S")
                            groups.setdefault((stat, evt_str, 'app1_mode'), []).append(f)
                        else:
                            year = st_head[0].stats.starttime.year
                            jday = st_head[0].stats.starttime.julday
                            groups.setdefault((stat, str(year), f"{jday:03d}"), []).append(f)
                except Exception:
                    pass

        if not groups:
            self.log_msg("No valid miniSEED trace files found.")
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            return

        total_groups = len(groups)
        self.log_msg(f"Found {total_groups} unique data groups to process. Engaging multi-threaded batch mode...")

        lock = threading.Lock()
        self.state['progress'] = 0
        self.state['total'] = total_groups
        workers = max(1, (os.cpu_count() or 4) - 2)

        def process_station_day(item):
            import obspy 
            group_key, group_files = item
            stat, val2, mode_flag = group_key[0], group_key[1], group_key[2] if len(group_key) == 3 else "blca_mode"
            
            try:
                if mode_flag == 'app1_mode':
                    event_str = val2
                    self.log_msg(f"> Processing Event {event_str} | Station {stat}")
                else:
                    year = val2
                    jday = mode_flag
                    self.log_msg(f"> Processing Station {stat} | Year {year} | Day {jday}")

                st = obspy.Stream()
                for f in group_files:
                    try:
                        st += obspy.read(str(f))
                    except Exception:
                        pass 

                if not st:
                    return

                st.merge(method=1, fill_value=0)
                st.detrend('demean')
                st.detrend('linear')

                for tr in st:
                    if tr.stats.sampling_rate != target_sr:
                        tr.interpolate(sampling_rate=target_sr)

                active_hours = set()
                for tr in st:
                    tr_start = tr.stats.starttime
                    tr_end = tr.stats.endtime
                    curr = obspy.UTCDateTime(tr_start.year, tr_start.month, tr_start.day, tr_start.hour, 0, 0)
                    while curr <= tr_end:
                        active_hours.add(curr.timestamp)
                        curr += 3600
                
                for current_hr_ts in sorted(list(active_hours)):
                    hr_start = obspy.UTCDateTime(current_hr_ts)
                    hr_end = hr_start + 3600

                    st_hr = st.slice(starttime=hr_start, endtime=hr_end)
                    if not st_hr:
                        continue
                        
                    # BLEED-OVER FIX: 
                    # If this specific hour chunk contains less than 5 seconds of total data, 
                    # it is just FDSN packet overlap. Discard it.
                    try:
                        valid_data_length = max([tr.stats.endtime - tr.stats.starttime for tr in st_hr])
                        if valid_data_length < 5.0:
                            continue
                    except ValueError:
                        continue
                    
                    ideal_times = np.arange(hr_start.timestamp, hr_end.timestamp, 1.0 / target_sr)
                    df = pd.DataFrame({'timestamp': ideal_times})
                    df['x'], df['y'], df['z'] = np.nan, np.nan, np.nan

                    has_data = False
                    dt_period = 1.0 / target_sr

                    for tr in st_hr:
                        chan = tr.stats.channel.upper()
                        abs_times = tr.times() + tr.stats.starttime.timestamp
                        
                        if chan == 'EHZ':
                            velocity_data = tr.data / geo_sens
                            converted_data = np.gradient(velocity_data, dt_period)
                            col = 'z'
                        elif chan in ['ENE', 'ENN', 'ENZ']:
                            converted_data = tr.data / accel_sens
                            if chan == 'ENE': col = 'x'
                            elif chan == 'ENN': col = 'y'
                            elif chan == 'ENZ': col = 'z'
                        else:
                            continue
                            
                        has_data = True
                        
                        tr_df = pd.DataFrame({'timestamp': abs_times, 'val': converted_data}).sort_values('timestamp')
                        tr_df = tr_df.drop_duplicates(subset=['timestamp'])
                        
                        df = pd.merge_asof(
                            df, 
                            tr_df, 
                            on='timestamp', 
                            direction='nearest', 
                            tolerance=(0.5 / target_sr)
                        )
                        
                        if col == 'z' and not df['z'].isna().all() and chan == 'ENZ':
                            df = df.drop(columns=['val'])
                            continue
                            
                        df[col] = df['val'].fillna(df[col])
                        df = df.drop(columns=['val'])

                    if not has_data: continue
                    
                    df = df.fillna(0.0)

                    if out_struct == 'app1':
                        save_dir = out_path / event_str / stat
                    else:
                        base_date = pd.to_datetime(hr_start.timestamp, unit='s')
                        save_dir = out_path / stat / "archive" / f"{base_date.year}" / f"{base_date.month:02d}" / f"{base_date.day:02d}"
                        
                    save_dir.mkdir(parents=True, exist_ok=True)
                    out_file = save_dir / f"data_{hr_start.hour:02d}.parquet"

                    df.to_parquet(out_file, index=False)
                    
            except Exception as e:
                self.log_msg(f"Error processing group {group_key}: {e}")
            finally:
                with lock:
                    self.state['progress'] += 1
                    prog = self.state['progress']
                self.log_msg(json.dumps({"progress": prog, "total": total_groups}))

        tasks = []
        for key, files in groups.items():
            tasks.append((key, files))

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(process_station_day, tasks)

        self.log_msg(f"Conversion complete. Data structured at {output_dir}")
        self.log_msg(json.dumps({"done": True, "has_more": False, "progress": total_groups, "total": total_groups}))
        self.state['is_running'] = False