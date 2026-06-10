import io, json, os, textwrap
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.fonttype'] = 'none' 
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

AWS_ACCESS_KEY = 
AWS_SECRET_KEY = 
AWS_REGION = 'ap-south-1'
TARGET_BUCKET = 'blca'
PREFIX = ''

STATION_LOCATIONS = {
    'blca1': 'BUET CE Building Room 537', 'blca2': '', 'blca3': 'BUET CE Building SM Lab',
    'blca4': 'SUST CE Department', 'blca5': '', 'blca6': 'BUET CE Building Room 537',
    'blca7': 'BAU, Mymansingh', 'blca8': 'BUET CE Building Room 537', 'blca9': 'SUST CE Department',
    'blca10': 'IEER CUET, Chittagong', 'blca11': '', 'blca13': '', 'blca14': '', 'blca15': '',
    'blca16': '', 'blca17': ''
}

TEMP_HTML_DIR = Path("temp_interactive_plots")

def parse_factor(f_str):
    if not isinstance(f_str, str): return float(f_str)
    f_str = f_str.strip()
    if not f_str: return 1.0
    try:
        if '/' in f_str:
            num, den = f_str.split('/', 1)
            den_f = float(den)
            if den_f == 0.0: return 1.0
            return float(num) / den_f
        elif '*' in f_str:
            num, den = f_str.split('*', 1)
            return float(num) * float(den)
        return float(f_str)
    except Exception:
        return 1.0

def mark_max_min(ax, x_vals, y_vals, config, font_size=9):
    if not config.get('mark_extrema'): return
    try:
        x_array = np.asarray(x_vals)
        y_array = np.asarray(y_vals)
        
        valid = ~pd.isna(y_array)
        if not np.any(valid): return
        
        x_valid = x_array[valid]
        y_valid = y_array[valid]
        
        max_idx = np.argmax(y_valid)
        min_idx = np.argmin(y_valid)
        
        x_max, y_max = x_valid[max_idx], y_valid[max_idx]
        x_min, y_min = x_valid[min_idx], y_valid[min_idx]
        
        ax.plot(x_max, y_max, marker='^', color='red', markersize=6, linestyle='None', zorder=10)
        ax.annotate(f'Max: {y_max:.3g}', xy=(x_max, y_max), xytext=(0, 5),
                    textcoords='offset points', ha='center', va='bottom',
                    fontsize=font_size, color='red', weight='bold', zorder=10)
        
        ax.plot(x_min, y_min, marker='v', color='blue', markersize=6, linestyle='None', zorder=10)
        ax.annotate(f'Min: {y_min:.3g}', xy=(x_min, y_min), xytext=(0, -5),
                    textcoords='offset points', ha='center', va='top',
                    fontsize=font_size, color='blue', weight='bold', zorder=10)
    except Exception:
        pass

def export_plotly_html(plot_type, data_payload, title, file_name, config=None):
    if config is None: config = {}
    font_size = config.get('axis_font_size', 12)
    title_font_size = config.get('title_font_size', 13)
    unit_name = config.get('unit_name', 'm/s²') if config.get('change_unit') else 'm/s²'
    
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        TEMP_HTML_DIR.mkdir(exist_ok=True)
        html_path = TEMP_HTML_DIR / f"{file_name}.html"
        
        def add_plotly_max_min(fig, x_vals, y_vals, row, col):
            if not config.get('mark_extrema'): return
            try:
                x_array = np.asarray(x_vals)
                y_array = np.asarray(y_vals)
                valid = ~pd.isna(y_array)
                if not np.any(valid): return
                
                x_valid = x_array[valid]
                y_valid = y_array[valid]
                
                max_idx = np.argmax(y_valid)
                min_idx = np.argmin(y_valid)
                
                fig.add_trace(go.Scattergl(x=[x_valid[max_idx]], y=[y_valid[max_idx]], mode='markers+text',
                                         text=[f'Max: {y_valid[max_idx]:.3g}'], textposition='top center',
                                         textfont=dict(color='red', size=10), marker=dict(color='red', symbol='triangle-up', size=8),
                                         showlegend=False), row=row, col=col)
                fig.add_trace(go.Scattergl(x=[x_valid[min_idx]], y=[y_valid[min_idx]], mode='markers+text',
                                         text=[f'Min: {y_valid[min_idx]:.3g}'], textposition='bottom center',
                                         textfont=dict(color='blue', size=10), marker=dict(color='blue', symbol='triangle-down', size=8),
                                         showlegend=False), row=row, col=col)
            except Exception:
                pass

        def subsample(df, n=50000):
            if len(df) > n: return df.iloc[::max(1, len(df)//n)]
            return df

        if plot_type == 'segment':
            df = subsample(data_payload)
            cols = ['x', 'y', 'z']
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05)
            for i, col in enumerate(cols):
                if col in df.columns:
                    x_val = df['timestamp_dt'] if 'timestamp_dt' in df.columns else df.index
                    fig.add_trace(go.Scattergl(x=x_val, y=df[col], name=col.upper(), mode='lines', line=dict(color=['#1f77b4', '#2ca02c', '#d62728'][i], width=1)), row=i+1, col=1)
                    add_plotly_max_min(fig, x_val, df[col], row=i+1, col=1)
                    fig.update_yaxes(title_text=f"Accel {col.upper()} ({unit_name})", fixedrange=True, title_font=dict(size=font_size), row=i+1, col=1)
            fig.update_layout(title=dict(text=title, font=dict(size=title_font_size)), hovermode='x unified', dragmode='zoom', height=800, template='plotly_white', showlegend=False)
            fig.update_xaxes(fixedrange=False, title_font=dict(size=font_size))
            fig.write_html(str(html_path), include_plotlyjs='cdn')
            return f"/view_html?path={html_path.name}"
            
        elif plot_type == 'spectrum':
            periods = data_payload['periods']
            spectra_dict = data_payload['spectra_dict']
            axes_list = list(spectra_dict.keys())
            num_axes = len(axes_list)
            
            fig = make_subplots(rows=num_axes, cols=1, shared_xaxes=True, vertical_spacing=0.05)
            
            for i, col in enumerate(axes_list):
                col_spectra = spectra_dict[col]
                for j, (dmp, psa) in enumerate(col_spectra.items()):
                    color = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'][j % 6]
                    show_leg = (i == 0) 
                    fig.add_trace(go.Scattergl(x=periods, y=psa, name=f"Dmp {dmp*100:.1f}%", legendgroup=f"dmp_{dmp}", showlegend=show_leg, mode='lines', line=dict(color=color, width=1.5)), row=i+1, col=1)
                    add_plotly_max_min(fig, periods, psa, row=i+1, col=1)
                fig.update_yaxes(title_text=f"PSA {col.upper()} ({unit_name})", fixedrange=True, title_font=dict(size=font_size), row=i+1, col=1)
                
            fig.update_layout(title=dict(text=title, font=dict(size=title_font_size)), hovermode='x unified', dragmode='zoom', height=300 * num_axes, template='plotly_white')
            fig.update_xaxes(title_text="Time Period (s)", fixedrange=False, title_font=dict(size=font_size), row=num_axes, col=1)
            fig.write_html(str(html_path), include_plotlyjs='cdn')
            return f"/view_html?path={html_path.name}"

        elif plot_type == 'fft':
            freqs = data_payload['freqs']
            amps_dict = data_payload['amps_dict']
            axes_list = list(amps_dict.keys())
            num_axes = len(axes_list)
            
            fig = make_subplots(rows=num_axes, cols=1, shared_xaxes=True, vertical_spacing=0.05)
            colors_map = {'x': '#1f77b4', 'y': '#2ca02c', 'z': '#d62728'}
            
            for i, col in enumerate(axes_list):
                line_color = colors_map.get(col, '#1f77b4')
                fig.add_trace(go.Scattergl(x=freqs, y=amps_dict[col], name=f"FFT {col.upper()}", mode='lines', line=dict(color=line_color, width=1.5)), row=i+1, col=1)
                add_plotly_max_min(fig, freqs, amps_dict[col], row=i+1, col=1)
                fig.update_yaxes(title_text=f"Amp {col.upper()}", fixedrange=True, title_font=dict(size=font_size), row=i+1, col=1)
                
            fig.update_layout(title=dict(text=title, font=dict(size=title_font_size)), hovermode='x unified', dragmode='zoom', height=250 * num_axes + 100, template='plotly_white', showlegend=False)
            fig.update_xaxes(title_text="Frequency (Hz)", fixedrange=False, title_font=dict(size=font_size), row=num_axes, col=1)
            fig.write_html(str(html_path), include_plotlyjs='cdn')
            return f"/view_html?path={html_path.name}"
            
        elif plot_type == 'compare_segment':
            num_profiles = len(data_payload)
            col = data_payload[0].get('col', 'x')
            fig = make_subplots(rows=num_profiles, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=[item['name'] for item in data_payload])
            for i, item in enumerate(data_payload):
                df = subsample(item['df'])
                if 'orig_df' in item:
                    orig_df = subsample(item['orig_df'])
                    fig.add_trace(go.Scattergl(x=orig_df['relative_time'], y=orig_df[col], name='Orig', mode='lines', line=dict(color='gray', width=1)), row=i+1, col=1)
                fig.add_trace(go.Scattergl(x=df['relative_time'], y=df[col], name=item['name'], mode='lines', line=dict(color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'][i % 5], width=1)), row=i+1, col=1)
                add_plotly_max_min(fig, df['relative_time'], df[col], row=i+1, col=1)
                fig.update_yaxes(title_text=item['name'], fixedrange=True, title_font=dict(size=font_size), row=i+1, col=1)
            fig.update_layout(title=dict(text=title, font=dict(size=title_font_size)), hovermode='x unified', dragmode='zoom', height=300 * num_profiles, template='plotly_white', showlegend=False)
            fig.update_xaxes(fixedrange=False, title_font=dict(size=font_size))
            fig.write_html(str(html_path), include_plotlyjs='cdn')
            return f"/view_html?path={html_path.name}"
            
        elif plot_type == 'compare_spectrum':
            num_profiles = len(data_payload)
            fig = make_subplots(rows=num_profiles, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=[item['name'] for item in data_payload])
            for i, item in enumerate(data_payload):
                if 'spectra' in item:
                    for j, (dmp, psa) in enumerate(item['spectra'].items()):
                        color = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'][j % 6]
                        fig.add_trace(go.Scattergl(x=item['periods'], y=psa, name=f"{item['name']} (Dmp {dmp*100:.1f}%)", mode='lines', line=dict(color=color, width=1)), row=i+1, col=1)
                        add_plotly_max_min(fig, item['periods'], psa, row=i+1, col=1)
                else:
                    fig.add_trace(go.Scattergl(x=item['periods'], y=item['psa'], name=item['name'], mode='lines', line=dict(color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'][i % 5], width=1)), row=i+1, col=1)
                    add_plotly_max_min(fig, item['periods'], item['psa'], row=i+1, col=1)
                fig.update_yaxes(title_text="PSA", fixedrange=True, title_font=dict(size=font_size), row=i+1, col=1)
            fig.update_layout(title=dict(text=title, font=dict(size=title_font_size)), hovermode='x unified', dragmode='zoom', height=300 * num_profiles, template='plotly_white', showlegend=True)
            fig.update_xaxes(title_text="Time Period (s)", fixedrange=False, title_font=dict(size=font_size))
            fig.write_html(str(html_path), include_plotlyjs='cdn')
            return f"/view_html?path={html_path.name}"

        elif plot_type == 'compare_fft':
            num_profiles = len(data_payload)
            fig = make_subplots(rows=num_profiles, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=[item['name'] for item in data_payload])
            for i, item in enumerate(data_payload):
                fig.add_trace(go.Scattergl(x=item['freqs'], y=item['amps'], name=item['name'], mode='lines', line=dict(color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'][i % 5], width=1)), row=i+1, col=1)
                add_plotly_max_min(fig, item['freqs'], item['amps'], row=i+1, col=1)
                fig.update_yaxes(title_text="Amplitude", fixedrange=True, title_font=dict(size=font_size), row=i+1, col=1)
            fig.update_layout(title=dict(text=title, font=dict(size=title_font_size)), hovermode='x unified', dragmode='zoom', height=300 * num_profiles, template='plotly_white', showlegend=False)
            fig.update_xaxes(title_text="Frequency (Hz)", fixedrange=False, title_font=dict(size=font_size))
            fig.write_html(str(html_path), include_plotlyjs='cdn')
            return f"/view_html?path={html_path.name}"
            
    except Exception as e:
        print(f"Plotly not available or failed: {e}")
    return ""

def parse_timestamps(text, log_msg_func):
    target_events = []
    lines = text.strip().split('\n')
    for line_num, line in enumerate(lines, 1):
        parts = line.strip().split()
        if len(parts) >= 2:
            try:
                dt = datetime.strptime(f"{parts[0]} {parts[1]}", "%m/%d/%Y %H:%M:%S")
                target_events.append(dt)
            except ValueError as e:
                log_msg_func(f"Warning: Could not parse line {line_num}: '{line}'. Error: {e}")
    return target_events

def fetch_s3_stations(s3_client, bucket_name, prefix, log_msg_func):
    stations = []
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix, Delimiter='/')
        for prefix_obj in response.get('CommonPrefixes', []):
            station_name = prefix_obj['Prefix'][len(prefix):].strip('/')
            stations.append(station_name)
    except Exception as e:
        log_msg_func(f"Error fetching stations from S3: {e}")
    return stations

def render_and_stream(fig, file_name, plot_title, config, target_save_dir, event_str, station, log_msg_func, html_url=""):
    title_font_size = config.get('title_font_size', 13)
    
    # Text wrapping applied here automatically for all matplotlib titles
    wrapped_title = "\n".join(textwrap.wrap(plot_title, width=110))
    fig.suptitle(wrapped_title, fontsize=title_font_size, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.94]) # Adjusted room for multiline titles
    
    if config.get('save_plots') and target_save_dir:
        target_save_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(target_save_dir / f"{file_name}.svg", format='svg', bbox_inches='tight')
        
    canvas = FigureCanvasAgg(fig)
    buf = io.StringIO()
    fig.savefig(buf, format='svg', bbox_inches='tight')
    svg_content = buf.getvalue()
    
    svg_start = svg_content.find('<svg')
    if svg_start != -1: svg_content = svg_content[svg_start:]
    
    payload = json.dumps({"svg": svg_content, "title": plot_title, "event_date": event_str, "station": station, "file_name": file_name, "html_url": html_url})
    log_msg_func(f"SVG_DATA|||{payload}")
    fig.clf()

def compute_response_spectrum(accel, dt, periods, damping=0.05):
    m_len = len(periods)
    omega = 2.0 * np.pi / periods
    damping = min(damping, 0.999)
    omega_d = omega * np.sqrt(1.0 - damping**2)
    xi = damping
    
    u = np.zeros(m_len)
    v = np.zeros(m_len)
    max_u = np.zeros(m_len)
    
    for i in range(len(accel) - 1):
        ug_ddot_0 = accel[i]
        ug_ddot_1 = accel[i+1]
        s = (ug_ddot_1 - ug_ddot_0) / dt
        E = -s / (omega**2)
        F = (1.0 / omega**2) * ((2.0 * xi / omega) * s - ug_ddot_0)
        C1 = u - F
        C2 = (v + xi * omega * C1 - E) / omega_d
        
        e_term = np.exp(-xi * omega * dt)
        cos_term = np.cos(omega_d * dt)
        sin_term = np.sin(omega_d * dt)
        
        u_next = e_term * (C1 * cos_term + C2 * sin_term) + E * dt + F
        v_next = -xi * omega * e_term * (C1 * cos_term + C2 * sin_term) + e_term * (-C1 * omega_d * sin_term + C2 * omega_d * cos_term) + E
                 
        u = u_next
        v = v_next
        max_u = np.maximum(max_u, np.abs(u))
        
    return max_u * omega**2

def process_and_plot_segment(df_segment, config, event_str, station, target_save_dir, start_time_dt, end_time_dt, log_msg_func):
    date_str = start_time_dt.strftime("%Y-%m-%d")
    time_start = start_time_dt.strftime('%H:%M:%S')
    time_end = end_time_dt.strftime('%H:%M:%S')
    seg_str = f"{start_time_dt.strftime('%H%M%S')}-{end_time_dt.strftime('%H%M%S')}"
    font_size = config.get('axis_font_size', 12)
    unit_name = config.get('unit_name', 'm/s²') if config.get('change_unit') else 'm/s²'
    
    custom_title_base = config.get('custom_title_base', '').strip()
    default_prefix = f"Station: {station} | Date: {date_str}"
    prefix = custom_title_base if custom_title_base else default_prefix
    title_base = f"{prefix} | Time: {time_start} to {time_end}"
    
    base_file_name = f"{station}_{date_str}_{seg_str}"

    if config.get('keep_csv') and target_save_dir:
        target_save_dir.mkdir(parents=True, exist_ok=True)
        df_segment.drop(columns=['timestamp_dt'], errors='ignore').to_csv(target_save_dir / f"{base_file_name}_Original.csv", index=False)

    colors_map = {'x': '#1f77b4', 'y': '#2ca02c', 'z': '#d62728'}
    dt = np.nanmedian(np.diff(df_segment['timestamp'].values))
    if np.isnan(dt) or dt <= 0: dt = 0.01

    def plot_response_spectrums(df_target, state_label, file_suffix):
        periods = np.linspace(0.01, 3.0, 300) 
        dampings = config.get('dampings', [0.0])
        resp_axes_choice = config.get('resp_axes', ['x'])
        if not resp_axes_choice: resp_axes_choice = ['x']
        
        spectra_data_csv = {'Period': periods} if (config.get('keep_csv') and target_save_dir) else None
        
        num_axes = len(resp_axes_choice)
        fig = Figure(figsize=(15, 3.5 * num_axes + 1))
        axes = fig.subplots(nrows=num_axes, ncols=1, sharex=True)
        if num_axes == 1: axes = [axes]
        
        plotly_spectra_dict = {}
        for i, col in enumerate(resp_axes_choice):
            ax = axes[i]
            accel_arr = df_target[col].values
            col_spectra = {}
            for dmp in dampings:
                psa = compute_response_spectrum(accel_arr, dt, periods, damping=dmp)
                col_spectra[dmp] = psa
                ax.plot(periods, psa, linewidth=1.5, label=f"Dmp: {dmp*100:.1f}%")
                mark_max_min(ax, periods, psa, config, font_size * 0.8)
                if spectra_data_csv is not None: spectra_data_csv[f"PSA_{col.upper()}_Dmp_{dmp*100:.1f}"] = psa
                
            ax.set_ylabel(f"PSA {col.upper()} ({unit_name})", fontsize=font_size)
            ax.grid(True, linestyle='--', alpha=0.7)
            if i == num_axes - 1:
                ax.set_xticks(np.arange(0, 3.1, 0.5))
            ax.set_xlim([0, 3.0])
            ax.legend(loc='upper right')
            plotly_spectra_dict[col] = col_spectra
            
        axes[-1].set_xlabel("Time Period (s)", fontsize=font_size)
        
        axes_str = "".join([c.upper() for c in resp_axes_choice])
        file_name = f"{base_file_name}_{file_suffix}_RespSpectrum_{axes_str}"
        
        plot_title = config.get('updated_titles', {}).get(file_name, f"{title_base} | {state_label} | Resp Spectrum Axes: {axes_str}")
        
        html_url = export_plotly_html('spectrum', {'periods': periods, 'spectra_dict': plotly_spectra_dict}, plot_title, file_name, config)
        render_and_stream(fig, file_name, plot_title, config, target_save_dir, event_str, station, log_msg_func, html_url)

        if spectra_data_csv is not None:
            pd.DataFrame(spectra_data_csv).to_csv(target_save_dir / f"{base_file_name}_{file_suffix}_RespSpectrum.csv", index=False)

    def plot_fft_spectrums(df_target, state_label, file_suffix):
        fft_axes_choice = config.get('fft_axes', ['x', 'y', 'z'])
        if not fft_axes_choice: fft_axes_choice = ['x', 'y', 'z']
        
        n_samples = len(df_target)
        freqs = np.fft.rfftfreq(n_samples, d=dt)
        fft_data_csv = {'Frequency': freqs} if (config.get('keep_csv') and target_save_dir) else None

        num_axes = len(fft_axes_choice)
        fig = Figure(figsize=(15, 3 * num_axes + 1))
        axes = fig.subplots(nrows=num_axes, ncols=1, sharex=True)
        if num_axes == 1: axes = [axes]
        
        plotly_amps = {}
        for i, col in enumerate(fft_axes_choice):
            ax = axes[i]
            amps = np.abs(np.fft.rfft(df_target[col].values)) * 2.0 / n_samples
            ax.plot(freqs, amps, linewidth=1.5, color=colors_map.get(col, '#1f77b4'))
            mark_max_min(ax, freqs, amps, config, font_size * 0.8)
            plotly_amps[col] = amps
            if fft_data_csv is not None: fft_data_csv[f"Amp_{col.upper()}"] = amps
            
            ax.set_ylabel(f"Amp {col.upper()}", fontsize=font_size)
            ax.grid(True, linestyle='--', alpha=0.7)
            
        axes[-1].set_xlabel("Frequency (Hz)", fontsize=font_size)
        
        axes_str = "".join([c.upper() for c in fft_axes_choice])
        file_name = f"{base_file_name}_{file_suffix}_FFT_{axes_str}"
        
        plot_title = config.get('updated_titles', {}).get(file_name, f"{title_base} | {state_label} | FFT Axes: {axes_str}")
        
        html_url = export_plotly_html('fft', {'freqs': freqs, 'amps_dict': plotly_amps}, plot_title, file_name, config)
        render_and_stream(fig, file_name, plot_title, config, target_save_dir, event_str, station, log_msg_func, html_url)

        if fft_data_csv is not None:
            pd.DataFrame(fft_data_csv).to_csv(target_save_dir / f"{base_file_name}_{file_suffix}_FFT.csv", index=False)

    if config.get('draw_orig'):
        fig = Figure(figsize=(15, 10))
        axes = fig.subplots(nrows=3, ncols=1, sharex=True)
        for i, col in enumerate(['x', 'y', 'z']):
            axes[i].plot(df_segment['timestamp_dt'], df_segment[col], color=colors_map[col], linewidth=0.5)
            mark_max_min(axes[i], df_segment['timestamp_dt'], df_segment[col], config, font_size * 0.8)
            axes[i].set_ylabel(f"Accel {col.upper()} ({unit_name})", fontsize=font_size)
            axes[i].grid(True, linestyle='--', alpha=0.7)
        axes[0].set_xlim([start_time_dt, end_time_dt])
        
        file_name = f"{base_file_name}_Original"
        plot_title = config.get('updated_titles', {}).get(file_name, f"{title_base} | Filter: None")
        
        html_url = export_plotly_html('segment', df_segment, plot_title, file_name, config)
        render_and_stream(fig, file_name, plot_title, config, target_save_dir, event_str, station, log_msg_func, html_url)

    if config.get('resp_plots'): plot_response_spectrums(df_segment, "Filter: None", "Orig")
    if config.get('fft_plots'): plot_fft_spectrums(df_segment, "Filter: None", "Orig")

    if bool(config.get('filters', [])) and (config.get('sep_plots') or config.get('comp_plots') or config.get('resp_plots') or config.get('fft_plots')):
        n_samples = len(df_segment)
        time_step = 1.0 / 100.0
        freqs = np.fft.rfftfreq(n_samples, d=time_step)
        fft_data = {col: np.fft.rfft(df_segment[col].values) for col in ['x', 'y', 'z']}

        for low_cut, high_cut in config.get('filters', []):
            filter_label = f"{low_cut}to{high_cut}Hz"
            mask_freq = (freqs >= low_cut) & (freqs <= high_cut)
            df_filtered = df_segment.copy()
            for col in ['x', 'y', 'z']:
                df_filtered[col] = np.fft.irfft(np.where(mask_freq, fft_data[col], 0), n=n_samples)

            if config.get('keep_csv') and target_save_dir:
                df_filtered.drop(columns=['timestamp_dt'], errors='ignore').to_csv(target_save_dir / f"{base_file_name}_Filtered_{filter_label}.csv", index=False)

            if config.get('sep_plots'):
                fig = Figure(figsize=(15, 10))
                axes = fig.subplots(nrows=3, ncols=1, sharex=True)
                for i, col in enumerate(['x', 'y', 'z']):
                    axes[i].plot(df_filtered['timestamp_dt'], df_filtered[col], color=colors_map[col], linewidth=1.2)
                    mark_max_min(axes[i], df_filtered['timestamp_dt'], df_filtered[col], config, font_size * 0.8)
                    axes[i].set_ylabel(f"Accel {col.upper()} ({unit_name})", fontsize=font_size)
                    axes[i].grid(True, linestyle='--', alpha=0.7)
                axes[0].set_xlim([start_time_dt, end_time_dt])
                
                file_name = f"{base_file_name}_Filtered_{filter_label}"
                plot_title = config.get('updated_titles', {}).get(file_name, f"{title_base} | Filter: {low_cut} to {high_cut}Hz")
                
                html_url = export_plotly_html('segment', df_filtered, plot_title, file_name, config)
                render_and_stream(fig, file_name, plot_title, config, target_save_dir, event_str, station, log_msg_func, html_url)

            if config.get('comp_plots'):
                fig = Figure(figsize=(15, 10))
                axes = fig.subplots(nrows=3, ncols=1, sharex=True)
                for i, col in enumerate(['x', 'y', 'z']):
                    axes[i].plot(df_segment['timestamp_dt'], df_segment[col], color='gray', linewidth=0.5, alpha=0.5, label='Original')
                    axes[i].plot(df_filtered['timestamp_dt'], df_filtered[col], color=colors_map[col], linewidth=1.2, label='Filtered')
                    mark_max_min(axes[i], df_filtered['timestamp_dt'], df_filtered[col], config, font_size * 0.8)
                    axes[i].set_ylabel(f"Accel {col.upper()} ({unit_name})", fontsize=font_size)
                    axes[i].grid(True, linestyle='--', alpha=0.7)
                    axes[i].legend(loc='upper right')
                axes[0].set_xlim([start_time_dt, end_time_dt])
                
                file_name = f"{base_file_name}_Comp_{filter_label}"
                plot_title = config.get('updated_titles', {}).get(file_name, f"{title_base} | Comp Filter: {low_cut} to {high_cut}Hz")
                
                render_and_stream(fig, file_name, plot_title, config, target_save_dir, event_str, station, log_msg_func, "")
                
            if config.get('resp_plots'): plot_response_spectrums(df_filtered, f"Filter: {low_cut} to {high_cut}Hz", f"Filt_{filter_label}")
            if config.get('fft_plots'): plot_fft_spectrums(df_filtered, f"Filter: {low_cut} to {high_cut}Hz", f"Filt_{filter_label}")
        
        del fft_data, df_filtered
    log_msg_func(f"[{event_str} - {station}] Processing completed successfully.")

def process_multi_compare(data_list, config, event_str, target_save_dir, log_msg_func):
    colors_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
    axes_to_plot = ['x', 'y', 'z']
    
    custom_title_base = config.get('custom_title_base', '').strip()
    default_prefix = " vs ".join([item['name'] for item in data_list])
    title_base = custom_title_base if custom_title_base else default_prefix
    
    font_size = config.get('axis_font_size', 12)

    def generate_compare_figure(col_target, plot_mode, source_list, title_fallback, file_name, dampings=None):
        if dampings is None: dampings = [0.0]
        num_profiles = len(source_list)
        fig = Figure(figsize=(15, 3.5 * num_profiles))
        axes = fig.subplots(num_profiles, 1, sharex=True)
        if num_profiles == 1: axes = [axes]
        
        plotly_payload = []
        
        for idx, item in enumerate(source_list):
            ax = axes[idx]
            c = colors_palette[idx % len(colors_palette)]
            
            if plot_mode == 'spectrum':
                periods = np.linspace(0.01, 3.0, 300)
                spectra_dict = {}
                for d_idx, dmp in enumerate(dampings):
                    psa = compute_response_spectrum(item['df'][col_target].values, item['dt'], periods, damping=dmp)
                    spectra_dict[dmp] = psa
                    d_color = colors_palette[d_idx % len(colors_palette)]
                    ax.plot(periods, psa, color=d_color, linewidth=1.5, label=f"Dmp: {dmp*100:.1f}%")
                    mark_max_min(ax, periods, psa, config, font_size * 0.8)
                ax.legend(loc='upper right')
                plotly_payload.append({'name': item['name'], 'periods': periods, 'spectra': spectra_dict, 'col': col_target})
                ax.set_xlim([0, 3.0])
                ax.set_xticks(np.arange(0, 3.1, 0.5))
                
            elif plot_mode == 'fft':
                n_samples = len(item['df'])
                freqs = np.fft.rfftfreq(n_samples, d=item['dt'])
                amps = np.abs(np.fft.rfft(item['df'][col_target].values)) * 2.0 / n_samples
                
                ax.plot(freqs, amps, color=c, linewidth=1.5, label=item['name'])
                mark_max_min(ax, freqs, amps, config, font_size * 0.8)
                plotly_payload.append({'name': item['name'], 'freqs': freqs, 'amps': amps, 'col': col_target})
                
            else: 
                if 'orig_df' in item:
                    ax.plot(item['orig_df']['relative_time'], item['orig_df'][col_target], color='gray', linewidth=0.5, alpha=0.5)
                    ax.plot(item['df']['relative_time'], item['df'][col_target], color=c, linewidth=1.2, label=item['name'] + ' (Filt)')
                    mark_max_min(ax, item['df']['relative_time'], item['df'][col_target], config, font_size * 0.8)
                    plotly_payload.append({'name': item['name'], 'df': item['df'], 'orig_df': item['orig_df'], 'col': col_target})
                else:
                    ax.plot(item['df']['relative_time'], item['df'][col_target], color=c, linewidth=1.0, label=item['name'])
                    mark_max_min(ax, item['df']['relative_time'], item['df'][col_target], config, font_size * 0.8)
                    plotly_payload.append({'name': item['name'], 'df': item['df'], 'col': col_target})
            
            ax.set_ylabel(item['name'], fontsize=font_size)
            ax.grid(True, linestyle='--', alpha=0.7)
        
        xlabel_text = "Time Period (s)" if plot_mode == 'spectrum' else ("Frequency (Hz)" if plot_mode == 'fft' else "Relative Time (s)")
        axes[-1].set_xlabel(xlabel_text, fontsize=font_size)
        
        plot_title = config.get('updated_titles', {}).get(file_name, title_fallback)
        
        plotly_type_map = {'segment': 'compare_segment', 'spectrum': 'compare_spectrum', 'fft': 'compare_fft'}
        html_url = export_plotly_html(plotly_type_map[plot_mode], plotly_payload, plot_title, file_name, config)
        render_and_stream(fig, file_name, plot_title, config, target_save_dir, event_str, "Compare", log_msg_func, html_url)

    if config.get('draw_orig'):
        for col in axes_to_plot:
            generate_compare_figure(col, 'segment', data_list, f"{title_base} | Original Plot | Axis: {col.upper()}", f"Compare_{event_str}_Orig_{col.upper()}")

    if config.get('resp_plots'):
        dampings_list = config.get('dampings', [0.0])
        for col in config.get('resp_axes', ['x']):
            generate_compare_figure(col, 'spectrum', data_list, f"{title_base} | Response Spectrum | Axis: {col.upper()}", f"Compare_{event_str}_Resp_{col.upper()}", dampings=dampings_list)

    if config.get('fft_plots'):
        for col in config.get('fft_axes', ['x', 'y', 'z']):
            generate_compare_figure(col, 'fft', data_list, f"{title_base} | FFT Plot | Axis: {col.upper()}", f"Compare_{event_str}_FFT_{col.upper()}")

    if bool(config.get('filters', [])):
        for low_cut, high_cut in config.get('filters'):
            filter_label = f"{low_cut}to{high_cut}Hz"
            filtered_data_list = []
            comp_data_list = []
            
            for item in data_list:
                n_samples = len(item['df'])
                freqs = np.fft.rfftfreq(n_samples, d=1.0/100.0)
                mask_freq = (freqs >= low_cut) & (freqs <= high_cut)
                df_filt = item['df'].copy()
                for col in axes_to_plot:
                    df_filt[col] = np.fft.irfft(np.where(mask_freq, np.fft.rfft(item['df'][col].values), 0), n=n_samples)
                filtered_data_list.append({'name': item['name'], 'df': df_filt, 'dt': item['dt']})
                comp_data_list.append({'name': item['name'], 'df': df_filt, 'orig_df': item['df'], 'dt': item['dt']})

            if config.get('sep_plots'):
                for col in axes_to_plot: generate_compare_figure(col, 'segment', filtered_data_list, f"{title_base} | Filtered: {low_cut} to {high_cut}Hz | Axis: {col.upper()}", f"Compare_{event_str}_Filt_{filter_label}_{col.upper()}")
            if config.get('comp_plots'):
                for col in axes_to_plot: generate_compare_figure(col, 'segment', comp_data_list, f"{title_base} | Comp (Orig vs Filt): {low_cut} to {high_cut}Hz | Axis: {col.upper()}", f"Compare_{event_str}_Comp_{filter_label}_{col.upper()}")
            if config.get('resp_plots'):
                dampings_list = config.get('dampings', [0.0])
                for col in config.get('resp_axes', ['x']): 
                    generate_compare_figure(col, 'spectrum', filtered_data_list, f"{title_base} | Filt Response Spectrum | Axis: {col.upper()} | {filter_label}", f"Compare_{event_str}_FiltResp_{filter_label}_{col.upper()}", dampings=dampings_list)
            if config.get('fft_plots'):
                for col in config.get('fft_axes', ['x', 'y', 'z']):
                    generate_compare_figure(col, 'fft', filtered_data_list, f"{title_base} | Filt FFT Plot | Axis: {col.upper()} | {filter_label}", f"Compare_{event_str}_FiltFFT_{filter_label}_{col.upper()}")