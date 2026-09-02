import os, sys, importlib, inspect, threading, queue, json, webbrowser, shutil, socket
from pathlib import Path
from flask import Flask, request, jsonify, Response, render_template_string, send_from_directory, send_file

app = Flask(__name__)
log_queue = queue.Queue()
app_processors = {}

# Clean & Prepare Interactive Plot Directory
TEMP_HTML_DIR = Path("temp_interactive_plots")
if TEMP_HTML_DIR.exists(): shutil.rmtree(TEMP_HTML_DIR, ignore_errors=True)
TEMP_HTML_DIR.mkdir(exist_ok=True)

if '.' not in sys.path:
    sys.path.insert(0, '.')

for filename in os.listdir('.'):
    if filename.startswith('processor_app') and filename.endswith('.py'):
        module_name = filename[:-3]
        try:
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, 'APP_ID') and hasattr(obj, 'APP_TITLE'):
                    app_processors[obj.APP_ID] = obj(log_queue)
        except Exception as e:
            print(f"Failed to load module {filename}: {e}")

sorted_apps = sorted(app_processors.items(), key=lambda x: x[0])

tabs_html = ""
panes_html = ""
js_scripts = ""

for i, (app_id, app_obj) in enumerate(sorted_apps):
    active_class = "active" if i == 0 else ""
    tabs_html += f'<button class="tab-btn {active_class}" onclick="openTab(\'{app_id}\')">{app_obj.APP_TITLE}</button>\n'
    panes_html += f'<div id="tab-{app_id}" class="tab-pane {active_class}">{app_obj.get_html_template()}</div>\n'
    if hasattr(app_obj, 'get_js_funcs'):
        js_scripts += app_obj.get_js_funcs() + "\n"

HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html>
<head>
    <title>BLCSN Data Process Software by mr-tanvirx</title>
    <style>
        :root {{ --bg-color: #f4f6f9; --text-color: #333; --header-bg: #2c3e50; --card-bg: white; --border-color: #ced4da; --tab-bg: #e9ecef; --tab-hover: #d3d9df; --input-bg: white; --input-text: #333; --station-header: #e9ecef; --log-bg: #1e1e1e; --duration-bg: #e2e3e5; --duration-text: #383d41; }}
        body.dark-mode {{ --bg-color: #121212; --text-color: #e0e0e0; --header-bg: #000000; --card-bg: #1e1e1e; --border-color: #333333; --tab-bg: #2c2c2c; --tab-hover: #3d3d3d; --input-bg: #2c2c2c; --input-text: #e0e0e0; --station-header: #2c2c2c; --log-bg: #000000; --duration-bg: #2c2c2c; --duration-text: #ffc107; }}
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; background: var(--bg-color); color: var(--text-color); transition: 0.3s; }}
        
        .header {{ 
            background: var(--header-bg); 
            color: white; 
            padding: 20px; 
            display: flex;
            align-items: center;
            justify-content: flex-start;
            position: relative; 
            min-height: 50px;
        }}
        .brand-container {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .logo-img {{
            height: 45px;
            width: 45px;
            object-fit: contain;
        }}
        .title-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            line-height: 1.2;
        }}
        .main-title-text {{
            font-weight: bold; 
            font-size: 1.35em;
        }}
        .subscript-author {{
            font-size: 0.55em;
            font-weight: normal;
            color: #a0aab2;
            margin-top: 2px;
        }}
        .subscript-author a {{
            color: #4da3ff; 
            text-decoration: none;
        }}
        .subscript-author a:hover {{
            text-decoration: underline;
        }}
        
        .theme-toggle-btn {{ position: absolute; right: 20px; top: 50%; transform: translateY(-50%); background: #007bff; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; font-weight: bold; }}
        .theme-toggle-btn:hover {{ background: #0056b3; }}
        .container {{ max-width: 1200px; margin: auto; padding: 20px; }}
        .tab-nav {{ display: flex; gap: 10px; margin-bottom: 25px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px; flex-wrap: wrap; }}
        .tab-btn {{ padding: 12px 20px; cursor: pointer; background: var(--tab-bg); border: none; border-radius: 8px 8px 0 0; font-size: 1em; font-weight: bold; color: var(--text-color); transition: 0.2s; }}
        .tab-btn:hover {{ background: var(--tab-hover); }}
        .tab-btn.active {{ background: #007bff; color: white; }}
        .tab-pane {{ display: none; }}
        .tab-pane.active {{ display: block; animation: fadeIn 0.3s ease; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(5px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .grid-layout {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
        .section-card {{ background: var(--card-bg); padding: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid var(--border-color); }}
        .section-title {{ font-size: 1.1em; font-weight: bold; margin-bottom: 15px; color: #007bff; display: flex; align-items: center; gap: 8px; justify-content: space-between; }}
        .section-title::before {{ content: ""; display: block; width: 4px; height: 18px; background: #007bff; border-radius: 2px; }}
        .input-group {{ margin-bottom: 15px; }}
        label {{ display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9em; color: var(--text-color); }}
        input[type="text"], input[type="number"], textarea {{ width: 100%; padding: 10px; box-sizing: border-box; border: 1px solid var(--border-color); border-radius: 6px; background: var(--input-bg); color: var(--input-text); }}
        .inline-inputs {{ display: flex; gap: 8px; align-items: center; }}
        .inline-inputs input[type="number"] {{ width: 70px; }}
        .filter-row {{ display: flex; gap: 10px; align-items: center; margin-bottom: 8px; }}
        .filter-row input {{ width: 100px; }}
        .radio-group {{ display: flex; gap: 15px; margin-top: 5px; }}
        .settings-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
        button {{ padding: 10px 15px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 6px; font-weight: bold; }}
        button:hover {{ background: #0056b3; }}
        .btn-large {{ width: 100%; font-size: 1.2em; padding: 15px; background: #28a745; margin-top: 20px; }}
        .btn-warning {{ background: #ffc107; color: #333; font-size: 1.2em; padding: 15px; border-radius: 8px; width: 100%; border: 2px solid #e0a800; margin-top: 10px;}}
        .btn-secondary {{ background: #6c757d; width: 100%; font-size: 1.1em; margin-bottom: 10px; padding: 12px;}}
        .btn-secondary:hover {{ background: #5a6268; }}
        .btn-small {{ padding: 6px 12px; font-size: 0.9em; background: #6c757d; margin-bottom: 15px; display: inline-block; }}
        h3 {{ color: var(--text-color); margin-top: 30px; border-bottom: 2px solid var(--border-color); padding-bottom: 5px; }}
        #log-area {{ width: 100%; height: 250px; background: var(--log-bg); color: #4af626; padding: 15px; overflow-y: auto; font-family: monospace; border-radius: 6px; }}
        #progress-container {{ width: 100%; background: var(--border-color); border-radius: 6px; margin-bottom: 15px; height: 25px; }}
        #progress-bar {{ width: 0%; height: 100%; background: #28a745; transition: width 0.3s; }}
        .date-group {{ margin-top: 30px; border: 2px solid var(--border-color); border-radius: 10px; background: var(--card-bg); overflow: hidden; }}
        .date-header {{ background: var(--header-bg); color: white; font-size: 1.4em; font-weight: bold; padding: 15px 20px; position: sticky; top: 0; z-index: 10; }}
        .date-scroll-area {{ max-height: 800px; overflow-y: auto; padding: 15px; background: var(--bg-color); }}
        .station-group {{ margin-bottom: 25px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--card-bg); }}
        .station-header {{ background: var(--station-header); font-weight: bold; padding: 12px 20px; color: var(--text-color); }}
        .plots-container {{ padding: 20px; }}
        .svg-wrapper {{ text-align: center; }}
        .svg-wrapper svg {{ max-width: 100%; height: auto; }}
        .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); backdrop-filter: blur(5px); }}
        .modal-content {{ margin: 2vh auto; width: 96vw; height: 96vh; background: var(--bg-color); border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; }}
        .modal-controls {{ padding: 15px 20px; background: var(--header-bg); display: flex; gap: 15px; align-items: center; color: white; flex-shrink: 0; }}
        .modal-scroll-area {{ flex-grow: 1; overflow: auto; background: #ffffff; padding: 20px; text-align: center; }}
        .modal-svg-wrapper svg {{ width: 100%; height: auto; transition: width 0.1s; transform-origin: top center; }}
        .close-modal {{ color: white; margin-left: auto; font-size: 32px; cursor: pointer; }}
        .duration-box {{ background: var(--duration-bg); color: var(--duration-text); padding: 5px 10px; border-radius: 5px; font-weight: bold; display: inline-block; margin-top: 10px; font-size: 0.9em; }}
        .compare-row {{ border: 2px dashed var(--border-color); padding: 15px; margin-bottom: 15px; border-radius: 8px; position: relative; }}
        .remove-row-btn {{ position: absolute; top: 10px; right: 10px; background: #dc3545; padding: 4px 8px; font-size: 0.8em; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand-container">
            <img src="/logo.png" class="logo-img" alt="BLCSN Logo">
            <div class="title-wrapper">
                <span class="main-title-text">BLCSN Data Process Software</span>
                <sub class="subscript-author">by <a href="https://github.com/mr-tanvirx" target="_blank">mr-tanvirx</a></sub>
            </div>
        </div>
        <button class="theme-toggle-btn" onclick="toggleTheme()">Toggle Dark Mode</button>
    </div>
    <div class="container">
        <div class="tab-nav">{tabs_html}</div>
        {panes_html}
        
        <h3 style="margin-top: 40px;">Live Status Engine</h3>
        <div id="progress-container"><div id="progress-bar"></div></div>
        <div id="log-area"></div>
        <h3 style="margin-top: 40px;">Data Visualization Output</h3>
        <div id="svg-output"></div>
        <div id="pagination-controls" style="display: none; text-align: center; margin-top: 40px; padding-bottom: 60px;">
            <button class="btn-warning" onclick="loadNextPage()">Process Next Events Chunk</button>
        </div>
    </div>

    <div id="stretch-modal" class="modal">
        <div class="modal-content">
            <div class="modal-controls">
                <span id="modal-title" style="font-weight: bold; font-size: 1.2em;">Stretch Plot</span>
                <button id="zoom-out-btn" onclick="zoomModal(-50)" class="btn-warning" style="width:auto; margin:0; padding:5px 15px;">- Zoom Out</button>
                <span id="zoom-level-indicator">100%</span>
                <button id="zoom-in-btn" onclick="zoomModal(50)" class="btn-large" style="width:auto; margin:0; padding:5px 15px; background:#28a745;">+ Zoom In</button>
                <span class="close-modal" onclick="closeStretchModal()">&times;</span>
            </div>
            <div class="modal-scroll-area" style="padding:0; background:white;"><div id="modal-svg-wrapper" class="modal-svg-wrapper" style="width:100%; height:100%;"></div></div>
        </div>
    </div>

    <script>
        let currentApp = '{sorted_apps[0][0] if sorted_apps else ""}';
        let evtSource = null;
        let currentStretchScale = 100;
        window._customTitles = window._customTitles || {{}};

        function toggleTheme() {{
            document.body.classList.toggle('dark-mode');
            localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
        }}
        window.onload = () => {{ if (localStorage.getItem('theme') === 'dark') document.body.classList.add('dark-mode'); }};
        
        function openTab(tabId) {{
            currentApp = tabId;
            document.querySelectorAll('.tab-pane, .tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            document.querySelector(`[onclick="openTab('${{tabId}}')"]`).classList.add('active');
            document.getElementById('log-area').innerHTML = '';
            document.getElementById('svg-output').innerHTML = '';
            document.getElementById('progress-bar').style.width = '0%';
            document.getElementById('pagination-controls').style.display = 'none';
        }}
        
        function closeStretchModal() {{
            document.getElementById('stretch-modal').style.display = 'none';
            document.getElementById('modal-svg-wrapper').innerHTML = "";
        }}
        
        function zoomModal(factor) {{
            currentStretchScale = Math.max(100, currentStretchScale + factor);
            const svgEl = document.getElementById('modal-svg-wrapper').querySelector('svg');
            if (svgEl) {{ svgEl.style.width = currentStretchScale + '%'; svgEl.style.height = 'auto'; }}
            document.getElementById('zoom-level-indicator').innerText = currentStretchScale + '%';
        }}

        function extractFiltersUI(containerId) {{
            const arr = [];
            const container = document.getElementById(containerId);
            if(container) {{
                container.querySelectorAll('.filter-row').forEach(row => {{
                    const l = row.querySelector('.low-cut')?.value;
                    const h = row.querySelector('.high-cut')?.value;
                    if(l && h) arr.push([parseFloat(l), parseFloat(h)]);
                }});
            }}
            return arr;
        }}
        
        function extractDampingsUI(containerId) {{
            const arr = [];
            const container = document.getElementById(containerId);
            if(container) {{
                container.querySelectorAll('.filter-row').forEach(row => {{
                    const v = row.querySelector('.damping-val')?.value;
                    if(v !== "" && v !== undefined) arr.push(parseFloat(v) / 100.0);
                }});
            }}
            if(arr.length === 0) arr.push(0.0);
            return arr;
        }}
        
        function addFilterUI(id) {{
            const c = document.getElementById(id);
            if(c && c.children.length < 10) c.innerHTML += '<div class="filter-row"><input type="number" step="0.1" class="low-cut" placeholder="Low"> to <input type="number" step="0.1" class="high-cut" placeholder="High"></div>';
        }}
        
        function addDampingUI(id) {{
            const c = document.getElementById(id);
            if(c && c.children.length < 10) c.innerHTML += '<div class="filter-row"><input type="number" step="0.1" class="damping-val" placeholder="e.g. 5"></div>';
        }}

        async function executeAppWorkflow(appId, payload) {{
            const logArea = document.getElementById('log-area');
            if(logArea) logArea.innerHTML = "";
            document.getElementById('svg-output').innerHTML = "";
            document.getElementById('progress-bar').style.width = "0%";
            document.getElementById('pagination-controls').style.display = 'none';
            payload.updated_titles = window._customTitles;
            
            const initBtn = document.getElementById('tab-' + appId)?.querySelector('.init-btn');
            if(initBtn) initBtn.disabled = true;

            listenToStream();

            try {{
                const res = await fetch(`/api/${{appId}}/init`, {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(payload) }});
                const data = await res.json();
                if(data.status === "Initialized") {{
                    loadNextPage();
                }} else {{
                    if(logArea) logArea.innerHTML += "> Init Error: " + (data.message || "Initialization failed.") + "<br>";
                    if(initBtn) initBtn.disabled = false;
                }}
            }} catch(e) {{
                if(logArea) logArea.innerHTML += "> Request failed: " + e + "<br>";
                if(initBtn) initBtn.disabled = false;
            }}
        }}

        function loadNextPage() {{
            document.getElementById('svg-output').innerHTML = "<div style='padding:40px;text-align:center;color:var(--text-color);border:2px dashed var(--border-color);border-radius:8px;'>Processing events in background...<br>Plots will appear automatically.</div>";
            document.getElementById('pagination-controls').style.display = 'none';
            listenToStream();
            fetch(`/api/${{currentApp}}/process`, {{ method: 'POST' }});
        }}

        function listenToStream() {{
            if (evtSource) evtSource.close();
            evtSource = new EventSource("/stream");
            const logArea = document.getElementById('log-area');
            const pb = document.getElementById('progress-bar');
            
            evtSource.onmessage = function(event) {{
                const data = JSON.parse(event.data);
                if (data.action === 'request_suffixes') {{
                    const c = document.getElementById('app3-suffixes-container');
                    c.innerHTML = '<div class="section-title">Found Stations (Add Suffixes)</div><div class="settings-grid" id="suffix-grid"></div><button class="btn-large" onclick="triggerApp3Render(window._stCache)">Render Availability Plot</button>';
                    window._stCache = data.stations;
                    data.stations.forEach(st => document.getElementById('suffix-grid').innerHTML += `<div class="input-group"><label>${{st}}</label><input type="text" id="suffix-${{st}}" placeholder="Suffix (optional)"></div>`);
                    c.style.display = 'block';
                    if(logArea) logArea.innerHTML += `<br>> Found ${{data.stations.length}} stations. Awaiting suffix inputs...<br>`;
                }}
                if (data.log) {{ if(logArea) {{ logArea.innerHTML += data.log + "<br>"; logArea.scrollTop = logArea.scrollHeight; }} }}
                if (data.progress !== undefined && data.total > 0 && pb) pb.style.width = Math.min(100, Math.round((data.progress / data.total) * 100)) + "%";
                
                if (data.svg) {{
                    const svgOut = document.getElementById('svg-output');
                    if (svgOut && svgOut.innerHTML.includes("Processing events in background")) svgOut.innerHTML = "";
                    
                    const dateId = 'date-' + data.event_date.replace(/[^a-zA-Z0-9_-]/g, '_');
                    if (!document.getElementById(dateId)) svgOut.innerHTML += `<div class="date-group" id="${{dateId}}"><div class="date-header">Event: ${{data.event_date}}</div><div class="date-scroll-area" id="${{dateId}}-scroll"></div></div>`;
                    
                    const stId = dateId + '-station-' + data.station.replace(/[^a-zA-Z0-9_-]/g, '_');
                    if (!document.getElementById(stId)) document.getElementById(dateId + '-scroll').innerHTML += `<div class="station-group" id="${{stId}}"><div class="station-header">Profile: ${{data.station}}</div><div class="plots-container" id="${{stId}}-plots"></div></div>`;
                    
                    const wrapper = document.createElement('div');
                    wrapper.className = 'svg-wrapper';
                    
                    wrapper.innerHTML = `<div>${{data.svg}}</div>
                    <div style="margin-top:15px; padding-bottom:15px; border-bottom:1px solid #ddd;">
                        <button class="btn-save">Save Image</button>
                        <button class="btn-edit-title" style="margin-left:15px;background:#6f42c1;color:#fff;border:none;padding:10px 15px;border-radius:6px;font-weight:bold;cursor:pointer;">✎ Edit Title</button>
                        <button class="btn-stretch" style="margin-left:15px;background:#17a2b8;color:#fff;border:none;padding:10px 15px;border-radius:6px;font-weight:bold;cursor:pointer;">Stretch / Zoom Plot</button>
                    </div>`;
                    
                    wrapper.querySelector('.btn-save').onclick = () => {{ const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([data.svg], {{ type: 'image/svg+xml' }})); a.download = (data.file_name || 'plot').replace(/[^a-zA-Z0-9_-]/g, '_') + '.svg'; a.click(); }};
                    
                    wrapper.querySelector('.btn-edit-title').onclick = () => {{
                        const oldTitle = data.title;
                        const newTitle = prompt("Update Plot Title:", oldTitle);
                        if (newTitle !== null && newTitle.trim() !== "") {{
                            const finalTitle = newTitle.trim();
                            window._customTitles[data.file_name] = finalTitle;
                            
                            const svgTextEls = Array.from(wrapper.querySelectorAll('svg text'));
                            let replaced = false;
                            
                            svgTextEls.forEach(el => {{
                                const txt = el.textContent.trim();
                                if (txt.length >= 3 && oldTitle.includes(txt)) {{
                                    const yAttr = parseFloat(el.getAttribute('y') || '1000');
                                    if (yAttr < 80) {{
                                        if (!replaced) {{
                                            el.textContent = finalTitle;
                                            replaced = true;
                                        }} else {{
                                            el.textContent = "";
                                        }}
                                    }}
                                }}
                            }});
                            data.title = finalTitle;
                        }}
                    }};

                    wrapper.querySelector('.btn-stretch').onclick = () => {{
                        if (data.html_url && data.html_url !== "") {{
                            document.getElementById('modal-title').innerText = data.title;
                            document.getElementById('modal-svg-wrapper').innerHTML = `<iframe src="${{data.html_url}}" style="width:100%; height:100%; min-height:85vh; border:none; background:white; display:block;"></iframe>`;
                            document.getElementById('zoom-in-btn').style.display = 'none';
                            document.getElementById('zoom-out-btn').style.display = 'none';
                            document.getElementById('zoom-level-indicator').style.display = 'none';
                            document.getElementById('stretch-modal').style.display = 'flex';
                        }} else {{
                            currentStretchScale = 100;
                            document.getElementById('modal-title').innerText = data.title;
                            document.getElementById('modal-svg-wrapper').innerHTML = data.svg;
                            document.getElementById('zoom-in-btn').style.display = 'inline-block';
                            document.getElementById('zoom-out-btn').style.display = 'inline-block';
                            document.getElementById('zoom-level-indicator').style.display = 'inline-block';
                            document.getElementById('zoom-level-indicator').innerText = '100%';
                            document.getElementById('stretch-modal').style.display = 'flex';
                        }}
                    }};
                    document.getElementById(stId + '-plots').appendChild(wrapper);
                }}

                if (data.done !== undefined) {{
                    evtSource.close();
                    if (data.has_more) {{
                        document.getElementById('pagination-controls').style.display = 'block';
                        if(logArea) logArea.innerHTML += "<br><strong style='color:#ffc107;'>> CHUNK PAUSED to save RAM. Click 'Process Next' below.</strong><br>";
                    }} else if (data.action !== 'request_suffixes') {{
                        if(logArea) logArea.innerHTML += "<br><strong>> TASK COMPLETELY PROCESSED.</strong><br>";
                        const btn = document.getElementById('tab-' + currentApp)?.querySelector('.init-btn');
                        if (btn) btn.disabled = false;
                    }}
                    if(logArea) logArea.scrollTop = logArea.scrollHeight;
                }}
            }};
        }}

        {js_scripts}
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/logo.png')
def get_logo():
    logo_path = Path("BLCSN_logo.png")
    if logo_path.exists():
        return send_file(logo_path, mimetype='image/png')
    return jsonify({"error": "Logo file not found"}), 404

@app.route('/view_html')
def view_html():
    path = request.args.get('path')
    return send_from_directory(TEMP_HTML_DIR, path)

@app.route('/api/<app_id>/init', methods=['POST'])
def init_app(app_id):
    if app_id in app_processors:
        while not log_queue.empty(): log_queue.get()
        res = app_processors[app_id].initialize(request.json)
        if res.get("status") == "Initialized":
            app_processors[app_id].state['is_running'] = True
        return jsonify(res)
    return jsonify({"status": "Error", "message": f"App processor {app_id} not found."})

@app.route('/api/<app_id>/process', methods=['POST'])
def process_app(app_id):
    if app_id in app_processors:
        app_processors[app_id].state['is_running'] = True
        threading.Thread(target=app_processors[app_id].start_page_thread).start()
        return jsonify({"status": "Processing"})
    return jsonify({"status": "Error", "message": f"App processor {app_id} not found."})

@app.route('/stream')
def stream():
    def event_stream():
        idle_count = 0
        while True:
            try:
                msg = log_queue.get(timeout=0.2)
                idle_count = 0
                prog = max([getattr(p, 'state', {}).get("progress", 0) for p in app_processors.values()] or [0])
                tot = max([getattr(p, 'state', {}).get("total", 1) for p in app_processors.values()] or [1])
                
                if msg.startswith("SVG_DATA|||"):
                    p = json.loads(msg.split("|||", 1)[1])
                    p["progress"], p["total"] = prog, tot
                    yield f'data: {json.dumps(p)}\n\n'
                elif msg.startswith('{"done":') or msg.startswith('{"action":'):
                    yield f'data: {msg}\n\n'
                    if msg.startswith('{"done":'): break
                else:
                    yield f'data: {json.dumps({"log": msg, "progress": prog, "total": tot})}\n\n'
            except queue.Empty:
                idle_count += 1
                is_any_running = any([getattr(p, 'state', {}).get("is_running", False) for p in app_processors.values()])
                if not is_any_running and idle_count > 15:
                    break
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    def get_free_port(start_port=5000):
        port = start_port
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', port)) != 0:
                    return port
            port += 1
            
    available_port = get_free_port(5000)
    print(f"Starting server on port {available_port}...")
    webbrowser.open_new(f"http://localhost:{available_port}")
    app.run(port=available_port, threaded=True)