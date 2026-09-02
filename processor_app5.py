import json, gc, os, re, threading
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import concurrent.futures
from processor_shared import process_multi_compare, parse_factor

class App5Processor:
    APP_ID = "app5"
    APP_TITLE = "App 5: Compare Plots"

    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.state = {"is_running": False, "config": None}

    def log_msg(self, msg): 
        self.log_queue.put(msg)

    def get_html_template(self):
        return """
        <div style="display: flex; gap: 10px; margin-bottom: 20px; justify-content: flex-end;">
            <button class="btn-secondary" style="width:auto; margin:0; background: #6f42c1;" onclick="exportConfigApp5()">Save Master Compare Config (.compare.json)</button>
            <label class="btn-secondary" style="width:auto; margin:0; cursor:pointer; background: #6f42c1;">
                Load Master Compare Config (.compare.json)
                <input type="file" id="a5-master-config" style="display:none;" accept=".compare.json,.json" onchange="importConfigApp5(event)">
            </label>
        </div>
        <div class="grid-layout" style="grid-template-columns: 1fr;">
            <div class="section-card" style="border: 2px solid #17a2b8;">
                <div class="section-title">Compare Profiles Builder</div>
                <div class="input-group"><label>Output Directory for Comparative Plots</label><input type="text" id="a5-out-dir" placeholder="C:\\EQ_Compare_Outputs"></div>
                <div class="input-group" style="margin-top: 15px;"><label>Custom Plot Title Base (Optional)</label><input type="text" id="a5-custom-title" placeholder="e.g., Overlay Analysis for EQ Event X"></div>
                <div id="compare-rows-container" style="margin-top: 15px;"></div>
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
                    <div class="input-group"><label>Mark Max & Min Values</label><div class="radio-group"><label><input type="radio" name="a5_extrema" class="mark-extrema" value="y"> Y</label><label><input type="radio" name="a5_extrema" class="mark-extrema" value="n" checked> N</label></div></div>
                    <div class="input-group"><label>Filtered Plots</label><div class="radio-group"><label><input type="radio" name="a5_sep" class="sep-plots" value="y" checked> Y</label><label><input type="radio" name="a5_sep" class="sep-plots" value="n"> N</label></div></div>
                    <div class="input-group"><label>Comparison Plots (Orig vs Filt)</label><div class="radio-group"><label><input type="radio" name="a5_comp" class="comp-plots" value="y" checked> Y</label><label><input type="radio" name="a5_comp" class="comp-plots" value="n"> N</label></div></div>
                    
                    <div class="input-group">
                        <label>FFT Plots (Freq vs Amp)</label>
                        <div class="radio-group">
                            <label><input type="radio" name="a5_fft" class="fft-plots" value="y" onchange="document.getElementById('a5_fft_axes').style.display='block'"> Y</label>
                            <label><input type="radio" name="a5_fft" class="fft-plots" value="n" checked onchange="document.getElementById('a5_fft_axes').style.display='none'"> N</label>
                        </div>
                        <div id="a5_fft_axes" style="display:none; margin-top: 10px; padding: 10px; background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 6px;">
                            <label style="display:inline; margin-right: 10px;"><input type="checkbox" class="fft-ax-x" value="x" checked> X</label>
                            <label style="display:inline; margin-right: 10px;"><input type="checkbox" class="fft-ax-y" value="y" checked> Y</label>
                            <label style="display:inline;"><input type="checkbox" class="fft-ax-z" value="z" checked> Z</label>
                        </div>
                    </div>

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
                    <div class="input-group"><label>Y-Axis Unit</label><input type="text" id="a5-y-unit" placeholder="e.g., m/s², etc." value="m/s²"></div>
                    <div class="input-group"><label>Axis Title Font Size</label><input type="number" id="a5-axis-font" value="12"></div>
                    <div class="input-group"><label>Main Title Font Size</label><input type="number" id="a5-title-font" value="13"></div>
                </div>
            </div>
        </div>
        <button class="btn-large init-btn" onclick="run_app5()">Generate Comparison Plots</button>
        """

    def get_js_funcs(self):
        return """
        function calculateDurationExactRow(row) {
            const sh = parseFloat(row.querySelector('.s-hh')?.value || 0);
            const sm = parseFloat(row.querySelector('.s-mm')?.value || 0);
            const ss = parseFloat(row.querySelector('.s-ss')?.value || 0);
            const eh = parseFloat(row.querySelector('.e-hh')?.value || 0);
            const em = parseFloat(row.querySelector('.e-mm')?.value || 0);
            const es = parseFloat(row.querySelector('.e-ss')?.value || 0);
            const outBox = row.querySelector('.duration-box');
            
            if(!row.querySelector('.s-hh')?.value && !row.querySelector('.e-hh')?.value) {
                outBox.innerText = "Duration: Auto (Full Segment)"; 
                return;
            }
            let diff = (eh * 3600 + em * 60 + es) - (sh * 3600 + sm * 60 + ss);
            if (diff < 0) diff += 86400; 
            outBox.innerText = `Duration: ${Number.isInteger(diff) ? diff : diff.toFixed(3)} seconds`;
        }

        function addCompareRow(dataObj = null) {
            const container = document.getElementById('compare-rows-container');
            if(!container) return;
            const row = document.createElement('div');
            row.className = 'compare-row';

            let bMode = dataObj?.baseline_mode;
            if (!bMode) {
                bMode = (dataObj?.mode_bias !== false) ? 'mode' : 'none';
            }

            row.innerHTML = `
                <button class="remove-row-btn" onclick="this.parentElement.remove()">X Remove</button>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <strong style="color:var(--text-color);" class="row-title-lbl">Compare Profile</strong>
                    <div style="font-size:0.85em;">
                        Load Config: <input type="file" accept=".conf,.json" class="cmp-file" style="width:200px;">
                    </div>
                </div>
                <div class="input-group"><label>Label/Name</label><input type="text" class="cmp-name" placeholder="e.g. Station A Data" value="${dataObj?.name || ''}"></div>
                <div class="input-group"><label>Source Directory / File</label><input type="text" class="cmp-dir" placeholder="Folder path or file path" value="${dataObj?.target_dir || ''}"></div>
                
                <div class="inline-inputs" style="margin-bottom:8px;">
                    <span>Start:</span>
                    <input type="number" class="cmp-dur-trig s-hh" placeholder="hh" step="any" value="${dataObj?.start_hh || ''}"> :
                    <input type="number" class="cmp-dur-trig s-mm" placeholder="mm" step="any" value="${dataObj?.start_mm || ''}"> :
                    <input type="number" class="cmp-dur-trig s-ss" placeholder="ss" step="any" value="${dataObj?.start_ss || ''}">
                </div>
                <div class="inline-inputs" style="margin-bottom:8px;">
                    <span>End:&nbsp;&nbsp;</span>
                    <input type="number" class="cmp-dur-trig e-hh" placeholder="hh" step="any" value="${dataObj?.end_hh || ''}"> :
                    <input type="number" class="cmp-dur-trig e-mm" placeholder="mm" step="any" value="${dataObj?.end_mm || ''}"> :
                    <input type="number" class="cmp-dur-trig e-ss" placeholder="ss" step="any" value="${dataObj?.end_ss || ''}">
                </div>
                
                <div style="margin-bottom: 8px; padding: 8px; background: var(--tab-bg); border: 1px dashed var(--border-color); border-radius: 6px;">
                    <div style="display: flex; gap: 20px; align-items: center; margin-bottom: 5px; flex-wrap: wrap;">
                        <label style="margin: 0; cursor:pointer; color: #17a2b8; font-weight: bold;">
                            <input type="checkbox" class="cmp-change-unit" ${dataObj?.change_unit ? 'checked' : ''}> Change Plotting Unit
                        </label>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <label style="margin: 0; font-size: 0.85em; font-weight: bold; color: #17a2b8;">Auto-Center Baseline:</label>
                            <select class="cmp-baseline-mode" style="padding: 3px 6px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--input-bg); color: var(--input-text); font-weight: 600;">
                                <option value="none" ${bMode === 'none' ? 'selected' : ''}>None</option>
                                <option value="mean" ${bMode === 'mean' ? 'selected' : ''}>Mean / Average (Minimizes RMS)</option>
                                <option value="mode" ${bMode === 'mode' ? 'selected' : ''}>Mode (Most Frequent)</option>
                                <option value="median" ${bMode === 'median' ? 'selected' : ''}>Median (Robust)</option>
                                <option value="detrend" ${bMode === 'detrend' ? 'selected' : ''}>Linear Detrend (Drift Removal)</option>
                            </select>
                        </div>
                    </div>
                    <div class="unit-inputs-box" style="display: ${dataObj?.change_unit ? 'block' : 'none'}; margin-top: 8px; border-top: 1px solid var(--border-color); padding-top: 8px;">
                        <div style="display: flex; gap: 10px;">
                            <div style="flex: 1;">
                                <label style="font-size: 0.85em; margin-bottom: 4px;">Unit Name</label>
                                <input type="text" class="cmp-unit-name" placeholder="e.g., g" value="${dataObj?.unit_name || 'g'}">
                            </div>
                            <div style="flex: 1;">
                                <label style="font-size: 0.85em; margin-bottom: 4px;">Conversion Multiplying Factor</label>
                                <input type="text" class="cmp-unit-factor" placeholder="e.g., 1/9.81" value="${dataObj?.unit_factor || '1/9.81'}">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="inline-inputs" style="margin-bottom:8px; background: var(--tab-bg); padding: 8px; border-radius: 6px; flex-wrap: wrap; gap: 15px;">
                    <label style="margin: 0; cursor:pointer;"><input type="checkbox" class="cmp-inv" ${dataObj?.invert ? 'checked' : ''}> Multiply Data by -1</label>
                    <label style="margin: 0; cursor:pointer;"><input type="checkbox" class="cmp-swap" ${dataObj?.swap_xy ? 'checked' : ''}> Swap X & Y Axes</label>
                    <label style="margin: 0; cursor:pointer;"><input type="checkbox" class="cmp-etabs" ${dataObj?.etabs_format ? 'checked' : ''}> ETABS format</label>
                    <label style="margin: 0; cursor:pointer;"><input type="checkbox" class="cmp-imv" ${dataObj?.imv_format ? 'checked' : ''}> IMV format</label>
                </div>
                <div class="duration-box">Duration: Auto (Full Segment)</div>
            `;
            container.appendChild(row);
            
            row.querySelector('.cmp-change-unit').addEventListener('change', function(e) {
                row.querySelector('.unit-inputs-box').style.display = this.checked ? 'block' : 'none';
            });
            
            row.querySelectorAll('.cmp-dur-trig').forEach(el => el.addEventListener('input', () => {
                calculateDurationExactRow(row);
            }));
            
            row.querySelector('.cmp-file').addEventListener('change', function(e) {
                const file = e.target.files[0];
                if(!file) return;
                const reader = new FileReader();
                reader.onload = function(evt) {
                    try {
                        let content = evt.target.result;
                        let jsonStart = content.indexOf('{');
                        let jsonEnd = content.lastIndexOf('}');
                        if(jsonStart !== -1 && jsonEnd !== -1) content = content.substring(jsonStart, jsonEnd + 1);
                        const conf = JSON.parse(content);
                        
                        row.querySelector('.cmp-dir').value = conf['target-dir'] || conf.target_dir || conf['a2-target-dir'] || "";
                        row.querySelector('.s-hh').value = conf['start-hh'] || conf.start_hh || "";
                        row.querySelector('.s-mm').value = conf['start-mm'] || conf.start_mm || "";
                        row.querySelector('.s-ss').value = conf['start-ss'] || conf.start_ss || "";
                        row.querySelector('.e-hh').value = conf['end-hh'] || conf.end_hh || "";
                        row.querySelector('.e-mm').value = conf['end-mm'] || conf.end_mm || "";
                        row.querySelector('.e-ss').value = conf['end-ss'] || conf.end_ss || "";
                        
                        row.querySelector('.cmp-change-unit').checked = (conf['change-unit'] === 'y' || conf.change_unit === true || conf.change_unit === 'y');
                        row.querySelector('.cmp-change-unit').dispatchEvent(new Event('change'));
                        row.querySelector('.cmp-unit-factor').value = conf['unit-factor'] || conf.unit_factor || "1/9.81";
                        row.querySelector('.cmp-unit-name').value = conf['unit-name'] || conf.unit_name || "g";
                        
                        let importedMode = conf.baseline_mode;
                        if (!importedMode) importedMode = (conf.mode_bias !== false) ? 'mode' : 'none';
                        row.querySelector('.cmp-baseline-mode').value = importedMode;

                        row.querySelector('.cmp-etabs').checked = conf.hasOwnProperty('etabs_format') ? conf['etabs_format'] : false;
                        row.querySelector('.cmp-imv').checked = conf.hasOwnProperty('imv_format') ? conf['imv_format'] : false;

                        calculateDurationExactRow(row);
                        document.getElementById('log-area').innerHTML += `> Single row config loaded.<br>`;
                    } catch(err) { alert("Invalid config file format."); }
                };
                reader.readAsText(file);
                e.target.value = ''; 
            });

            if(dataObj) calculateDurationExactRow(row);
        }

        function buildCmpConfigsArray() {
            const arr = [];
            document.querySelectorAll('.compare-row').forEach((row, index) => {
                const selectedMode = row.querySelector('.cmp-baseline-mode')?.value || 'none';
                arr.push({
                    name: row.querySelector('.cmp-name')?.value || `Profile ${index + 1}`,
                    target_dir: row.querySelector('.cmp-dir')?.value || '',
                    start_hh: row.querySelector('.s-hh')?.value || '',
                    start_mm: row.querySelector('.s-mm')?.value || '',
                    start_ss: row.querySelector('.s-ss')?.value || '',
                    end_hh: row.querySelector('.e-hh')?.value || '',
                    end_mm: row.querySelector('.e-mm')?.value || '',
                    end_ss: row.querySelector('.e-ss')?.value || '',
                    change_unit: row.querySelector('.cmp-change-unit')?.checked || false,
                    unit_factor: row.querySelector('.cmp-unit-factor')?.value || '1',
                    unit_name: row.querySelector('.cmp-unit-name')?.value || '',
                    baseline_mode: selectedMode,
                    mode_bias: (selectedMode === 'mode'),
                    invert: row.querySelector('.cmp-inv')?.checked || false,
                    swap_xy: row.querySelector('.cmp-swap')?.checked || false,
                    etabs_format: row.querySelector('.cmp-etabs')?.checked || false,
                    imv_format: row.querySelector('.cmp-imv')?.checked || false
                });
            });
            return arr;
        }

        function exportConfigApp5() {
            try {
                const pane = document.getElementById('tab-app5');
                const config = {
                    "app": "app5",
                    "output-dir": document.getElementById('a5-out-dir')?.value || "",
                    "custom_title_base": document.getElementById('a5-custom-title')?.value || "",
                    "compare_configs": buildCmpConfigsArray(),
                    "filters": extractFiltersUI('a5-fc'),
                    "dampings": extractDampingsUI('a5-dc'),
                    "draw-orig": pane.querySelector('.draw-orig:checked')?.value || "y",
                    "mark-extrema": pane.querySelector('.mark-extrema:checked')?.value || "n",
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
                    "y-axis-unit": document.getElementById('a5-y-unit')?.value || "",
                    "axis-font-size": document.getElementById('a5-axis-font')?.value || "12",
                    "title-font-size": document.getElementById('a5-title-font')?.value || "13",
                    "updated_titles": window._customTitles || {}
                };
                const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(config, null, 4));
                const a = document.createElement('a');
                a.href = dataStr;
                a.download = "Compare_Config.compare.json";
                a.click();
            } catch (err) { alert("Export error: " + err); }
        }

        function importConfigApp5(event) {
            const file = event.target.files[0];
            if(!file) return;
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    const conf = JSON.parse(e.target.result);
                    const pane = document.getElementById('tab-app5');
                    
                    if(document.getElementById('a5-out-dir')) document.getElementById('a5-out-dir').value = conf['output-dir'] || "";
                    if(document.getElementById('a5-custom-title')) document.getElementById('a5-custom-title').value = conf['custom_title_base'] || "";
                    if(document.getElementById('a5-y-unit')) document.getElementById('a5-y-unit').value = conf['y-axis-unit'] || "m/s²";
                    if(document.getElementById('a5-axis-font')) document.getElementById('a5-axis-font').value = conf['axis-font-size'] || "12";
                    if(document.getElementById('a5-title-font')) document.getElementById('a5-title-font').value = conf['title-font-size'] || "13";
                    
                    if(conf.updated_titles) {
                        window._customTitles = Object.assign(window._customTitles || {}, conf.updated_titles);
                    }
                    
                    const container = document.getElementById('compare-rows-container');
                    if(container) container.innerHTML = '';
                    
                    if(conf.compare_configs) {
                        conf.compare_configs.forEach(cfg => addCompareRow(cfg));
                    }
                    
                    const fc = document.getElementById('a5-fc');
                    if(fc) {
                        fc.innerHTML = '';
                        if(conf.filters && conf.filters.length > 0) {
                            conf.filters.forEach(f => fc.innerHTML += `<div class="filter-row"><input type="number" step="0.1" class="low-cut" placeholder="Low" value="${f[0]}"> to <input type="number" step="0.1" class="high-cut" placeholder="High" value="${f[1]}"></div>`);
                        } else addFilterUI('a5-fc');
                    }
                    
                    const dc = document.getElementById('a5-dc');
                    if(dc) {
                        dc.innerHTML = '';
                        if(conf.dampings && conf.dampings.length > 0) {
                            conf.dampings.forEach(d => dc.innerHTML += `<div class="filter-row"><input type="number" step="0.1" class="damping-val" placeholder="e.g. 5" value="${d * 100}"></div>`);
                        } else addDampingUI('a5-dc');
                    }

                    const setRadio = (cls, val) => { if(val) { const r = pane.querySelector(`.${cls}[value="${val}"]`); if(r) r.checked = true; } };
                    setRadio('draw-orig', conf['draw-orig']);
                    setRadio('mark-extrema', conf['mark-extrema'] || conf.mark_extrema);
                    setRadio('sep-plots', conf['sep-plots']);
                    setRadio('comp-plots', conf['comp-plots']);
                    setRadio('fft-plots', conf['fft-plots']);
                    setRadio('resp-plots', conf['resp-plots']);
                    setRadio('save-plots', conf['save-plots']);
                    
                    if(conf.hasOwnProperty('fft-ax-x') && pane.querySelector('.fft-ax-x')) pane.querySelector('.fft-ax-x').checked = conf['fft-ax-x'];
                    if(conf.hasOwnProperty('fft-ax-y') && pane.querySelector('.fft-ax-y')) pane.querySelector('.fft-ax-y').checked = conf['fft-ax-y'];
                    if(conf.hasOwnProperty('fft-ax-z') && pane.querySelector('.fft-ax-z')) pane.querySelector('.fft-ax-z').checked = conf['fft-ax-z'];
                    if(conf.hasOwnProperty('resp-ax-x') && pane.querySelector('.resp-ax-x')) pane.querySelector('.resp-ax-x').checked = conf['resp-ax-x'];
                    if(conf.hasOwnProperty('resp-ax-y') && pane.querySelector('.resp-ax-y')) pane.querySelector('.resp-ax-y').checked = conf['resp-ax-y'];
                    if(conf.hasOwnProperty('resp-ax-z') && pane.querySelector('.resp-ax-z')) pane.querySelector('.resp-ax-z').checked = conf['resp-ax-z'];

                    if(document.getElementById('a5_fft_axes')) document.getElementById('a5_fft_axes').style.display = (conf['fft-plots'] === 'y') ? 'block' : 'none';
                    if(document.getElementById('a5_resp_axes')) document.getElementById('a5_resp_axes').style.display = (conf['resp-plots'] === 'y') ? 'block' : 'none';
                    
                    document.getElementById('log-area').innerHTML += `> Master Compare Config successfully imported.<br>`;
                } catch(err) { alert("Invalid config file formatting."); }
            };
            reader.readAsText(file);
            event.target.value = ''; 
        }

        function run_app5() {
            try {
                const pane = document.getElementById('tab-app5');
                if(!pane) throw new Error("App container not found.");
                
                const configs = buildCmpConfigsArray();
                if(configs.length < 2) {
                    alert("Comparison requires at least 2 profile configurations.");
                    return;
                }

                const payload = {
                    output_dir: document.getElementById('a5-out-dir')?.value || "C:/EQ_Compare_Outputs",
                    custom_title_base: document.getElementById('a5-custom-title')?.value || "",
                    compare_configs: configs,
                    filters: extractFiltersUI('a5-fc'),
                    dampings: extractDampingsUI('a5-dc'),
                    draw_orig: pane.querySelector('.draw-orig:checked')?.value === 'y',
                    mark_extrema: pane.querySelector('.mark-extrema:checked')?.value === 'y',
                    sep_plots: pane.querySelector('.sep-plots:checked')?.value === 'y',
                    comp_plots: pane.querySelector('.comp-plots:checked')?.value === 'y',
                    fft_plots: pane.querySelector('.fft-plots:checked')?.value === 'y',
                    fft_axes: ['x','y','z'].filter(ax => pane.querySelector('.fft-ax-'+ax)?.checked),
                    resp_plots: pane.querySelector('.resp-plots:checked')?.value === 'y',
                    resp_axes: ['x','y','z'].filter(ax => pane.querySelector('.resp-ax-'+ax)?.checked),
                    save_plots: pane.querySelector('.save-plots:checked')?.value === 'y',
                    y_axis_unit: document.getElementById('a5-y-unit')?.value || 'm/s²',
                    axis_font_size: parseInt(document.getElementById('a5-axis-font')?.value || 12),
                    title_font_size: parseInt(document.getElementById('a5-title-font')?.value || 13)
                };
                executeAppWorkflow('app5', payload);
            } catch (err) {
                alert("Frontend Preparation Error: " + err.message);
                console.error(err);
            }
        }

        if (document.readyState === 'complete' || document.readyState === 'interactive') {
            setTimeout(() => { if (document.querySelectorAll('.compare-row').length === 0) { addCompareRow(); addCompareRow(); } }, 100);
        } else {
            window.addEventListener('DOMContentLoaded', () => {
                if (document.querySelectorAll('.compare-row').length === 0) { addCompareRow(); addCompareRow(); }
            });
        }
        """

    def initialize(self, config):
        self.log_msg("--- APP 5: MULTI-EVENT COMPARISON ACTIVE ---")
        configs = config.get('compare_configs', [])
        if len(configs) < 2:
            msg = "Minimum 2 valid profiles required for comparison. Please add profiles."
            self.log_msg(f"> Error: {msg}")
            return {"status": "Error", "message": msg}
        self.state['config'] = config
        self.state['is_running'] = True
        return {"status": "Initialized"}

    def start_page_thread(self):
        try:
            self.state['is_running'] = True
            config = self.state['config']
            configs = config.get('compare_configs', [])
            self.state['total'] = 1
            self.state['progress'] = 0
            
            target_save_dir = Path(config.get('output_dir', 'C:/EQ_Compare_Outputs'))
            target_save_dir.mkdir(parents=True, exist_ok=True)
            
            y_unit = config.get('y_axis_unit', '').strip()
            
            data_results = [None] * len(configs)
            duration_set = set()
            lock = threading.Lock()

            def read_file_to_df(f, conf):
                ext = f.suffix.lower()
                is_etabs = conf.get('etabs_format')
                is_imv = conf.get('imv_format')
                skip_rows = 3 if is_etabs else 0
                hdr = None if (is_etabs or is_imv) else 'infer'

                if ext in ['.parquet', '.pq']:
                    try:
                        df_part = pd.read_parquet(f)
                        if is_etabs and len(df_part) > 3: df_part = df_part.iloc[3:]
                        return df_part
                    except Exception: pass

                if ext in ['.xlsx', '.xls', '.xlsb']:
                    try:
                        if is_etabs: return pd.read_excel(f, header=None, skiprows=3)
                        elif is_imv: return pd.read_excel(f, header=None)
                        else: return pd.read_excel(f)
                    except Exception: pass

                try:
                    df_part = pd.read_csv(f, sep=None, engine='python', on_bad_lines='skip', skiprows=skip_rows, header=hdr)
                    if df_part is not None and not df_part.empty: return df_part
                except Exception: pass

                try:
                    df_part = pd.read_csv(f, sep=r'[\s,;\t]+', engine='python', on_bad_lines='skip', skiprows=skip_rows, header=hdr)
                    if df_part is not None and not df_part.empty: return df_part
                except Exception: pass

                try: return pd.read_parquet(f)
                except Exception: pass

                try: return pd.read_excel(f)
                except Exception: pass
                return None

            def process_profile(idx, conf, ref_data=None):
                try:
                    name = conf.get('name', f"Profile {idx+1}")
                    target_str = conf.get('target_dir', '').strip().strip('"').strip("'")
                    if not target_str:
                        self.log_msg(f"[{name}] <span style='color:orange;'>Empty path provided. Skipping.</span>")
                        return None

                    tdir = Path(target_str)
                    if not tdir.exists():
                        self.log_msg(f"[{name}] <span style='color:red;'>Path does not exist: {target_str}</span>")
                        return None
                    
                    sh, sm, ss = conf.get('start_hh'), conf.get('start_mm'), conf.get('start_ss')
                    eh, em, es = conf.get('end_hh'), conf.get('end_mm'), conf.get('end_ss')
                    has_time = all(x not in ["", None] for x in [sh, sm, ss, eh, em, es])
                    
                    start_sec = (float(sh)*3600 + float(sm)*60 + float(ss)) if has_time else 0.0
                    end_sec = (float(eh)*3600 + float(em)*60 + float(es)) if has_time else 0.0
                    if end_sec < start_sec: end_sec += 86400
                    dur = (end_sec - start_sec) if has_time else 0.0

                    files_to_process = []
                    if tdir.is_file():
                        files_to_process = [tdir]
                    elif tdir.is_dir():
                        ignored_exts = {'.json', '.py', '.png', '.jpg', '.jpeg', '.svg', '.db', '.compare.json', '.exe', '.dll', '.zip'}
                        files_to_process = [f for f in tdir.rglob('*') if f.is_file() and not f.name.startswith('.') and f.suffix.lower() not in ignored_exts]
                        files_to_process.sort()

                    if not files_to_process:
                        self.log_msg(f"[{name}] <span style='color:red;'>No data files found at path: {target_str}</span>")
                        return None

                    dfs = []
                    for f in files_to_process:
                        try:
                            df_part = read_file_to_df(f, conf)
                            if df_part is not None and not df_part.empty:
                                dfs.append(df_part)
                        except Exception as file_err:
                            self.log_msg(f"[{name}] Error reading file {f.name}: {file_err}")
                            
                    if not dfs:
                        self.log_msg(f"[{name}] <span style='color:red;'>Failed to extract data matrix from files. Skipping.</span>")
                        return None
                        
                    df = pd.concat(dfs, ignore_index=True)
                    if df.empty:
                        self.log_msg(f"[{name}] <span style='color:red;'>Dataset strictly empty after concatenation.</span>")
                        return None

                    num_cols = df.shape[1]
                    hz_imv = 2048.0
                    hz_etabs = 100.0

                    if conf.get('imv_format'):
                        if num_cols == 1:
                            df.columns = ['val']
                            df['x'] = pd.to_numeric(df['val'], errors='coerce')
                            df['y'] = 0.0
                            df['z'] = 0.0
                        elif num_cols == 3:
                            df.columns = ['x', 'y', 'z']
                        else:
                            df = df.iloc[:, 0:4]
                            df.columns = ['timestamp', 'x', 'y', 'z']
                        
                        df['timestamp'] = np.arange(len(df)) / hz_imv
                        df['ts_sec'] = df['timestamp']
                        self.log_msg(f"[{name}] Loaded IMV format raw sequence ({len(df)} samples).")

                    elif conf.get('etabs_format'):
                        if num_cols >= 4:
                            df = df.iloc[:, 0:4]
                            df.columns = ['timestamp', 'x', 'y', 'z']
                        elif num_cols == 3:
                            df.columns = ['x', 'y', 'z']
                        else:
                            df.columns = ['val']
                            df['x'] = pd.to_numeric(df['val'], errors='coerce')
                            df['y'] = 0.0
                            df['z'] = 0.0
                        df['timestamp'] = np.arange(len(df)) / hz_etabs
                        df['ts_sec'] = df['timestamp']
                        self.log_msg(f"[{name}] Applied ETABS format (100Hz timeline).")
                    else:
                        if num_cols == 1:
                            df.columns = ['val']
                            df['timestamp'] = np.arange(len(df)) / hz_etabs
                            df['x'] = pd.to_numeric(df['val'], errors='coerce')
                            df['y'] = 0.0
                            df['z'] = 0.0
                            df['ts_sec'] = df['timestamp']
                            self.log_msg(f"[{name}] Auto-mapped 1 column data to X-axis.")
                        elif num_cols == 3:
                            df.columns = ['x', 'y', 'z']
                            df['timestamp'] = np.arange(len(df)) / hz_etabs
                            df['ts_sec'] = df['timestamp']
                            self.log_msg(f"[{name}] Auto-mapped 3 columns to [X, Y, Z] (100Hz timeline).")
                        elif num_cols >= 4:
                            df = df.iloc[:, 0:4]
                            df.columns = ['timestamp', 'x', 'y', 'z']
                            
                            ts_col = df['timestamp']
                            ts_num = pd.to_numeric(ts_col, errors='coerce')

                            if ts_num.notna().sum() > 0 and ts_num.dropna().iloc[0] >= 0 and ts_num.dropna().iloc[0] < 86400 and not isinstance(ts_col.iloc[0], str):
                                df['ts_sec'] = ts_num
                            elif ts_num.notna().sum() > 0 and ts_num.dropna().iloc[0] > 1e8:
                                ts_dt = pd.to_datetime(ts_num, unit='s', errors='coerce')
                                df['ts_sec'] = (ts_dt - ts_dt.dt.floor('D')).dt.total_seconds()
                            else:
                                ts_dt = pd.to_datetime(ts_col, errors='coerce')
                                if ts_dt.notna().sum() > 0 and ts_dt.dropna().iloc[0] is not pd.NaT:
                                    df['ts_sec'] = (ts_dt - ts_dt.dt.floor('D')).dt.total_seconds()
                                else:
                                    df['ts_sec'] = ts_num.fillna(np.arange(len(df)) / hz_etabs)

                            # Reconstruct absolute time anchor when file starts near zero and folder timestamp exists
                            first_val = df['ts_sec'].iloc[0] if not df['ts_sec'].empty else 0.0
                            if first_val < 3600.0:
                                datetime_match = re.search(r'\d{4}-\d{2}-\d{2}[_\sT](\d{2})[-_:](\d{2})[-_:](\d{2})', target_str)
                                if datetime_match:
                                    fh, fm, fs = map(int, datetime_match.groups())
                                    folder_start_sec = fh * 3600 + fm * 60 + fs
                                    df['ts_sec'] = (df['ts_sec'] - first_val) + folder_start_sec
                                    self.log_msg(f"[{name}] Detected start time offset {fh:02d}:{fm:02d}:{fs:02d} from file path.")
                                else:
                                    clean_path = re.sub(r'\d{4}-\d{2}-\d{2}', '', target_str)
                                    time_matches = re.findall(r'(?:^|[^\d])([0-1]\d|2[0-3])[-_:]([0-5]\d)[-_:]([0-5]\d)(?:[^\d]|$)', clean_path)
                                    if time_matches:
                                        fh, fm, fs = map(int, time_matches[-1])
                                        folder_start_sec = fh * 3600 + fm * 60 + fs
                                        df['ts_sec'] = (df['ts_sec'] - first_val) + folder_start_sec
                                        self.log_msg(f"[{name}] Detected start time offset {fh:02d}:{fm:02d}:{fs:02d} from file path.")
                        else:
                            self.log_msg(f"[{name}] <span style='color:red;'>Invalid dataset schema (0 columns). Skipping.</span>")
                            return None

                    for col in ['x', 'y', 'z']:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

                    df = df.dropna(subset=['ts_sec']).sort_values('ts_sec')

                    if has_time and not conf.get('imv_format'):
                        # Stage 1: Try matching exact clock time
                        mask = (df['ts_sec'] >= start_sec) & (df['ts_sec'] <= end_sec)
                        df_segment = df[mask].copy()

                        # Stage 2: Try matching relative offsets if direct clock match fails
                        if df_segment.empty:
                            min_ts = df['ts_sec'].min()
                            rel_start = min_ts + start_sec
                            rel_end = rel_start + dur
                            mask_rel = (df['ts_sec'] >= rel_start) & (df['ts_sec'] <= rel_end)
                            df_segment = df[mask_rel].copy()

                        # Stage 3: Fallback slice if bounds are still out of range
                        if df_segment.empty:
                            self.log_msg(f"[{name}] <span style='color:orange;'>Time bounds outside data bounds. Slicing strict {dur:.1f}s from data start.</span>")
                            min_ts = df['ts_sec'].min()
                            df_segment = df[(df['ts_sec'] >= min_ts) & (df['ts_sec'] <= min_ts + dur)].copy()
                            if df_segment.empty: df_segment = df.copy()

                        with lock: duration_set.add(round(dur, 2))
                    else:
                        df_segment = df.copy()

                    # Resample / scale IMV to match reference profile's size and time grid
                    if conf.get('imv_format') and ref_data is not None:
                        ref_t = ref_data['df']['relative_time'].values
                        ref_dur = ref_t[-1] - ref_t[0] if len(ref_t) > 1 else 1.0
                        N_imv = len(df_segment)
                        t_raw_imv = np.linspace(0, ref_dur, N_imv)
                        
                        df_resampled = pd.DataFrame()
                        for col in ['x', 'y', 'z']:
                            df_resampled[col] = np.interp(ref_t, t_raw_imv, df_segment[col].values)
                        
                        df_resampled['timestamp'] = ref_t
                        df_resampled['relative_time'] = ref_t
                        dt_val = ref_data['dt']
                        df_segment = df_resampled
                        self.log_msg(f"[{name}] Scaled IMV format to match reference profile '{ref_data['name']}' (Duration: {ref_dur:.2f}s, Samples: {len(ref_t)}).")
                    else:
                        t_min = df_segment['ts_sec'].min()
                        df_segment['relative_time'] = df_segment['ts_sec'] - t_min

                        if conf.get('imv_format'): dt_val = 1.0 / hz_imv
                        elif conf.get('etabs_format'): dt_val = 1.0 / hz_etabs
                        else:
                            dt_diffs = np.diff(df_segment['ts_sec'].values)
                            dt_val = np.nanmedian(dt_diffs) if len(dt_diffs) > 0 else 0.01
                            if np.isnan(dt_val) or dt_val <= 0: dt_val = 0.01

                    if conf.get('change_unit'):
                        factor = parse_factor(conf.get('unit_factor', '1.0'))
                        df_segment['x'] *= factor
                        df_segment['y'] *= factor
                        df_segment['z'] *= factor
                        u_name = conf.get('unit_name', 'g')
                        display_name = f"{name} ({u_name})"
                        self.log_msg(f"[{name}] Applied unit mapping: {factor} ({u_name})")
                    else:
                        display_name = f"{name} ({y_unit})" if y_unit else name

                    # Apply Selected Auto-Center / Baseline Removal Method
                    baseline_mode = conf.get('baseline_mode')
                    if not baseline_mode:
                        baseline_mode = 'mode' if conf.get('mode_bias') else 'none'

                    if baseline_mode != 'none':
                        for col in ['x', 'y', 'z']:
                            if baseline_mode == 'mode':
                                mode_series = df_segment[col].round(4).mode()
                                bias = mode_series.iloc[0] if not mode_series.empty else df_segment[col].median()
                                df_segment[col] = df_segment[col] - bias
                                self.log_msg(f"[{name}] Applied {col.upper()} Mode center: {bias:.4f}")
                            elif baseline_mode == 'mean':
                                bias = df_segment[col].mean()
                                df_segment[col] = df_segment[col] - bias
                                self.log_msg(f"[{name}] Applied {col.upper()} Mean/Average center (RMS minimized): {bias:.4f}")
                            elif baseline_mode == 'median':
                                bias = df_segment[col].median()
                                df_segment[col] = df_segment[col] - bias
                                self.log_msg(f"[{name}] Applied {col.upper()} Median center: {bias:.4f}")
                            elif baseline_mode == 'detrend':
                                t_vals = df_segment['relative_time'].values
                                poly = np.polyfit(t_vals, df_segment[col].values, 1)
                                df_segment[col] = df_segment[col] - (poly[0] * t_vals + poly[1])
                                self.log_msg(f"[{name}] Applied {col.upper()} Linear Detrend (slope={poly[0]:.6e}, intercept={poly[1]:.4f})")

                    if conf.get('swap_xy'):
                        temp_x = df_segment['x'].copy()
                        df_segment['x'] = df_segment['y']
                        df_segment['y'] = temp_x
                        self.log_msg(f"[{name}] Swapped internal X and Y.")

                    if conf.get('invert'):
                        df_segment['x'] *= -1
                        df_segment['y'] *= -1
                        df_segment['z'] *= -1
                        self.log_msg(f"[{name}] Multiplied logic by -1.")

                    res_dict = {'name': display_name, 'df': df_segment, 'dt': dt_val}
                    self.log_msg(f"[{name}] <span style='color:#28a745;'>Processed ({len(df_segment)} samples, Hz={1/dt_val:.1f}).</span>")
                    del dfs, df; gc.collect()
                    return res_dict
                except Exception as e:
                    import traceback
                    self.log_msg(f"<strong style='color:red;'>Processing Crash [{conf.get('name')}]: {e}</strong><br><pre>{traceback.format_exc()}</pre>")
                    return None

            # Pass 1: Process non-IMV profiles to establish reference time array and size
            ref_data = None
            for idx, conf in enumerate(configs):
                if not conf.get('imv_format'):
                    res = process_profile(idx, conf)
                    if res is not None:
                        data_results[idx] = res
                        if ref_data is None:
                            ref_data = res

            # Pass 2: Process IMV profiles (scaling them to ref_data) and any remaining tasks
            for idx, conf in enumerate(configs):
                if conf.get('imv_format'):
                    res = process_profile(idx, conf, ref_data=ref_data)
                    if res is not None:
                        data_results[idx] = res
                elif data_results[idx] is None:
                    res = process_profile(idx, conf)
                    if res is not None:
                        data_results[idx] = res

            data_list = [d for d in data_results if d is not None]

            if len(data_list) >= 2:
                timestamp_mark = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                self.log_msg(f"> Forwarding {len(data_list)} loaded events to plot generator...")
                try:
                    process_multi_compare(data_list, config, timestamp_mark, target_save_dir, self.log_msg)
                except Exception as plot_err:
                    import traceback
                    self.log_msg(f"<strong style='color:red;'>Visualization Crash: {plot_err}</strong><br><pre>{traceback.format_exc()}</pre>")
            else:
                self.log_msg(f"<strong style='color:red;'>Aborted: Need at least 2 profiles, successfully gathered only {len(data_list)}.</strong>")

            self.state['progress'] = 1
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False
            
        except Exception as master_err:
            import traceback
            self.log_msg(f"<strong style='color:red;'>SYSTEM FATAL: {master_err}</strong><br><pre>{traceback.format_exc()}</pre>")
            self.log_msg(json.dumps({"done": True, "has_more": False}))
            self.state['is_running'] = False