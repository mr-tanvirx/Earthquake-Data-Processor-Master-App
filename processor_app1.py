import json, gc, shutil, os, time
import urllib.request
import urllib.error
import pandas as pd
from pathlib import Path
import boto3
import concurrent.futures
from processor_shared import parse_timestamps, fetch_s3_stations, process_and_plot_segment, AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION, TARGET_BUCKET, PREFIX

class App1Processor:
    APP_ID = "app1"
    APP_TITLE = "App 1: Search EQ Archive"

    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.state = {"is_running": False, "events": [], "all_stations": [], "current_event_idx": 0, "config": None, "local_stations": [], "s3_stations": []}

    def log_msg(self, msg): self.log_queue.put(msg)

    def get_html_template(self):
        return """
        <div class="grid-layout" id="form-app1">
            <div class="section-card">
                <div class="section-title">Global Search Configuration</div>
                <div class="input-group"><label>Local Archive Directory</label><input type="text" class="local-dir" id="a1-local-dir" placeholder="e.g., G:\\Archive"></div>
                <div class="input-group"><label>Check S3 Cloud Archive?</label>
                    <div class="radio-group"><label><input type="radio" name="a1_s3" class="check-s3" value="y" checked> Yes</label><label><input type="radio" name="a1_s3" class="check-s3" value="n"> No</label></div>
                </div>
                
                <div class="input-group" style="margin-top: 15px;">
                    <label style="color: #6f42c1; font-weight: bold;">Check Raspberry Shake Data?</label>
                    <div class="radio-group">
                        <label><input type="radio" name="a1_rs" class="check-rs" value="y" onchange="document.getElementById('a1_rs_params').style.display='block'"> Yes</label>
                        <label><input type="radio" name="a1_rs" class="check-rs" value="n" checked onchange="document.getElementById('a1_rs_params').style.display='none'"> No</label>
                    </div>
                    <div id="a1_rs_params" style="display:none; margin-top: 10px; padding: 10px; background: var(--bg-color); border: 2px dashed #6f42c1; border-radius: 6px;">
                        <div class="inline-inputs" style="margin-bottom:8px;">
                            <input type="text" id="rs-net" placeholder="Network" value="AM" style="width: 70px;">
                            <input type="text" id="rs-sta" placeholder="Station ID" value="RE038" style="width: 100px;">
                            <input type="text" id="rs-loc" placeholder="Location" value="00" style="width: 70px;">
                            <input type="text" id="rs-cha" placeholder="Channels" value="EHZ,ENZ,ENE,ENN" style="width: 140px;">
                        </div>
                        <small>Target: Output Directory -> FDSNWS Server miniSEED downloads.</small>
                    </div>
                </div>
            </div>
            <div class="section-card" style="border: 2px dashed #007bff;">
                <div class="section-title">Custom Folder Overrides & Saving</div>
                <div class="input-group"><label>Custom Root Directory</label><input type="text" class="custom-dir" id="a1-custom-dir" placeholder="e.g., C:\\My_Custom_EQ_Data"></div>
                <div class="input-group"><label>Output Directory</label><input type="text" class="output-dir" id="a1-out-dir" placeholder="e.g., C:\\Downloads\\Output"></div>
                
                <h4 style="margin: 10px 0 5px 0; font-size: 1em; color: #17a2b8;">Generate App 2 Configurations per EQ?</h4>
                <div class="input-group">
                    <div class="radio-group"><label><input type="radio" name="a1_gen_conf" class="gen-app2-conf" value="y" checked> Yes</label><label><input type="radio" name="a1_gen_conf" class="gen-app2-conf" value="n"> No</label></div>
                </div>
                <div class="input-group"><label>Config Save Directory</label><input type="text" class="conf-out-dir" id="a1-conf-out-dir" placeholder="e.g., C:\\EQ_Configs"></div>
            </div>
        </div>
        <div class="grid-layout">
            <div class="section-card">
                <div class="section-title">Event Parameters</div>
                <div class="input-group">
                    <label>Recent Earthquakes (M/D/YYYY HH:MM:SS)</label>
                    <textarea class="eq-text" id="a1-eq-text" rows="5">5/26/2026 5:40:49
5/26/2026 14:07:51
5/26/2026 16:30:57
5/29/2026 12:22:54
6/4/2026 15:39:26</textarea>
                </div>
                <div class="input-group">
                    <label>Time Window</label>
                    <div class="inline-inputs"><span>Plot</span><input type="number" class="time-before" id="a1-tb" value="10" oninput="calcDurA1()"><span>s behind to</span><input type="number" class="time-after" id="a1-ta" value="90" oninput="calcDurA1()"><span>s after.</span></div>
                    <div class="duration-box" id="a1-duration">Duration: 100 seconds</div>
                    <small style="display:block; margin-top:5px; color:#6f42c1;">* If Raspberry Shake FDSN is checked, the entire containing hour will be downloaded automatically.</small>
                </div>
            </div>
            <div class="section-card">
                <div class="section-title">Filters & Spectrum Config</div>
                <label>Band Pass Filters (Hz)</label>
                <div class="filters-container" id="a1-fc"><div class="filter-row"><input type="number" class="low-cut" placeholder="Low"> to <input type="number" class="high-cut" placeholder="High"></div></div>
                <button type="button" class="btn-small" onclick="addFilterUI('a1-fc')">+ Add Filter</button>
                <label style="margin-top: 10px;">Damping Ratios (%)</label>
                <div class="damping-container" id="a1-dc"><div class="filter-row"><input type="number" class="damping-val" placeholder="e.g. 5" value="0"></div></div>
                <button type="button" class="btn-small" onclick="addDampingUI('a1-dc')">+ Add Damping</button>
            </div>
        </div>
        <div class="section-card">
            <div class="section-title">Generation Settings</div>
            <div class="settings-grid" id="a1-settings">
                <div class="input-group"><label>Events Per Page</label><input type="number" class="events-per-page" id="a1-epp" value="5"></div>
                <div class="input-group"><label>Keep ALL Data as CSVs</label><div class="radio-group"><label><input type="radio" name="a1_csv" class="keep-csv" value="y"> Y</label><label><input type="radio" name="a1_csv" class="keep-csv" value="n" checked> N</label></div></div>
                <div class="input-group"><label>Draw Original Plot</label><div class="radio-group"><label><input type="radio" name="a1_orig" class="draw-orig" value="y" checked> Y</label><label><input type="radio" name="a1_orig" class="draw-orig" value="n"> N</label></div></div>
                <div class="input-group"><label>Mark Max & Min Values</label><div class="radio-group"><label><input type="radio" name="a1_extrema" class="mark-extrema" value="y"> Y</label><label><input type="radio" name="a1_extrema" class="mark-extrema" value="n" checked> N</label></div></div>
                <div class="input-group"><label>Filtered Plots</label><div class="radio-group"><label><input type="radio" name="a1_sep" class="sep-plots" value="y" checked> Y</label><label><input type="radio" name="a1_sep" class="sep-plots" value="n"> N</label></div></div>
                <div class="input-group"><label>Comparison Plots</label><div class="radio-group"><label><input type="radio" name="a1_comp" class="comp-plots" value="y" checked> Y</label><label><input type="radio" name="a1_comp" class="comp-plots" value="n"> N</label></div></div>
                <div class="input-group">
                    <label>Response Spectrum Plots</label>
                    <div class="radio-group">
                        <label><input type="radio" name="a1_resp" class="resp-plots" value="y" onchange="document.getElementById('a1_resp_axes').style.display='block'"> Y</label>
                        <label><input type="radio" name="a1_resp" class="resp-plots" value="n" checked onchange="document.getElementById('a1_resp_axes').style.display='none'"> N</label>
                    </div>
                    <div id="a1_resp_axes" style="display:none; margin-top: 10px; padding: 10px; background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 6px;">
                        <label style="display:inline; margin-right: 10px;"><input type="checkbox" class="resp-ax-x" value="x" checked> X-Axis</label>
                        <label style="display:inline; margin-right: 10px;"><input type="checkbox" class="resp-ax-y" value="y"> Y-Axis</label>
                        <label style="display:inline;"><input type="checkbox" class="resp-ax-z" value="z"> Z-Axis</label>
                    </div>
                </div>
                <div class="input-group"><label>Save Automatically</label><div class="radio-group"><label><input type="radio" name="a1_save" class="save-plots" value="y"> Y</label><label><input type="radio" name="a1_save" class="save-plots" value="n" checked> N</label></div></div>
                <div class="input-group"><label>Axis Title Font Size</label><input type="number" id="a1-axis-font" value="12"></div>
                <div class="input-group"><label>Main Title Font Size</label><input type="number" id="a1-title-font" value="13"></div>
            </div>
        </div>
        <button class="btn-large init-btn" onclick="run_app1()">Initialize App 1 Processing</button>
        """

    def get_js_funcs(self):
        return """
        function calcDurA1() {
            const b = parseInt(document.getElementById('a1-tb').value || 0);
            const a = parseInt(document.getElementById('a1-ta').value || 0);
            document.getElementById('a1-duration').innerText = `Duration: ${b + a} seconds`;
        }
        function run_app1() {
            const pane = document.getElementById('tab-app1');
            const payload = {
                local_dir: document.getElementById('a1-local-dir').value,
                check_s3: pane.querySelector('.check-s3:checked')?.value === 'y',
                check_rs: pane.querySelector('.check-rs:checked')?.value === 'y',
                rs_net: document.getElementById('rs-net').value || 'AM',
                rs_sta: document.getElementById('rs-sta').value || 'RE038',
                rs_loc: document.getElementById('rs-loc').value || '00',
                rs_cha: document.getElementById('rs-cha').value || 'EHZ,ENZ,ENE,ENN',
                custom_dir: document.getElementById('a1-custom-dir').value,
                output_dir: document.getElementById('a1-out-dir').value,
                gen_app2_config: pane.querySelector('.gen-app2-conf:checked')?.value === 'y',
                app2_config_dir: document.getElementById('a1-conf-out-dir').value || document.getElementById('a1-out-dir').value,
                eq_text: document.getElementById('a1-eq-text').value,
                time_before: parseFloat(document.getElementById('a1-tb').value || 10),
                time_after: parseFloat(document.getElementById('a1-ta').value || 90),
                events_per_page: parseInt(document.getElementById('a1-epp').value || 5),
                filters: extractFiltersUI('a1-fc'),
                dampings: extractDampingsUI('a1-dc'),
                draw_orig: pane.querySelector('.draw-orig:checked')?.value === 'y',
                mark_extrema: pane.querySelector('.mark-extrema:checked')?.value === 'y',
                keep_csv: pane.querySelector('.keep-csv:checked')?.value === 'y',
                sep_plots: pane.querySelector('.sep-plots:checked')?.value === 'y',
                comp_plots: pane.querySelector('.comp-plots:checked')?.value === 'y',
                resp_plots: pane.querySelector('.resp-plots:checked')?.value === 'y',
                resp_axes: ['x','y','z'].filter(ax => pane.querySelector('.resp-ax-'+ax)?.checked),
                save_plots: pane.querySelector('.save-plots:checked')?.value === 'y',
                axis_font_size: parseInt(document.getElementById('a1-axis-font').value || 12),
                title_font_size: parseInt(document.getElementById('a1-title-font').value || 13)
            };
            executeAppWorkflow('app1', payload);
        }
        """

    def initialize(self, config):
        events = parse_timestamps(config['eq_text'], self.log_msg)
        if not events: return {"status": "Error"}

        if config.get('check_rs'):
            self.state['events'] = events
            self.state['config'] = config
            self.state['current_event_idx'] = 0
            self.log_msg("--- APP 1: RASPBERRY SHAKE FDSNWS DOWNLOAD MODE ACTIVE ---")
            return {"status": "Initialized"}

        custom_dir = Path(config['custom_dir']) if config.get('custom_dir', '').strip() else None
        self.state['s3_stations'] = []
        self.state['local_stations'] = []
        all_stations = []

        if custom_dir and custom_dir.exists():
            self.log_msg("--- APP 1: CUSTOM DIRECTORY MODE ACTIVE ---")
            all_stations_set = set()
            for event_dir in custom_dir.iterdir():
                if event_dir.is_dir():
                    for stat_dir in event_dir.iterdir():
                        if stat_dir.is_dir(): all_stations_set.add(stat_dir.name)
            all_stations = sorted(list(all_stations_set))
        else:
            self.log_msg("--- APP 1: GLOBAL SEARCH MODE ACTIVE ---")
            if config.get('check_s3'):
                try:
                    s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=AWS_REGION)
                    self.state['s3_stations'] = fetch_s3_stations(s3_client, TARGET_BUCKET, PREFIX, self.log_msg)
                except Exception as e: self.log_msg(f"S3 Error: {e}")

            local_dir_base = Path(config['local_dir']) if config.get('local_dir', '').strip() else None
            if local_dir_base and local_dir_base.exists():
                self.state['local_stations'] = [d.name for d in local_dir_base.iterdir() if d.is_dir()]
            all_stations = sorted(list(set(self.state['local_stations'] + self.state['s3_stations'])))

        if not all_stations: return {"status": "Error"}
        
        self.state['events'] = events
        self.state['all_stations'] = all_stations
        self.state['current_event_idx'] = 0
        self.state['config'] = config
        return {"status": "Initialized"}

    def start_page_thread(self):
        self.state['is_running'] = True
        config = self.state['config']
        
        if config.get('check_rs'):
            self.run_rs_download(config)
            return

        events_per_page = config.get('events_per_page', 5)
        start_idx = self.state['current_event_idx']
        end_idx = start_idx + events_per_page
        current_events = self.state['events'][start_idx:end_idx]
        
        if not current_events:
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            return

        tasks = [(evt, stat) for evt in current_events for stat in self.state['all_stations']]
        self.state['total'] = len(tasks)
        self.state['progress'] = 0
        out_dir = Path(config['output_dir']) / "folder"
        custom_dir = Path(config['custom_dir']) if config.get('custom_dir', '').strip() else None

        workers = max(1, (os.cpu_count() or 4) - 2)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(self.process_task, evt, stat, config, out_dir, custom_dir) for evt, stat in tasks]
            concurrent.futures.wait(futures)

        self.state['current_event_idx'] = end_idx
        self.log_msg(json.dumps({"done": True, "has_more": self.state['current_event_idx'] < len(self.state['events'])}))
        self.state['is_running'] = False

    def run_rs_download(self, config):
        out_dir = Path(config['output_dir']) / "Raspberry_Shake_Downloads"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        net = config.get('rs_net', 'AM')
        sta = config.get('rs_sta', '').strip()
        loc = config.get('rs_loc', '00')
        cha = config.get('rs_cha', 'EHZ,ENZ,ENE,ENN')
        
        if not sta:
            self.log_msg('<strong style="color:red;">Error: Station code is required for Raspberry Shake FDSN downloads.</strong>')
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            return

        events = self.state['events']
        self.state['total'] = len(events)
        self.state['progress'] = 0
        
        for evt in events:
            st_hour = evt.replace(minute=0, second=0, microsecond=0)
            et_hour = st_hour + pd.Timedelta(hours=1)
            
            st_str = st_hour.strftime("%Y-%m-%dT%H:%M:%S")
            et_str = et_hour.strftime("%Y-%m-%dT%H:%M:%S")
            
            url = f"https://data.raspberryshake.org/fdsnws/dataselect/1/query?starttime={st_str}&endtime={et_str}&network={net}&station={sta}&location={loc}&channel={cha}&nodata=404"
            
            evt_file_str = evt.strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{net}_{sta}_{evt_file_str}.mseed"
            dest_path = out_dir / filename
            
            self.log_msg(f"Targeting FDSN Server for event: {evt_file_str} (Fetching full hour: {st_hour.hour:02d}:00:00)")
            
            try:
                urllib.request.urlretrieve(url, str(dest_path))
                self.log_msg(f"-> Success: Downloaded {filename}")
            except urllib.error.HTTPError as e:
                self.log_msg(f"-> Failed for {evt_file_str}. HTTP Error: {e.code}. Likely no data available or station offline.")
            except Exception as e:
                self.log_msg(f"-> Network/Request Error: {e}")
            
            self.state['progress'] += 1
            self.log_msg(json.dumps({"progress": self.state['progress'], "total": self.state['total']}))
            
            time.sleep(3)

        self.log_msg('<br><strong style="color: #6f42c1; font-size: 1.1em; padding: 10px; border: 1px dashed #6f42c1; display: inline-block;">convert downloaded data\'s from app6 to search earthquake from here</strong><br>')
        
        self.log_msg(json.dumps({"done": True, "has_more": False}))
        self.state['is_running'] = False

    def generate_app2_config(self, config, target_save_dir, event_str, station, start_time_dt, end_time_dt):
        conf_out_path = Path(config.get('app2_config_dir', config.get('output_dir')))
        conf_out_path.mkdir(parents=True, exist_ok=True)
        
        app2_conf = {
            "app": "app2",
            "target-dir": str(target_save_dir),
            "start-hh": f"{start_time_dt.hour:02d}", "start-mm": f"{start_time_dt.minute:02d}", "start-ss": f"{start_time_dt.second + start_time_dt.microsecond / 1e6}",
            "end-hh": f"{end_time_dt.hour:02d}", "end-mm": f"{end_time_dt.minute:02d}", "end-ss": f"{end_time_dt.second + end_time_dt.microsecond / 1e6}",
            "filters": config.get('filters', []),
            "dampings": config.get('dampings', []),
            "draw-orig": "y" if config.get('draw_orig') else "n",
            "mark-extrema": "y" if config.get('mark_extrema') else "n",
            "keep-csv": "y" if config.get('keep_csv') else "n",
            "sep-plots": "y" if config.get('sep_plots') else "n",
            "comp-plots": "y" if config.get('comp_plots') else "n",
            "fft-plots": "n", 
            "resp-plots": "y" if config.get('resp_plots') else "n",
            "save-plots": "y" if config.get('save_plots') else "n",
            "axis-font-size": config.get('axis_font_size', 12),
            "title-font-size": config.get('title_font_size', 13),
            "custom_title_base": "",
            "notes-comments": f"Auto-generated from App 1 Search for {station} on {event_str}"
        }
        
        for ax in config.get('resp_axes', []): app2_conf[f"resp-ax-{ax}"] = True
            
        file_name = f"App2_Config_{station}_{event_str}.json"
        with open(conf_out_path / file_name, 'w') as f:
            json.dump(app2_conf, f, indent=4)

    def process_task(self, event_dt, station, config, parquet_folder, custom_dir_path):
        try:
            event_str = event_dt.strftime("%Y-%m-%d_%H-%M-%S")
            target_save_dir = parquet_folder / event_str / station
            start_time_dt = event_dt - pd.Timedelta(seconds=config['time_before'])
            end_time_dt = event_dt + pd.Timedelta(seconds=config['time_after'])
            
            curr = start_time_dt.replace(minute=0, second=0, microsecond=0)
            end = end_time_dt.replace(minute=0, second=0, microsecond=0)
            req_hours = []
            while curr <= end:
                req_hours.append(curr)
                curr += pd.Timedelta(hours=1)

            acquired_files = []
            s3_client = boto3.Session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=AWS_REGION).client('s3') if config.get('check_s3') and not custom_dir_path else None

            for req_hour in req_hours:
                hour_str = f"{req_hour.hour:02d}"
                file_acquired = False
                
                if target_save_dir.exists():
                    cached = [f for f in target_save_dir.glob("*.parquet") if f.stem[-2:] == hour_str]
                    if cached:
                        acquired_files.extend(cached)
                        continue

                if custom_dir_path and (custom_dir_path / event_str / station).exists():
                    for f in (custom_dir_path / event_str / station).glob("*.parquet"):
                        if f.stem[-2:] == hour_str:
                            acquired_files.append(f)
                            file_acquired = True
                            break
                            
                elif station in self.state['local_stations'] and Path(config['local_dir']).exists():
                    day_dir = Path(config['local_dir']) / station / "archive" / str(req_hour.year) / f"{req_hour.month:02d}" / f"{req_hour.day:02d}"
                    if day_dir.exists():
                        for f in day_dir.glob("*.parquet"):
                            if f.stem[-2:] == hour_str:
                                target_save_dir.mkdir(parents=True, exist_ok=True)
                                dest = target_save_dir / f.name
                                shutil.copy2(f, dest)
                                acquired_files.append(dest)
                                file_acquired = True
                                break

                if not file_acquired and s3_client and station in self.state['s3_stations']:
                    target_prefix = f"{PREFIX}{station}/data/{req_hour.year}/{req_hour.month:02d}/{req_hour.day:02d}/"
                    try:
                        resp = s3_client.list_objects_v2(Bucket=TARGET_BUCKET, Prefix=target_prefix)
                        if 'Contents' in resp:
                            for obj in resp['Contents']:
                                if obj['Key'].endswith('.parquet') and obj['Key'].rsplit('.', 1)[0][-2:] == hour_str:
                                    target_save_dir.mkdir(parents=True, exist_ok=True)
                                    dest = target_save_dir / obj['Key'].split('/')[-1].replace(':', '_')
                                    s3_client.download_file(TARGET_BUCKET, obj['Key'], str(dest))
                                    acquired_files.append(dest)
                                    break
                    except Exception: pass

            if not acquired_files: return

            dfs = [pd.read_parquet(f).iloc[:, 0:4] for f in acquired_files if not pd.read_parquet(f).empty]
            if not dfs: return
                
            df = pd.concat(dfs, ignore_index=True)
            df.columns = ['timestamp', 'x', 'y', 'z']
            df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s')
            mask = (df['timestamp_dt'] >= start_time_dt) & (df['timestamp_dt'] <= end_time_dt)
            df_segment = df[mask].copy().sort_values('timestamp_dt')
            
            if not df_segment.empty:
                process_and_plot_segment(df_segment, config, event_str, station, target_save_dir, start_time_dt, end_time_dt, self.log_msg)
                if config.get('gen_app2_config'):
                    self.generate_app2_config(config, target_save_dir, event_str, station, start_time_dt, end_time_dt)
                    
            del dfs, df, df_segment; gc.collect()
        except Exception as e:
            self.log_msg(f"[{event_dt} - {station}] Error: {e}")
        finally:
            self.state['progress'] += 1