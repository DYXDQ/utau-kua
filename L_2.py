# -*- coding: utf-8 -*-
import sys
import os
import re
import tkinter.messagebox as messagebox

print('loading...',end='')

class UstProcessor:
    def __init__(self, ust_path, multiplier=2.0):
        self.ust_path = ust_path
        self.multiplier = multiplier
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

    def multiply_lengths(self):
        for section in self.sections:
            if section['type'] != 'number':
                continue
            length_str = section['data'].get('Length', '0')
            try:
                length = int(length_str)
                new_length = round(length * self.multiplier)  # 四舍五入到整数
                section['data']['Length'] = str(new_length)
            except ValueError:
                continue  # 跳过无效长度

    def save(self):
        try:
            with open(self.ust_path, 'w', encoding='shift_jis', newline='\r\n', errors='ignore') as f:
                for section in self.sections:  # 这里原代码的sections应该是self.sections
                    f.write(section['header'] + '\r\n')
                    for k, v in section['data'].items():
                        f.write('{0}={1}\r\n'.format(k, v))
            return True
        except Exception as e:
            messagebox.showerror("保存错误", "文件保存失败：{0}".format(str(e)))
            return False


def main():
    if len(sys.argv) < 2:
        messagebox.showerror("错误", "请通过UTAU插件菜单运行")
        return
    # 倍增因子，用户可手动修改此值
    multiplier = 2.0  # 默认2倍，可手动更改为其他值（如 1.5, 3.0）
    ust_path = sys.argv[-1]
    processor = UstProcessor(ust_path, multiplier)
    if not processor.sections:
        return
    processor.multiply_lengths()
    if processor.save():
        print("音符长度已成功改变！")


if __name__ == "__main__":
    main()