import sys
import os
import tkinter as tk
import tkinter.messagebox as messagebox
from tkinter import ttk

class UstNoteParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.notes = []
        self.tempo = 120.0  # 默认曲速
    
    def parse(self):
        """解析UST文件并提取音符信息"""
        current_note = None
        
        try:
            with open(self.file_path, 'r', encoding='shift_jis') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 处理节
                    if line.startswith('[#'):
                        if current_note:
                            self.notes.append(current_note)
                        current_note = self._new_note(line[2:-1])
                    
                    # 处理全局设置
                    elif line.startswith('Tempo='):
                        self.tempo = float(line.split('=')[1])
                    
                    # 处理音符参数
                    elif current_note and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        current_note['data'][key] = value
            
                if current_note:  # 添加最后一个音符
                    self.notes.append(current_note)
                
        except Exception as e:
            messagebox.showerror("解析错误", str(e))
            return False
        
        return True
    
    def _new_note(self, note_type):
        """创建新音符数据结构"""
        return {
            'type': note_type,
            'data': {
                'Lyric': '',
                'NoteNum': '60',
                'Length': '480',
                'PreUtterance': '',
                'Velocity': '',
                'Intensity': '',
                'Modulation': '',
                'Flags': ''
            }
        }

class NoteViewer:
    def __init__(self, notes, tempo):
        self.root = tk.Tk()
        self.root.title("UTAU音符分析器")
        self.notes = notes
        self.tempo = tempo
        self._setup_ui()
    
    def _setup_ui(self):
        """创建带表格的界面"""
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 基本信息显示
        info_frame = tk.LabelFrame(main_frame, text="全局设置")
        tk.Label(info_frame, text="曲速(BPM):").grid(row=0, column=0, sticky='e')
        tk.Label(info_frame, text=str(self.tempo)).grid(row=0, column=1, sticky='w')
        info_frame.pack(fill='x', pady=5)
        
        # 表格框架
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill='both', expand=True)
        
        # 创建表格
        columns = ('type', 'lyric', 'notenum', 'length', 'preutt', 'velocity', 'flags')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        # 设置列标题
        self.tree.heading('type', text='类型')
        self.tree.heading('lyric', text='歌词')
        self.tree.heading('notenum', text='音高')
        self.tree.heading('length', text='长度')
        self.tree.heading('preutt', text='先行发声')
        self.tree.heading('velocity', text='辅音速度')
        self.tree.heading('flags', text='标志位')
        
        # 设置列宽
        self.tree.column('type', width=80, anchor='center')
        self.tree.column('lyric', width=100, anchor='center')
        self.tree.column('notenum', width=60, anchor='center')
        self.tree.column('length', width=80, anchor='center')
        self.tree.column('preutt', width=80, anchor='center')
        self.tree.column('velocity', width=80, anchor='center')
        self.tree.column('flags', width=150, anchor='w')
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.tree.pack(side='left', fill='both', expand=True)
        
        # 填充数据
        for note in self.notes:
            length_ticks = note['data'].get('Length', '480')
            try:
                length_sec = (int(length_ticks)/480) * (60/self.tempo)
            except:
                length_sec = 0.0
            
            self.tree.insert('', 'end', values=(
                note['type'],
                note['data'].get('Lyric', ''),
                self._midi_to_note(int(note['data'].get('NoteNum', '60'))),
                "{0}ticks ({1:.2f}s)".format(length_ticks, length_sec),
                note['data'].get('PreUtterance', '自动'),
                note['data'].get('Velocity', '100'),
                note['data'].get('Flags', '无')
            ))
        
        # 底部按钮
        tk.Button(main_frame, text="退出", command=self.root.destroy).pack(pady=10)
    
    def _midi_to_note(self, midi_num):
        """将MIDI编号转换为音高表示（兼容Python 3.4）"""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_num // 12) - 1
        note_index = midi_num % 12
        return "{0}{1}".format(notes[note_index], octave)
    
    def show(self):
        self.root.mainloop()

def main():
    if len(sys.argv) < 2:
        messagebox.showerror("错误", "请通过UTAU插件菜单运行")
        return
    
    file_path = sys.argv[-1]
    if not os.path.exists(file_path):
        messagebox.showerror("错误", "文件不存在")
        return
    
    # 解析文件
    parser = UstNoteParser(file_path)
    if not parser.parse():
        return
    
    # 显示界面
    viewer = NoteViewer(parser.notes, parser.tempo)
    viewer.show()

if __name__ == "__main__":
    main()