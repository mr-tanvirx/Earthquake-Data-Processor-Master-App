# processor_app9.py
import json
import gc
import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.fonttype'] = 'none'
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

TEMP_HTML_DIR = Path("temp_interactive_plots")

class App9Processor:
    APP_ID = "app9"
    APP_TITLE = "App 9: Resource Monitor Visualizer"

    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.state = {"is_running": False, "config": None, "devices_config": []}
        self.metrics_metadata = {
            'global_cpu_usage_percent': {'name': 'Global CPU Usage', 'unit': '%', 'color': '#1f77b4'},
            'global_cpu_temp_c': {'name': 'Global CPU Temperature', 'unit': '°C', 'color': '#d62728'},
            'global_memory_usage_percent': {'name': 'Global Memory Usage', 'unit': '%', 'color': '#2ca02c'},
            'global_disk_usage_percent': {'name': 'Global Disk Space Usage', 'unit': '%', 'color': '#7f7f7f'},
            'disk_read_speed_mb_s': {'name': 'Disk Read Speed', 'unit': 'MB/s', 'color': '#17becf'},
            'disk_write_speed_mb_s': {'name': 'Disk Write Speed', 'unit': 'MB/s', 'color': '#bcbd22'},
            'reader_ram_percent': {'name': 'Reader Process RAM Usage', 'unit': '%', 'color': '#9467bd'},
            'reader_swap_percent': {'name': 'Reader Process Swap Space', 'unit': '%', 'color': '#c5b0d5'},
            'writer_ram_percent': {'name': 'Writer Process RAM Usage', 'unit': '%', 'color': '#ff7f0e'},
            'writer_swap_percent': {'name': 'Writer Process Swap Space', 'unit': '%', 'color': '#ffbb78'},
            'monitor_ram_percent': {'name': 'Monitor Process RAM Usage', 'unit': '%', 'color': '#e377c2'},
            'monitor_swap_percent': {'name': 'Monitor Process Swap Space', 'unit': '%', 'color': '#f7b6d2'},
            'cpu_voltage_v': {'name': 'CPU Voltage', 'unit': 'V', 'color': '#8c564b'},
            'cpu_clock_mhz': {'name': 'CPU Clock Frequency', 'unit': 'MHz', 'color': '#393b79'},
            'undervoltage_now': {'name': 'Undervoltage Status Flag', 'unit': 'Flag', 'color': '#ad494a'},
            'frequency_capped_now': {'name': 'Frequency Throttled Status Flag', 'unit': 'Flag', 'color': '#e7ba52'}
        }

    def log_msg(self, msg):
        self.log_queue.put(msg)

    def get_html_template(self):
        checklist_html = ""
        for key, meta in self.metrics_metadata.items():
            checklist_html += f"""
            <label style="display: block; margin-bottom: 6px; font-weight: normal; cursor: pointer;">
                <input type="checkbox" class="a9-metric-checkbox" value="{key}" checked> {meta['name']} ({meta['unit']})
            </label>
            """

        return f"""
        <div class="grid-layout" id="form-app9">
            <div class="section-card" style="border: 2px solid #007bff; grid-column: span 2;">
                <div class="section-title">
                    <span>Log Target Registry Manager</span>
                    <button type="button" class="btn-small" onclick="addA9DeviceRow()" style="margin: 0; background: #007bff;">+ Add Another Device to Compare</button>
                </div>
                <div id="a9-devices-container" style="display: flex; flex-direction: column; gap: 15px; margin-top: 10px;">
                    <!-- Dynamic Device Rows Injected Here -->
                </div>
            </div>
        </div>
        
        <div class="grid-layout">
            <div class="section-card">
                <div class="section-title">Time Bounds Selection</div>
                <div class="input-group">
                    <label>Extract Windows Bounds (hh:mm:ss)</label>
                    <div class="inline-inputs">
                        <span>From</span>
                        <input type="number" id="a9-sh" class="a9-dt" placeholder="hh" min="0" max="23"> :
                        <input type="number" id="a9-sm" class="a9-dt" placeholder="mm" min="0" max="59"> :
                        <input type="number" id="a9-ss" class="a9-dt" placeholder="ss" min="0" step="any">
                    </div>
                    <div class="inline-inputs" style="margin-top: 10px;">
                        <span>To</span>&nbsp;&nbsp;&nbsp;&nbsp;
                        <input type="number" id="a9-eh" class="a9-dt" placeholder="hh" min="0" max="23"> :
                        <input type="number" id="a9-em" class="a9-dt" placeholder="mm" min="0" max="59"> :
                        <input type="number" id="a9-es" class="a9-dt" placeholder="ss" min="0" step="any">
                    </div>
                    <div class="duration-box" id="a9-duration">Duration: Auto (Full Log Segment)</div>
                </div>
                <div class="input-group" style="margin-top: 15px;">
                    <label>Custom Plot Title Base (Optional)</label>
                    <input type="text" id="a9-custom-title" placeholder="e.g., Cross-Platform Infrastructure Performance Analysis">
                </div>
            </div>

            <div class="section-card" style="border: 2px solid #28a745;">
                <div class="section-title">System Metrics Selection Framework</div>
                <div style="max-height: 250px; overflow-y: auto; padding: 10px; background: var(--bg-color); border-radius: 6px;">
                    {checklist_html}
                </div>
            </div>
        </div>

        <div class="grid-layout">
            <div class="section-card" style="grid-column: span 2;">
                <div class="section-title">Statistical Indicators & Annotation Overlays</div>
                <div style="display: flex; flex-wrap: wrap; gap: 20px; margin-top: 10px;">
                    <label style="font-weight: bold; cursor: pointer; color: #1f77b4;">
                        <input type="checkbox" id="a9-show-original" checked> Overlay Raw Original Data Trace
                    </label>
                    <label style="font-weight: bold; cursor: pointer; color: #d62728;">
                        <input type="checkbox" id="a9-show-extrema"> Annotate Maximum & Minimum Value Markers
                    </label>
                    <label style="font-weight: bold; cursor: pointer; color: #2ca02c;">
                        <input type="checkbox" id="a9-show-avg"> Overlay Horizontal Baseline Evaluation Mean Average Lines
                    </label>
                    <label style="font-weight: bold; cursor: pointer; color: #ff7f0e;">
                        <input type="checkbox" id="a9-show-moving-avg"> Overlay Dynamic Rolling Moving Average Trend Lines
                    </label>
                    <div class="inline-inputs" style="margin: 0;">
                        <span style="font-size: 0.9em; font-weight: 600;">Window (Mins):</span>
                        <input type="number" id="a9-moving-avg-mins" value="30" min="1" max="1440" style="width: 70px; padding: 4px;">
                    </div>
                </div>
                
                <div class="settings-grid" style="margin-top: 20px; border-top: 1px solid var(--border-color); padding-top: 15px;">
                    <div class="input-group"><label>Axis Font Size</label><input type="number" id="a9-axis-font" value="11"></div>
                    <div class="input-group"><label>Title Font Size</label><input type="number" id="a9-title-font" value="13"></div>
                    <div class="input-group">
                        <label>Save Clean SVGs</label>
                        <div class="radio-group">
                            <label><input type="radio" name="a9_save" class="save-plots" value="y"> Y</label>
                            <label><input type="radio" name="a9_save" class="save-plots" value="n" checked> N</label>
                        </div>
                    </div>
                    <div class="input-group">
                        <label>Export CSV Slices</label>
                        <div class="radio-group">
                            <label><input type="radio" name="a9_csv" class="keep-csv" value="y"> Y</label>
                            <label><input type="radio" name="a9_csv" class="keep-csv" value="n" checked> N</label>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <button class="btn-large init-btn" onclick="run_app9()">Initialize Integrated Performance Plotter</button>
        """

    def get_js_funcs(self):
        return """
        let a9DeviceCount = 0;
        function addA9DeviceRow(dataObj = null) {
            a9DeviceCount++;
            const id = a9DeviceCount;
            const container = document.getElementById('a9-devices-container');
            const row = document.createElement('div');
            row.className = 'compare-row a9-device-box';
            row.id = `a9-dev-row-${id}`;
            row.style.position = 'relative';
            row.style.padding = '15px';
            row.style.border = '1px dashed var(--border-color)';
            row.style.borderRadius = '6px';
            
            row.innerHTML = `
                ${id > 1 ? '<button type="button" class="remove-row-btn" style="position:absolute; top:10px; right:10px; background:#dc3545; padding:4px 8px; font-size:0.8em;" onclick="document.getElementById(\\'a9-dev-row-${id}\\').remove()">X Remove</button>' : ''}
                <div style="display:grid; grid-template-columns: 1fr 2fr 1fr; gap:15px; align-items:center;">
                    <div class="input-group" style="margin:0;"><label>Device Label / Identifier</label><input type="text" class="a9-dev-name" placeholder="e.g., Edge Server Alpha" value="${dataObj?.name || 'Device ' + id}"></div>
                    <div class="input-group" style="margin:0;"><label>Log Target Directory Path</label><input type="text" class="a9-dev-dir" placeholder="e.g., C:\\Logs\\Device1" value="${dataObj?.target_dir || ''}"></div>
                    <div class="input-group" style="margin:0;"><label>Date Selection Filter (DD-MM-YYYY)</label><input type="text" class="a9-dev-date" placeholder="e.g., 15-07-2026 (Optional)" value="${dataObj?.date_match || ''}"></div>
                </div>
            `;
            container.appendChild(row);
        }

        // Auto-initialize primary tracking box layer block
        setTimeout(() => {
            const container = document.getElementById('a9-devices-container');
            if (container && container.children.length === 0) {
                addA9DeviceRow();
            }
        }, 100);

        function run_app9() {
            const pane = document.getElementById('tab-app9');
            
            const selectedMetrics = [];
            pane.querySelectorAll('.a9-metric-checkbox:checked').forEach(cb => {
                selectedMetrics.push(cb.value);
            });
            
            if (selectedMetrics.length === 0) {
                alert("Please select at least one tracking variable column metric block to evaluate plots.");
                return;
            }

            const devices = [];
            pane.querySelectorAll('.a9-device-box').forEach(box => {
                const nameVal = box.querySelector('.a9-dev-name').value.trim() || box.querySelector('.a9-dev-name').value;
                const dirVal = box.querySelector('.a9-dev-dir').value.trim() || box.querySelector('.a9-dev-dir').value;
                const dateVal = box.querySelector('.a9-dev-date').value.trim() || box.querySelector('.a9-dev-date').value;
                if (dirVal) {
                    devices.push({ name: nameVal, target_dir: dirVal, date_match: dateVal });
                }
            });

            if (devices.length === 0) {
                alert("Please specify at least one valid log directory path mapping layout.");
                return;
            }

            const payload = {
                devices: devices,
                custom_title_base: document.getElementById('a9-custom-title').value,
                start_hh: document.getElementById('a9-sh').value,
                start_mm: document.getElementById('a9-sm').value,
                start_ss: document.getElementById('a9-ss').value,
                end_hh: document.getElementById('a9-eh').value,
                end_mm: document.getElementById('a9-em').value,
                end_ss: document.getElementById('a9-es').value,
                selected_metrics: selectedMetrics,
                show_original: document.getElementById('a9-show-original').checked,
                show_extrema: document.getElementById('a9-show-extrema').checked,
                show_avg: document.getElementById('a9-show-avg').checked,
                show_moving_avg: document.getElementById('a9-show-moving-avg').checked,
                moving_avg_mins: parseInt(document.getElementById('a9-moving-avg-mins').value || 30),
                save_plots: pane.querySelector('.save-plots:checked')?.value === 'y',
                keep_csv: pane.querySelector('.keep-csv:checked')?.value === 'y',
                axis_font_size: parseInt(document.getElementById('a9-axis-font').value || 11),
                title_font_size: parseInt(document.getElementById('a9-title-font').value || 13)
            };
            executeAppWorkflow('app9', payload);
        }
        """

    def initialize(self, config):
        devices_input = config.get('devices', [])
        valid_devices_config = []

        for idx, dev in enumerate(devices_input):
            target_dir = Path(dev['target_dir'])
            if not target_dir.exists() or not target_dir.is_dir():
                self.log_msg(f"Warning: Directory configuration for profile '{dev['name']}' could not be resolved.")
                continue

            date_match = dev.get('date_match', '').strip()
            all_files = list(target_dir.glob("*.csv"))
            matched_files = [f for f in all_files if date_match in f.name] if date_match else all_files

            if not matched_files:
                self.log_msg(f"Warning: No valid monitoring logs located inside path mapping for '{dev['name']}'.")
                continue

            valid_devices_config.append({
                'name': dev['name'],
                'target_dir': target_dir,
                'files': sorted(matched_files)
            })

        if not valid_devices_config:
            self.log_msg("Error: No performance record profiles matched base operational parameters.")
            return {"status": "Error"}

        self.state['devices_config'] = valid_devices_config
        self.state['config'] = config
        return {"status": "Initialized"}

    def start_page_thread(self):
        self.state['is_running'] = True
        self.state['total'] = 1
        self.state['progress'] = 0
        try:
            self.process_logs()
        except Exception as e:
            self.log_msg(f"Fatal background visualizer execution error: {str(e)}")
        finally:
            self.state['progress'] = 1
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False

    def export_plotly_unified_html(self, devices_data, selected_metrics, title, file_name, config):
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            TEMP_HTML_DIR.mkdir(exist_ok=True)
            html_path = TEMP_HTML_DIR / f"{file_name}.html"

            moving_avg_mins = int(config.get('moving_avg_mins', 30))
            
            # Construct subplot layout stacking devices sequentially underneath each variable category
            subplot_sequences = []
            for metric_key in selected_metrics:
                metric_name = self.metrics_metadata[metric_key]['name']
                for dev in devices_data:
                    subplot_sequences.append(f"{metric_name} [{dev['name']}]")

            total_rows = len(subplot_sequences)
            fig = make_subplots(
                rows=total_rows, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=max(0.01, 0.35 / total_rows),
                subplot_titles=subplot_sequences
            )

            current_row = 1
            for metric_key in selected_metrics:
                meta = self.metrics_metadata[metric_key]
                for dev in devices_data:
                    df = dev['df']
                    x_vals = df['timestamp_dt']
                    y_vals = df[metric_key]

                    # Overlay primary processing paths traces
                    if config.get('show_original', True):
                        fig.add_trace(go.Scattergl(
                            x=x_vals, y=y_vals, 
                            name=f"{dev['name']} Raw", 
                            mode='lines', 
                            line=dict(color=meta['color'], width=1.5)
                        ), row=current_row, col=1)

                    # Dynamic time-based calculation window rolling trendline logic
                    if config.get('show_moving_avg') and not y_vals.empty:
                        moving_avg = pd.Series(y_vals.values, index=x_vals).rolling(window=f"{moving_avg_mins}min", min_periods=1).mean()
                        fig.add_trace(go.Scattergl(
                            x=x_vals, y=moving_avg,
                            name=f"{dev['name']} ({moving_avg_mins}m SMA)",
                            mode='lines',
                            line=dict(color='#ff7f0e', width=1.5, dash='dash')
                        ), row=current_row, col=1)

                    # Compute maximum and minimum extrema locations boundaries markers
                    if config.get('show_extrema') and not y_vals.empty:
                        max_idx = y_vals.idxmax()
                        min_idx = y_vals.idxmin()
                        
                        fig.add_trace(go.Scattergl(
                            x=[x_vals.iloc[max_idx]], y=[y_vals.iloc[max_idx]],
                            mode='markers+text', text=[f"Max: {y_vals.iloc[max_idx]:.4g}"],
                            textposition="top center", marker=dict(color='red', size=8, symbol='triangle-up'),
                            showlegend=False
                        ), row=current_row, col=1)
                        
                        fig.add_trace(go.Scattergl(
                            x=[x_vals.iloc[min_idx]], y=[y_vals.iloc[min_idx]],
                            mode='markers+text', text=[f"Min: {y_vals.iloc[min_idx]:.4g}"],
                            textposition="bottom center", marker=dict(color='blue', size=8, symbol='triangle-down'),
                            showlegend=False
                        ), row=current_row, col=1)

                    # Overlay horizontal math evaluation mean lines references
                    if config.get('show_avg') and not y_vals.empty:
                        mean_val = y_vals.mean()
                        fig.add_shape(
                            type="line", x0=x_vals.min(), x1=x_vals.max(), y0=mean_val, y1=mean_val,
                            line=dict(color="green", width=1.5, dash="dashdot"), row=current_row, col=1
                        )
                        fig.add_trace(go.Scattergl(
                            x=[x_vals.iloc[len(x_vals)//2]], y=[mean_val],
                            mode='text', text=[f"Avg: {mean_val:.4g}"],
                            textposition="top center", showlegend=False
                        ), row=current_row, col=1)

                    fig.update_yaxes(title_text=meta['unit'], fixedrange=True, row=current_row, col=1)
                    current_row += 1

            fig.update_layout(
                title=dict(text=title, font=dict(size=config.get('title_font_size', 13))),
                hovermode='x unified', dragmode='zoom', 
                template='plotly_white', height=max(500, 220 * total_rows)
            )
            fig.update_xaxes(fixedrange=False)

            fig.write_html(str(html_path), include_plotlyjs='cdn')
            return f"/view_html?path={html_path.name}"
        except Exception as e:
            self.log_msg(f"Plotly dynamic unified comparative asset crash: {str(e)}")
        return ""

    def process_logs(self):
        config = self.state['config']
        devices_config = self.state['devices_config']
        selected_metrics = config.get('selected_metrics', [])
        moving_avg_mins = int(config.get('moving_avg_mins', 30))

        sh, sm, ss = config.get('start_hh'), config.get('start_mm'), config.get('start_ss')
        eh, em, es = config.get('end_hh'), config.get('end_mm'), config.get('end_ss')
        has_start = all(x not in ["", None] for x in [sh, sm, ss])
        has_end = all(x not in ["", None] for x in [eh, em, es])

        devices_data = []
        global_start_time = None
        global_end_time = None

        # Parse and segment logs for each configured system location block independently
        for dev in devices_config:
            self.log_msg(f"Processing database records stack for target: '{dev['name']}'")
            dfs = []
            for file_path in dev['files']:
                try:
                    df_part = pd.read_csv(file_path, sep=None, engine='python', on_bad_lines='skip')
                    if not df_part.empty:
                        dfs.append(df_part)
                except Exception as ex:
                    self.log_msg(f"Bypassing corrupt entry block structural alignment file {file_path.name}: {str(ex)}")

            if not dfs:
                continue

            df = pd.concat(dfs, ignore_index=True)
            df.columns = [c.strip() for c in df.columns]

            if 'timestamp' not in df.columns:
                self.log_msg(f"Structural target abort: Data profile for '{dev['name']}' lacks 'timestamp' header rows mapping indicators.")
                continue

            df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.dropna(subset=['timestamp_dt']).sort_values('timestamp_dt')

            base_date = df['timestamp_dt'].min().floor('D')
            start_time_dt = base_date + pd.Timedelta(hours=int(sh), minutes=int(sm), seconds=float(ss)) if has_start else df['timestamp_dt'].min()
            end_time_dt = base_date + pd.Timedelta(hours=int(eh), minutes=int(em), seconds=float(es)) if has_end else df['timestamp_dt'].max()
            if has_end and end_time_dt < start_time_dt:
                end_time_dt += pd.Timedelta(days=1)

            mask = (df['timestamp_dt'] >= start_time_dt) & (df['timestamp_dt'] <= end_time_dt)
            df_segment = df[mask].copy().reset_index(drop=True)

            if df_segment.empty:
                self.log_msg(f"Zero bounded performance records overlap captured inside indices boundary logs for '{dev['name']}'.")
                continue

            # Ensure strict variable normalization across selected elements arrays
            for key in selected_metrics:
                if key in df_segment.columns:
                    df_segment[key] = pd.to_numeric(df_segment[key], errors='coerce').fillna(0.0)
                else:
                    df_segment[key] = 0.0

            devices_data.append({
                'name': dev['name'],
                'df': df_segment
            })

            # Sync timeline boundary configurations for absolute plotting bounds
            if global_start_time is None or start_time_dt < global_start_time:
                global_start_time = start_time_dt
            if global_end_time is None or end_time_dt > global_end_time:
                global_end_time = end_time_dt

            if config.get('keep_csv'):
                export_name = f"CompareSlice_{dev['name']}_{base_date.strftime('%Y-%m-%d')}_{window_str if 'window_str' in locals() else 'extracted'}.csv"
                df_segment.drop(columns=['timestamp_dt'], errors='ignore').to_csv(dev['target_dir'] / export_name, index=False)

        if not devices_data:
            self.log_msg("Error: Bounded computational routines compiled zero target datasets structures configurations blocks.")
            return

        date_str = global_start_time.strftime("%Y-%m-%d") if global_start_time else "Comparative"
        custom_title_base = config.get('custom_title_base', '').strip()
        prefix = custom_title_base if custom_title_base else f"Resource Multi-Device Compare Trace ({date_str})"
        plot_title = f"{prefix} | Window Range: {global_start_time.strftime('%H:%M:%S')} to {global_end_time.strftime('%H:%M:%S')}"
        file_base_name = f"MultiDevice_Report_{date_str}_{datetime.now().strftime('%H%M%S')}"

        # 1. Compile Plotly Interactive Zoomable Unified Subplot Stack Frame
        html_url = self.export_plotly_unified_html(devices_data, selected_metrics, plot_title, file_base_name, config)

        # 2. Compile Matplotlib Shared X-Axis Comparative Subplot Vector Array
        axis_font = config.get('axis_font_size', 11)
        title_font = config.get('title_font_size', 13)
        
        num_metrics = len(selected_metrics)
        num_devices = len(devices_data)
        total_rows = num_metrics * num_devices

        fig = Figure(figsize=(16, max(4.0, 2.3 * total_rows + 1.5)))
        axes = fig.subplots(nrows=total_rows, ncols=1, sharex=True)
        if total_rows == 1:
            axes = [axes]

        current_row_idx = 0
        for metric_key in selected_metrics:
            meta = self.metrics_metadata[metric_key]
            for dev in devices_data:
                ax = axes[current_row_idx]
                df_dev = dev['df']
                x_vals = df_dev['timestamp_dt']
                y_vals = df_dev[metric_key].values

                # Draw raw configuration lines paths tracking values bounds layers
                if config.get('show_original', True):
                    ax.plot(x_vals, y_vals, color=meta['color'], linewidth=1.2, label=f"{dev['name']} Raw")

                # Track Moving Averages calculations inside each distinct block
                if config.get('show_moving_avg') and len(y_vals) > 0:
                    moving_avg = pd.Series(y_vals, index=x_vals).rolling(window=f"{moving_avg_mins}min", min_periods=1).mean().values
                    ax.plot(x_vals, moving_avg, color='#ff7f0e', linestyle='--', linewidth=1.2, label=f'SMA ({moving_avg_mins}m)')

                # Process Maximum & Minimum markers points indices
                if config.get('show_extrema') and len(y_vals) > 0:
                    max_idx = np.argmax(y_vals)
                    min_idx = np.argmin(y_vals)
                    
                    ax.plot(x_vals.iloc[max_idx], y_vals[max_idx], marker='^', color='red', markersize=6, linestyle='None', zorder=5)
                    ax.annotate(f"Max: {y_vals[max_idx]:.4g}", xy=(x_vals.iloc[max_idx], y_vals[max_idx]), 
                                xytext=(0, 4), textcoords='offset points', ha='center', va='bottom', color='red', weight='bold', fontsize=axis_font-3)
                    
                    ax.plot(x_vals.iloc[min_idx], y_vals[min_idx], marker='v', color='blue', markersize=6, linestyle='None', zorder=5)
                    ax.annotate(f"Min: {y_vals[min_idx]:.4g}", xy=(x_vals.iloc[min_idx], y_vals[min_idx]), 
                                xytext=(0, -4), textcoords='offset points', ha='center', va='top', color='blue', weight='bold', fontsize=axis_font-3)

                # Process Mean average baseline layouts vectors
                if config.get('show_avg') and len(y_vals) > 0:
                    mean_val = np.mean(y_vals)
                    ax.axhline(mean_val, color='green', linestyle='-.', linewidth=1.2, alpha=0.8, label=f"Mean ({mean_val:.4g})")

                if (config.get('show_original', True) or config.get('show_avg') or config.get('show_moving_avg')) and len(y_vals) > 0:
                    ax.legend(loc='upper right', fontsize=axis_font-3)

                ax.set_ylabel(f"[{dev['name']}]\n{meta['name']} ({meta['unit']})", fontsize=axis_font-2)
                ax.grid(True, linestyle='--', alpha=0.5)
                current_row_idx += 1

        axes[-1].set_xlabel("Integrated Shared Log Timeline Axis Tracking", fontsize=axis_font)
        
        # Pull global timeline limits across available active parameters frames pools
        all_min_x = min([d['df']['timestamp_dt'].min() for d in devices_data])
        all_max_x = max([d['df']['timestamp_dt'].max() for d in devices_data])
        axes[0].set_xlim([all_min_x, all_max_x])

        fig.suptitle(plot_title, fontsize=title_font, fontweight='bold')
        fig.tight_layout(rect=[0, 0, 1, 0.97])

        if config.get('save_plots'):
            first_dev_dir = devices_config[0]['target_dir']
            fig.savefig(first_dev_dir / f"{file_base_name}.svg", format='svg', bbox_inches='tight')

        # Stream vector graphics array context out back to frontend framework engines
        canvas = FigureCanvasAgg(fig)
        import io
        buf = io.StringIO()
        fig.savefig(buf, format='svg', bbox_inches='tight')
        svg_content = buf.getvalue()
        
        svg_start_idx = svg_content.find('<svg')
        if svg_start_idx != -1: 
            svg_content = svg_content[svg_start_idx:]

        payload = json.dumps({
            "svg": svg_content, 
            "title": plot_title, 
            "event_date": date_str, 
            "station": "Multi-Device Unified Infrastructure Compare Mode", 
            "file_name": file_base_name, 
            "html_url": html_url
        })
        
        self.log_msg(f"SVG_DATA|||{payload}")
        self.log_msg("Comparative metric evaluations complete. Data structured inside single chart window layer matrix successfully.")
        
        fig.clf()
        del devices_data; gc.collect()