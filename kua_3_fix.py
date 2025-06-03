# -*- coding: utf-8 -*-
'''
print("作者的个人空间_哔哩哔哩 https://b23.tv/BJawtxi")
print("loading...",end="")
'''

import sys
import os
import re
import tkinter as tk
import tkinter.messagebox as messagebox
from tkinter import ttk

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

class MappingManager:
    def __init__(self):
        self.mapping = self._load_mapping()

    def _load_mapping(self):
        mapping_path = os.path.join(PLUGIN_DIR, "pinyin.txt")
        mapping = {}
        try:
            with open(mapping_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or ';' not in line:
                        continue
                    try:
                        pinyin, romaji = line.split(';', 1)
                        options = [opt.split(',') for opt in romaji.split('_') if opt]
                        formatted_options = []
                        for opt in options:
                            formatted_opt = []
                            for part in opt:
                                if '.' in part:
                                    try:
                                        ratio, roma = part.split('.', 1)
                                        ratio = int(ratio)
                                        if ratio <= 0:
                                            continue
                                        formatted_opt.append((ratio, roma.strip()))
                                    except (ValueError, IndexError):
                                        continue
                                else:
                                    continue
                            if formatted_opt:
                                formatted_options.append(formatted_opt)
                        if formatted_options:
                            mapping[pinyin.strip()] = formatted_options
                    except Exception:
                        continue
            return mapping if mapping else None
        except Exception as e:
            messagebox.showerror("映射表错误", "加载失败：{0}".format(str(e)))
            return None

class UstProcessor:
    def __init__(self, ust_path):
        self.ust_path = ust_path
        self.sections = []
        self._parse_ust()

    def _parse_ust(self):
        current_section = None
        try:
            with open(self.ust_path, 'r', encoding='shift_jis', errors='ignore') as f:
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
                        except ValueError:
                            continue
        except Exception as e:
            messagebox.showerror("解析错误", "UST文件解析失败：{0}".format(str(e)))

    def _get_section_type(self, header):
        match = re.match(r'\[#(\d+|PREV|NEXT)\]', header)
        if match:
            return 'number' if match.group(1).isdigit() else match.group(1)
        return 'other'

    def save(self, sections):
        try:
            with open(self.ust_path, 'w', encoding='shift_jis', newline='\r\n', errors='ignore') as f:
                for section in sections:
                    f.write(section['header'] + '\r\n')
                    for k, v in section['data'].items():
                        f.write('{0}={1}\r\n'.format(k, v))
            return True
        except Exception as e:
            messagebox.showerror("保存错误", "文件保存失败：{0}".format(str(e)))
            return False

class MappingInterface:
    def __init__(self, master, sections, mapping, ust_path):
        self.master = master
        self.original_sections = sections
        self.mapping = mapping
        self.ust_path = ust_path
        self.modified_sections = []
        self.selections = {}
        self.current_combobox = None

        master.title("映射替换工具")
        self._setup_ui()

    def _setup_ui(self):
        main_frame = tk.Frame(self.master, padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)

        ctrl_frame = tk.Frame(main_frame)
        self.overlap_var = tk.BooleanVar(value=True)
        self.pre_utterance_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl_frame, text="衔接处80ms的overlap", variable=self.overlap_var).pack(side='left', padx=5)
        ttk.Checkbutton(ctrl_frame, text="设置PreUtterance为0", variable=self.pre_utterance_var).pack(side='left', padx=5)
        ttk.Button(ctrl_frame, text="应用替换", command=self._apply_changes).pack(side='right')
        ctrl_frame.pack(fill='x', pady=5)

        self.tree = ttk.Treeview(
            main_frame,
            columns=('type', 'lyric', 'options'),
            show='headings',
            selectmode='none'
        )
        self.tree.heading('type', text='类型')
        self.tree.heading('lyric', text='原拼音')
        self.tree.heading('options', text='替换方案')
        self.tree.column('type', width=100, anchor='center')
        self.tree.column('lyric', width=150, anchor='center')
        self.tree.column('options', width=350, anchor='w')

        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.tree.bind("<Double-1>", self._on_double_click)
        self._populate_tree()

    def _populate_tree(self):
        for idx, section in enumerate(self.original_sections):
            if section['type'] != 'number':
                self._add_uneditable_row(section)
                continue
            lyric = section['data'].get('Lyric', '')
            if lyric in self.mapping and len(self.mapping[lyric]) > 0:
                options = self.mapping[lyric]
                default_option = ', '.join(roma for _, roma in options[0])
                self.selections[idx] = options[0]
                self.tree.insert('', 'end', values=('可替换', lyric, default_option), tags=('editable',))
            else:
                self.tree.insert('', 'end', values=('无匹配', lyric, '--'), tags=('uneditable',))

        self.tree.tag_configure('editable', background='#f0f0ff')
        self.tree.tag_configure('uneditable', background='#f0f0f0')

    def _add_uneditable_row(self, section):
        display_type = {
            'PREV': '前导音符',
            'NEXT': '后续音符',
            'other': '其他'
        }.get(section['type'], '特殊')
        lyric = section['data'].get('Lyric', section['type'])
        self.tree.insert('', 'end', values=(display_type, lyric, '（不可修改）'), tags=('uneditable',))

    def _on_double_click(self, event):
        if self.current_combobox:
            self.current_combobox.destroy()

        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)

        if not row_id or col_id != '#3':
            return

        item = self.tree.item(row_id)
        if 'editable' not in self.tree.item(row_id, 'tags'):
            return

        idx = self.tree.index(row_id)
        lyric = item['values'][1]
        options = self.mapping.get(lyric, [])

        bbox = self.tree.bbox(row_id, col_id)
        if not bbox:
            return

        self.current_combobox = ttk.Combobox(
            self.tree,
            values=[', '.join(roma for _, roma in opt) for opt in options],
            state='readonly',
            width=45
        )
        self.current_combobox.set(item['values'][2])
        self.current_combobox.place(
            x=bbox[0],
            y=bbox[1],
            width=bbox[2],
            height=bbox[3]
        )

        self.current_combobox.bind(
            "<<ComboboxSelected>>",
            lambda e, r=row_id, i=idx: self._update_selection(r, i)
        )

    def _update_selection(self, row_id, original_idx):
        selected = self.current_combobox.get()
        options = self.mapping.get(self.tree.item(row_id)['values'][1], [])
        for opt in options:
            if ', '.join(roma for _, roma in opt) == selected:
                self.selections[original_idx] = opt
                break
        self.tree.set(row_id, 'options', selected)
        self.current_combobox.destroy()
        self.current_combobox = None

    def _apply_changes(self):
        new_sections = []
        for idx, section in enumerate(self.original_sections):
            if section['type'] != 'number':
                # 非数字节直接保留
                new_sections.append(section)
                continue
            if idx not in self.selections:
                # 无替换方案的数字节保留
                new_sections.append(section)
                continue
            # 生成新音符
            original_note = section
            romaji_list = self.selections[idx]
            new_notes = self._generate_new_notes(original_note, romaji_list)
            new_sections.extend(new_notes)
            # 添加删除指令，包含原始音符的完整 data
            new_sections.append({
                'header': '[#DELETE]',
                'type': 'number',
                'data': section['data'].copy()  # 复制原始音符的 data
            })

        # 保存新节
        if UstProcessor(self.ust_path).save(new_sections):
            messagebox.showinfo("完成", "替换操作已完成")
            self.master.destroy()

    def _generate_new_notes(self, original_note, romaji_list):
        new_notes = []
        total_length = int(original_note['data'].get('Length', 480))
        total_ratio = sum(ratio for ratio, _ in romaji_list) or 10
        for i, (ratio, roma_sound) in enumerate(romaji_list):
            note_length = int(total_length * ratio / total_ratio)
            if note_length <= 0:
                continue
            new_note = {
                'header': '[#INSERT]',
                'type': 'number',
                'data': {
                    'Lyric': roma_sound,
                    'Length': str(note_length),
                    'NoteNum': original_note['data'].get('NoteNum', '60'),
                    'PreUtterance': '0' if self.pre_utterance_var.get() else '',
                    'VoiceOverlap': '80' if self.overlap_var.get() and i > 0 else '0'
                }
            }
            # 如果原始音符有 Tempo，且当前是第一个音符，添加 Tempo
            if i == 0 and 'Tempo' in original_note['data']:
                new_note['data']['Tempo'] = original_note['data']['Tempo']
            new_notes.append(new_note)
        return new_notes

def main():
    if len(sys.argv) < 2:
        messagebox.showerror("错误", "请通过UTAU插件菜单运行")
        return
    mapper = MappingManager()
    if not mapper.mapping:
        return
    ust_path = sys.argv[-1]
    processor = UstProcessor(ust_path)
    if not processor.sections:
        return
    root = tk.Tk()
    MappingInterface(root, processor.sections, mapper.mapping, ust_path)
    root.mainloop()

if __name__ == "__main__":
    main()