import os

def make_satellite_report_data(input_dir):
    # 处理valresult文件
    for f in [f for f in os.listdir(input_dir) if f.startswith("valresult_")]:
        output_filename = f.replace("valresult_", "report_")
        
        # 尝试不同的编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1']
        for encoding in encodings:
            try:
                with open(os.path.join(input_dir, f), 'r', encoding=encoding) as file:
                    lines = file.readlines()
                    report_data = {}
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        # 收集所需数据
                        if line.startswith('/HY satellite'):
                            report_data['/HY satellite'] = line.split('=')[1].strip()
                        elif line.startswith('/product'):
                            report_data['/Product'] = line.split('=')[1].strip()
                        elif line.startswith('/HY time'):
                            report_data['/HY time'] = line.split('=')[1].strip()
                        elif line.startswith('/HY file'):
                            report_data['/HY file'] = line.split('=')[1].strip()
                        elif line.startswith('/Validation source'):
                            report_data['/Validation Source'] = line.split('=')[1].strip()
                        elif line.startswith('/On-site time'):
                            report_data['/On-site time'] = line.split('=')[1].strip()
                        elif line.startswith('/On-site file'):
                            report_data['/On-site file'] = line.split('=')[1].strip()
                        elif line.startswith('/Time difference'):
                            report_data['/Time Difference'] = line.split('=')[1].strip()
                        elif line.startswith('/Total pixel count'):
                            report_data['/Total pixel count'] = line.split('=')[1].strip()
                    
                    with open(os.path.join(input_dir, output_filename), 'w', encoding='utf-8') as outfile:
                        for key, value in report_data.items():
                            outfile.write(f"{key}={value}\n")
                break
            except UnicodeDecodeError:
                if encoding == encodings[-1]:  # 如果是最后一个编码尝试
                    print(f"Failed to decode file {f} with all encodings")
                continue
            except Exception as e:
                print(f"Error processing file {f}: {str(e)}")
                break

    # 处理statistic文件
    for f in [f for f in os.listdir(input_dir) if f.startswith("statistic_")]:
        report_filename = f.replace("statistic_", "report_")
        
        for encoding in encodings:
            try:
                with open(os.path.join(input_dir, f), 'r', encoding=encoding) as file:
                    lines = file.readlines()
                    # 获取最后一行数据
                    last_line = lines[-1].strip()
                    # 分割数据
                    values = last_line.split()
                    
                    # 将数据写入report文件
                    with open(os.path.join(input_dir, report_filename), 'a', encoding='utf-8') as outfile:
                        outfile.write(f'/bias={values[0]}\n')
                        outfile.write(f'/STD={values[1]}\n')
                        outfile.write(f'/RMS={values[2]}\n')
                        outfile.write(f'/R={values[3]}\n')
                break
            except UnicodeDecodeError:
                if encoding == encodings[-1]:
                    print(f"Failed to decode file {f} with all encodings")
                continue
            except Exception as e:
                print(f"Error processing file {f}: {str(e)}")
                break

    # 添加处理resstastic文件的部分
    for f in [f for f in os.listdir(input_dir) if f.startswith("resstastic_")]:
        report_filename = f.replace("resstastic_", "report_")
        
        for encoding in encodings:
            try:
                with open(os.path.join(input_dir, f), 'r', encoding=encoding) as file:
                    lines = file.readlines()
                    
                    # 只查找包含总像元数和有效检验像元数的行
                    for line in lines:
                        if "总像元数" in line and "有效检验像元数" in line:
                            parts = line.strip().split('\t')
                            total_pixels = parts[0].split('：')[1]
                            valid_pixels = parts[1].split('：')[1]
                            
                            # 将数据追加到report文件
                            with open(os.path.join(input_dir, report_filename), 'a', encoding='utf-8') as outfile:
                                outfile.write(f'/Effective pixel count={total_pixels}\n')
                                outfile.write(f'/valresult={valid_pixels}\n')
                            break
                break
            except UnicodeDecodeError:
                if encoding == encodings[-1]:
                    print(f"Failed to decode file {f} with all encodings")
                continue
            except Exception as e:
                print(f"Error processing file {f}: {str(e)}")
                break

def main():
    input_dir = r"C:\Users\H\Desktop\new_HY_check\code\moduel\temp"
    make_satellite_report_data(input_dir)

if __name__ == "__main__":
    main()