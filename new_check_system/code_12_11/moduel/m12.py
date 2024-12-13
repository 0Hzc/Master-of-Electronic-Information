import os
import traceback
from datetime import datetime

def check_validation_errors(input_dir):
    try:
        # 检查目录是否存在
        if not os.path.exists(input_dir):
            print(f"错误：目录 {input_dir} 不存在")
            return

        # 获取所有相关文件
        all_files = os.listdir(input_dir)
        valresult_files = [f for f in all_files if f.startswith('valresult_')]
        timeresult_files = [f for f in all_files if f.startswith('timeresult_')]
        spaceresult_files = [f for f in all_files if f.startswith('spaceresult_')]
        
        print(f"找到 {len(valresult_files)} 个valresult文件")
        print(f"找到 {len(timeresult_files)} 个timeresult文件")
        print(f"找到 {len(spaceresult_files)} 个spaceresult文件")
        
        all_errors = []  # 存储所有错误信息
        
        # 首先检查所有timeresult文件
        for time_file in timeresult_files:
            time_path = os.path.join(input_dir, time_file)
            print(f"\n检查时间匹配文件：{time_file}")
            try:
                with open(time_path, 'r') as f:
                    content = f.read().strip()
                    print(f"时间匹配文件内容长度：{len(content)}")
                    if not content:
                        error_msg = f"时间匹配失败: {time_file} (文件为空)"
                        all_errors.append(error_msg)
                        print(error_msg)
            except Exception as e:
                print(f"读取文件 {time_file} 时出错：{str(e)}")
        
        # 检查所有spaceresult文件
        for space_file in spaceresult_files:
            space_path = os.path.join(input_dir, space_file)
            print(f"\n检查空间匹配文件：{space_file}")
            try:
                with open(space_path, 'r') as f:
                    content = f.read().strip()
                    print(f"空间匹配文件内容长度：{len(content)}")
                    if not content:
                        error_msg = f"空间匹配失败: {space_file} (文件为空)"
                        all_errors.append(error_msg)
                        print(error_msg)
            except Exception as e:
                print(f"读取文件 {space_file} 时出错：{str(e)}")
        
        # 检查所有valresult文件
        for val_file in valresult_files:
            val_path = os.path.join(input_dir, val_file)
            print(f"\n检查验证结果文件：{val_file}")
            try:
                with open(val_path, 'r') as f:
                    content = f.read()
                    if '/Effective pixel count=0' in content:
                        error_msg = f"产品检验失败: {val_file} (有效像素数为0)"
                        all_errors.append(error_msg)
                        print(error_msg)
            except Exception as e:
                print(f"读取文件 {val_file} 时出错：{str(e)}")
        
        # 如果有任何错误，生成错误文件并显示弹窗
        if all_errors:
            # 生成一个总的错误文件
            error_file = f'error_summary_{datetime.now().strftime("%Y%m%d%H%M%S")}.txt'
            error_path = os.path.join(input_dir, error_file)
            with open(error_path, 'w') as f:
                f.write('\n'.join(all_errors))
            
            # 显示弹窗
            # import tkinter as tk
            # from tkinter import messagebox
            # root = tk.Tk()
            # root.withdraw()
            # error_msg = '\n'.join(all_errors)
            # messagebox.showerror("验证错误", f"发现以下错误：\n{error_msg}")
            
            print(f"\n已生成错误文件：{error_file}")
            print(f"错误信息：\n{error_msg}")
        else:
            print("\n未发现任何错误")
        
        print("\n错误检查完成")
        
    except Exception as e:
        print(f"检查验证错误时出现问题：{str(e)}")
        traceback.print_exc()

def main():
    input_dir = r'C:\Users\H\Desktop\new_HY_check\code_12_11\output'
    print(f"开始检查目录：{input_dir}")
    check_validation_errors(input_dir)

if __name__ == '__main__':
    main()