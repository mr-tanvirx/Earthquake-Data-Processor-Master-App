import json, calendar
from pathlib import Path
from datetime import datetime
import boto3
from processor_shared import AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION, TARGET_BUCKET, PREFIX

class App3Processor:
    APP_ID = "app3"
    APP_TITLE = "App 3: BLCA Data Availability"

    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.state = {"is_running": False, "cached_data": None, "cached_type": None}

    def log_msg(self, msg):
        self.log_queue.put(msg)

    def get_html_template(self):
        return """
        <div class="grid-layout">
            <div class="section-card">
                <div class="section-title">BLCA Data Availability Dashboard</div>
                <div class="input-group">
                    <label>Local Archive Directory</label>
                    <input type="text" id="app3-local-dir" placeholder="e.g., G:\\Archive">
                </div>
                <button class="btn-secondary" onclick="run_app3('local_tree')">Generate Local Directory Tree Structure</button>
                <button class="btn-secondary" onclick="run_app3('s3_tree')">Generate S3 Bucket Tree Structure</button>
                <button class="btn-secondary" onclick="run_app3('local_svg')">Scan Local Data Availability</button>
                <button class="btn-secondary" onclick="run_app3('s3_svg')">Scan Cloud S3 Data Availability</button>
            </div>
            <div class="section-card" id="app3-suffixes-container" style="display: none;"></div>
        </div>
        """

    def get_js_funcs(self):
        return """
        function run_app3(action) {
            if(action === 'local_svg' || action === 's3_svg') {
                document.getElementById('app3-suffixes-container').style.display = 'none';
            }
            executeAppAction('app3', { action: action, local_dir: document.getElementById('app3-local-dir').value });
        }
        function triggerApp3Render(suffixes) {
            document.getElementById('log-area').innerHTML = "> Generating SVG with suffixes...<br>";
            executeAppAction('app3', { action: 'render_svg', suffixes: suffixes }, true);
        }
        """

    def run_custom_action(self, action, data):
        if action == 'local_tree': self.run_local_tree(data.get('local_dir'))
        elif action == 's3_tree': self.run_s3_tree()
        elif action == 'local_svg': self.run_local_availability(data.get('local_dir'))
        elif action == 's3_svg': self.run_s3_availability()
        elif action == 'render_svg': self.render_svg(data.get('suffixes', {}))

    def run_local_tree(self, local_dir):
        self.state['is_running'] = True
        self.log_msg(f"Generating Local Tree for: {local_dir}...")
        base_dir = Path(local_dir) if local_dir else Path("")
        if not base_dir.exists() or not base_dir.is_dir():
            self.log_msg(f"Error: Local directory '{local_dir}' not found.")
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            return
            
        def _build_local_tree_str(dir_path, prefix_str="", depth=0, max_depth=5):
            res = []
            if depth > max_depth: return res + [f"{prefix_str}└── [Max Depth Reached]"]
            try: items = sorted(list(dir_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError: return res
            for i, item in enumerate(items):
                is_last = (i == len(items) - 1)
                connector = "└── " if is_last else "├── "
                display_name = f"{item.name}/" if item.is_dir() else item.name
                res.append(f"{prefix_str}{connector}{display_name}")
                if item.is_dir():
                    extension = "    " if is_last else "│   "
                    res.extend(_build_local_tree_str(item, prefix_str + extension, depth + 1, max_depth))
            return res
            
        try:
            tree_lines = [base_dir.name + "/"] + _build_local_tree_str(base_dir)
            for line in tree_lines: self.log_msg(line.replace(" ", "&nbsp;"))
        except Exception as e: self.log_msg(f"Error generating local tree: {e}")
            
        self.log_msg(json.dumps({"done": True, "has_more": False}))
        self.state['is_running'] = False

    def run_s3_tree(self):
        self.state['is_running'] = True
        self.log_msg("Generating S3 Bucket Tree...")
        try:
            s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=AWS_REGION)
            pages = s3_client.get_paginator('list_objects_v2').paginate(Bucket=TARGET_BUCKET, Prefix=PREFIX)

            tree = {}
            for page in pages:
                if 'Contents' not in page: continue
                for obj in page['Contents']:
                    key = obj['Key']
                    if PREFIX and key.startswith(PREFIX): key = key[len(PREFIX):]
                    parts = [p for p in key.split('/') if p]
                    curr = tree
                    for part in parts:
                        if part not in curr: curr[part] = {}
                        curr = curr[part]

            def _build_tree_str(node, prefix_str=""):
                res = []
                items = sorted(node.keys())
                for i, item in enumerate(items):
                    is_last = (i == len(items) - 1)
                    connector = "└── " if is_last else "├── "
                    display_name = f"{item}/" if node[item] else item
                    res.append(f"{prefix_str}{connector}{display_name}")
                    if node[item]:
                        extension = "    " if is_last else "│   "
                        res.extend(_build_tree_str(node[item], prefix_str + extension))
                return res

            root_name = TARGET_BUCKET if not PREFIX else f"{TARGET_BUCKET}/{PREFIX}"
            for line in ([root_name] + _build_tree_str(tree)): self.log_msg(line.replace(" ", "&nbsp;"))

        except Exception as e: self.log_msg(f"Error accessing S3: {e}")
        self.log_msg(json.dumps({"done": True, "has_more": False}))
        self.state['is_running'] = False

    def build_year_grid(self, year, available_months, y_offset):
        if not available_months: return "", 0, 0
        start_month, end_month = min(available_months.keys()), max(available_months.keys())
        num_months = end_month - start_month + 1
        cols_per_day, rows_per_day, hr_box_size, hr_padding = 6, 4, 6, 1
        day_width, day_height = cols_per_day * (hr_box_size + hr_padding), rows_per_day * (hr_box_size + hr_padding)
        step_x, step_y = day_width + 8, day_height + 12
        width, height = 120 + (31 * step_x), 80 + (num_months * step_y)
        
        svg = [f'<g transform="translate(20, {y_offset})">',
               f'<text x="{width//2}" y="20" font-family="Arial" font-size="20" text-anchor="middle" font-weight="bold" fill="#555555">{year}</text>']
        for d in range(1, 32): svg.append(f'<text x="{100 + (d - 1) * step_x + (day_width / 2)}" y="50" font-family="Arial" font-size="12" text-anchor="middle" fill="#666666">{d}</text>')
            
        months_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for row_idx, m in enumerate(range(start_month, end_month + 1)):
            y_pos = 70 + (row_idx * step_y)
            svg.append(f'<text x="80" y="{y_pos + (day_height / 2) + 4}" font-family="Arial" font-size="12" text-anchor="end" fill="#333333" font-weight="bold">{months_labels[m-1]}</text>')
            days_in_month = calendar.monthrange(year, m)[1]
            active_days = available_months.get(m, {})
            for d in range(1, 32):
                x_pos = 100 + (d - 1) * step_x
                if d > days_in_month: svg.append(f'<rect x="{x_pos}" y="{y_pos}" width="{day_width}" height="{day_height}" fill="#f0f0f0" rx="3" ry="3"/>')
                else:
                    active_hours = active_days.get(d, set())
                    if not active_hours: svg.append(f'<rect x="{x_pos}" y="{y_pos}" width="{day_width}" height="{day_height}" fill="#cccccc" rx="2" ry="2"/>')
                    else:
                        svg.append(f'<rect x="{x_pos-1}" y="{y_pos-1}" width="{day_width+1}" height="{day_height+1}" fill="none" stroke="#e0e0e0" rx="2" ry="2"/>')
                        for h in range(24):
                            hx, hy = x_pos + (h % cols_per_day) * (hr_box_size + hr_padding), y_pos + (h // cols_per_day) * (hr_box_size + hr_padding)
                            color = "#2ca02c" if h in active_hours else "#d62728"
                            svg.append(f'<rect x="{hx}" y="{hy}" width="{hr_box_size}" height="{hr_box_size}" fill="{color}"/>')
        svg.append('</g>')
        return "\n".join(svg), width, height

    def generate_dashboard_svg(self, data, title, suffixes):
        if not data: return None
        groups = []
        current_y_offset = 100
        max_chart_width = 0
        assumed_chart_width = 1670 
        center_x = (assumed_chart_width + 40) // 2

        for station in sorted(data.keys()):
            suffix = suffixes.get(station, "").strip()
            display_name = f"{station} - {suffix}" if suffix else station
            groups.append(f'<rect x="20" y="{current_y_offset - 30}" width="{assumed_chart_width}" height="40" fill="#e8eef2" rx="5" ry="5"/>')
            groups.append(f'<text x="{center_x}" y="{current_y_offset - 3}" font-family="Arial" font-size="24" text-anchor="middle" font-weight="bold" fill="#112233">{display_name}</text>')
            current_y_offset += 40
            for year in sorted(data[station].keys()):
                svg_group_str, chart_w, chart_h = self.build_year_grid(year, data[station][year], current_y_offset)
                if chart_h == 0: continue
                groups.append(svg_group_str)
                max_chart_width = max(max_chart_width, chart_w)
                current_y_offset += chart_h + 40
            current_y_offset += 60

        if not groups: return None
        legend_y = current_y_offset
        total_width, total_height = max_chart_width + 40, legend_y + 80
        
        master_svg = [f'<svg width="{total_width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">',
                      '<rect width="100%" height="100%" fill="#ffffff"/>',
                      f'<text x="{center_x}" y="50" font-family="Arial" font-size="36" text-anchor="middle" font-weight="bold" fill="#000000">{title}</text>']
        master_svg.extend(groups)
        
        lx = center_x - 220
        master_svg.extend([
            f'<rect x="{lx - 20}" y="{legend_y - 25}" width="510" height="40" fill="#f8f9fa" stroke="#dddddd" rx="8" ry="8"/>',
            f'<rect x="{lx}" y="{legend_y - 12}" width="15" height="15" fill="#2ca02c" rx="2" ry="2"/>', f'<text x="{lx + 25}" y="{legend_y}" font-family="Arial" font-size="14" fill="#333333">Available</text>',
            f'<rect x="{lx + 110}" y="{legend_y - 12}" width="15" height="15" fill="#d62728" rx="2" ry="2"/>', f'<text x="{lx + 135}" y="{legend_y}" font-family="Arial" font-size="14" fill="#333333">Missing</text>',
            f'<rect x="{lx + 210}" y="{legend_y - 12}" width="15" height="15" fill="#cccccc" rx="2" ry="2"/>', f'<text x="{lx + 235}" y="{legend_y}" font-family="Arial" font-size="14" fill="#333333">Whole Day Missing</text>',
            f'<rect x="{lx + 380}" y="{legend_y - 12}" width="15" height="15" fill="#f0f0f0" rx="2" ry="2"/>', f'<text x="{lx + 405}" y="{legend_y}" font-family="Arial" font-size="14" fill="#333333">Invalid Date</text>'
        ])
        master_svg.append('</svg>')
        return "\n".join(master_svg)

    def run_local_availability(self, local_dir):
        self.state['is_running'] = True
        self.log_msg("Scanning Local Directory for Availability...")
        base_dir = Path(local_dir) if local_dir else Path("")
        data = {}
        if base_dir.exists() and base_dir.is_dir():
            for stat_dir in base_dir.iterdir():
                if not stat_dir.is_dir(): continue
                stat = stat_dir.name
                arc_dir = stat_dir / "archive"
                if not arc_dir.exists(): continue
                for yr_dir in arc_dir.iterdir():
                    if not yr_dir.name.isdigit(): continue
                    yr = int(yr_dir.name)
                    for mo_dir in yr_dir.iterdir():
                        if not mo_dir.name.isdigit(): continue
                        mo = int(mo_dir.name)
                        for d_dir in mo_dir.iterdir():
                            if not d_dir.name.isdigit(): continue
                            d = int(d_dir.name)
                            hrs = {int(f.stem[-2:]) for f in d_dir.iterdir() if f.is_file() and f.stem[-2:].isdigit() and 0 <= int(f.stem[-2:]) <= 23}
                            if hrs:
                                if stat not in data: data[stat] = {}
                                if yr not in data[stat]: data[stat][yr] = {}
                                if mo not in data[stat][yr]: data[stat][yr][mo] = {}
                                data[stat][yr][mo][d] = hrs
            if data:
                self.state['cached_data'] = data
                self.state['cached_type'] = 'local'
                self.log_msg(json.dumps({"action": "request_suffixes", "stations": sorted(list(data.keys())), "type": "local"}))
            else:
                self.log_msg("No data found in Local Archive.")
        else:
            self.log_msg("Invalid Local Directory path.")
        
        self.log_msg(json.dumps({"done": True, "has_more": False}))
        self.state['is_running'] = False

    def run_s3_availability(self):
        self.state['is_running'] = True
        self.log_msg("Scanning S3 Cloud for Availability...")
        data = {}
        try:
            s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=AWS_REGION)
            pages = s3_client.get_paginator('list_objects_v2').paginate(Bucket=TARGET_BUCKET, Prefix=PREFIX)
            for page in pages:
                if 'Contents' not in page: continue
                for obj in page['Contents']:
                    key = obj['Key'][len(PREFIX):].lstrip('/') if PREFIX and obj['Key'].startswith(PREFIX) else obj['Key']
                    parts = [p for p in key.split('/') if p]
                    if len(parts) >= 6 and parts[1] == 'data':
                        stat, yr, mo, d, hr_str = parts[0], parts[2], parts[3], parts[4], parts[-1].rsplit('.', 1)[0][-2:]
                        if yr.isdigit() and mo.isdigit() and d.isdigit() and hr_str.isdigit():
                            yr, mo, d, hr = int(yr), int(mo), int(d), int(hr_str)
                            if 0 <= hr <= 23:
                                if stat not in data: data[stat] = {}
                                if yr not in data[stat]: data[stat][yr] = {}
                                if mo not in data[stat][yr]: data[stat][yr][mo] = {}
                                if d not in data[stat][yr][mo]: data[stat][yr][mo][d] = set()
                                data[stat][yr][mo][d].add(hr)
                                
            if data:
                self.state['cached_data'] = data
                self.state['cached_type'] = 'cloud'
                self.log_msg(json.dumps({"action": "request_suffixes", "stations": sorted(list(data.keys())), "type": "cloud"}))
            else:
                self.log_msg("No data found in S3.")
        except Exception as e:
            self.log_msg(f"S3 Error: {e}")
            
        self.log_msg(json.dumps({"done": True, "has_more": False}))
        self.state['is_running'] = False

    def render_svg(self, suffixes):
        self.state['is_running'] = True
        data = self.state.get('cached_data')
        type_str = self.state.get('cached_type')
        if not data:
            self.log_msg("Error: No scanned data found. Please scan again.")
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            return
            
        self.log_msg("Rendering SVG with provided suffixes...")
        title = "Local Data Archive Availability" if type_str == 'local' else "Cloud Data Archive Availability"
        svg_str = self.generate_dashboard_svg(data, title, suffixes)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"{type_str}_availability_at_{timestamp}"
        
        if svg_str:
            payload = json.dumps({"svg": svg_str, "title": title, "event_date": "Dashboard", "station": type_str.capitalize(), "file_name": file_name})
            self.log_msg(f"SVG_DATA|||{payload}")
            
        self.log_msg("Rendering complete.")
        self.log_msg(json.dumps({"done": True, "has_more": False}))
        self.state['is_running'] = False