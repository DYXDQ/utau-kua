# -*- coding: utf-8 -*-
import sys
import os
import re
import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
from tkinter import ttk

class UstProcessor:
    def __init__(self, file_path, encoding='shift_jis'):
        self.file_path = file_path
        self.encoding = encoding
        self.sections = []
        self.total_ticks = 0
        self.is_mode2 = False
        self._parse_file()

    def _parse_file(self):
        current_section = None
        try:
            with open(self.file_path, 'r', encoding=self.encoding, errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('[#'):
                        current_section = {
                            'header': line,
                            'type': self._get_section_type(line),
                            'data': {},
                            'original_index': len(self.sections)
                        }
                        self.sections.append(current_section)
                    elif current_section and '=' in line:
                        try:
                            key, value = line.split('=', 1)
                            current_section['data'][key.strip()] = value.strip()
                            if current_section['type'] == 'SETTING' and key.strip() == 'Mode2':
                                self.is_mode2 = value.strip().lower() == 'true'
                        except ValueError:
                            continue
        except UnicodeDecodeError:
            if self.encoding == 'shift_jis' and 'tmp' not in self.file_path.lower():
                self.encoding = 'utf-8'
                self.sections = []
                self._parse_file()
            else:
                messagebox.showerror("解析错误", "无法解析文件：{0}".format(self.file_path))
        except Exception as e:
            messagebox.showerror("解析错误", "文件解析失败：{0}".format(str(e)))

        for section in self.sections:
            if section['type'] == 'number':
                length = section['data'].get('Length', '0')
                try:
                    self.total_ticks += int(length)
                except ValueError:
                    continue

    def _get_section_type(self, header):
        match = re.match(r'\[#(\d+|PREV|NEXT|SETTING)\]', header)
        if match:
            return 'number' if match.group(1).isdigit() else match.group(1)
        return 'other'

    def get_pitch_and_vibrato_data(self):
        """提取音高线和颤音数据"""
        pitch_timeline = []
        vibrato_data = []
        current_tick = 0
        for section in self.sections:
            if section['type'] != 'number':
                continue
            length = int(section['data'].get('Length', '0'))
            if length <= 0:
                continue

            # 音高字段
            pbs = section['data'].get('PBS', '0').split(';')[0]
            pbw = section['data'].get('PBW', '').split(',')
            pby = section['data'].get('PBY', '').split(',')

            try:
                pbs = float(pbs)
                pbw = [float(w) if w else 0.0 for w in pbw]
                pby = [float(y) if y else 0.0 for y in pby]
            except ValueError:
                pbw, pby = [], []

            if not pbw or not pby:
                pitch_timeline.append((current_tick, 0.0))
                current_tick += length
                pitch_timeline.append((current_tick, 0.0))
            else:
                tick_offset = 0
                for w, y in zip(pbw, pby):
                    if w <= 0:
                        continue
                    tick_pos = current_tick + tick_offset
                    pitch_timeline.append((tick_pos, y))
                    tick_offset += w
                pitch_timeline.append((current_tick + length, pby[-1] if pby else 0.0))
                current_tick += length

            # 颤音字段
            vbr = section['data'].get('VBR', '')
            if vbr:
                vibrato_data.append((current_tick - length, current_tick, vbr))

        return pitch_timeline, vibrato_data

    def apply_pitch_and_vibrato_data(self, source_pitch_timeline, source_vibrato_data, source_total_ticks):
        """将音高线和颤音映射到目标音符"""
        if not source_total_ticks or source_total_ticks != self.total_ticks:
            messagebox.showerror("错误", "源文件与目标文件的总长度不匹配")
            return False

        for section in self.sections:
            if section['type'] != 'number':
                continue
            length = int(section['data'].get('Length', '0'))
            if length <= 0:
                continue

            start_tick = sum(int(s['data'].get('Length', '0')) for s in self.sections[:section['original_index']] if s['type'] == 'number')
            end_tick = start_tick + length

            # 音高映射
            new_pbw = []
            new_pby = []
            prev_tick = start_tick
            for tick, pitch in source_pitch_timeline:
                if start_tick <= tick < end_tick:
                    relative_tick = tick - start_tick
                    width = relative_tick - sum(float(w) for w in new_pbw if w)
                    if width > 0:
                        new_pbw.append(str(width))
                        new_pby.append(str(pitch))
                    prev_tick = tick
            if prev_tick < end_tick:
                width = end_tick - prev_tick
                if width > 0 and new_pby:
                    new_pbw.append(str(width))
                    new_pby.append(new_pby[-1])

            if new_pbw and new_pby:
                section['data']['PBS'] = '0'
                section['data']['PBW'] = ','.join(new_pbw)
                section['data']['PBY'] = ','.join(new_pby)
            else:
                section['data'].pop('PBS', None)
                section['data'].pop('PBW', None)
                section['data'].pop('PBY', None)

            # 颤音映射
            applied_vbr = None
            for vbr_start, vbr_end, vbr in source_vibrato_data:
                if start_tick < vbr_end and end_tick > vbr_start:  # 任意重叠
                    applied_vbr = vbr
                    break
            if applied_vbr:
                section['data']['VBR'] = applied_vbr
            else:
                section['data'].pop('VBR', None)

        return True

    def save(self):
        try:
            with open(self.file_path, 'w', encoding='shift_jis', newline='\r\n', errors='replace') as f:
                for section in self.sections:
                    f.write(section['header'] + '\r\n')
                    for k, v in section['data'].items():
                        f.write('{0}={1}\r\n'.format(k, v))
            return True
        except Exception as e:
            messagebox.showerror("保存错误", "文件保存失败：{0}".format(str(e)))
            return False

class PitchMapperInterface:
    def __init__(self, master, tmp_path):
        self.master = master
        self.tmp_path = tmp_path
        self.selected_ust_path = None
        master.title("音高与颤音映射工具")
        self._setup_ui()

    def _setup_ui(self):
        main_frame = tk.Frame(self.master, padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)

        self.file_label = ttk.Label(main_frame, text="未选择 .ust 文件")
        self.file_label.pack(fill='x', pady=5)
        ttk.Button(main_frame, text="选择文件", command=self._select_file).pack(pady=5)
        ttk.Button(main_frame, text="应用音高和颤音映射", command=self._apply_mapping).pack(pady=10)

    def _select_file(self):
        file_path = filedialog.askopenfilename(
            title="选择 .ust 文件",
            filetypes=[("UST files", "*.ust")]
        )
        if file_path:
            self.selected_ust_path = file_path
            self.file_label.config(text="已选择：{0}".format(os.path.basename(file_path)))

    def _apply_mapping(self):
        if not self.selected_ust_path:
            messagebox.showerror("错误", "请先选择一个 .ust 文件")
            return

        target_processor = UstProcessor(self.tmp_path, encoding='shift_jis')
        if not target_processor.sections:
            return
        if not target_processor.is_mode2:
            messagebox.showerror("错误", "目标文件未启用 Mode2，请在 UTAU 中启用 Mode2")
            return

        source_processor = UstProcessor(self.selected_ust_path, encoding='shift_jis')
        if not source_processor.sections:
            return
        pitch_timeline, vibrato_data = source_processor.get_pitch_and_vibrato_data()
        source_total_ticks = source_processor.total_ticks

        if target_processor.apply_pitch_and_vibrato_data(pitch_timeline, vibrato_data, source_total_ticks):
            if target_processor.save():
                messagebox.showinfo("完成", "音高与颤音映射已完成")
                self.master.destroy()

def main():
    if len(sys.argv) < 2:
        messagebox.showerror("错误", "请通过UTAU插件菜单运行")
        return

    tmp_path = sys.argv[-1]
    root = tk.Tk()
    PitchMapperInterface(root, tmp_path)
    root.mainloop()

if __name__ == "__main__":
    main()