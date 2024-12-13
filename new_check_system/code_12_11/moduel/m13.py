import os
import glob

def process_reports(input_dir):
    # 存储所有找到的产品名称
    products = []
    # 存储基本信息（只需要第一个文件的基本信息）
    basic_info = []
    first_file = True
    
    # 查找所有report_开头的文件
    report_files = glob.glob(os.path.join(input_dir, "report_*.txt"))
    
    # 获取第一个文件的时间信息用于生成输出文件名
    first_report = report_files[0]
    time_str = first_report.split('_')[-1].replace('.txt', '')
    
    for report_file in report_files:
        with open(report_file, 'r') as f:
            lines = f.readlines()
        
        # 提取产品名称
        for line in lines:
            if line.startswith('/Product='):
                product = line.strip().split('=')[1]
                if product not in products:
                    products.append(product)
        
        # 只从第一个文件获取基本信息
        if first_file:
            for line in lines:
                # 跳过不需要的统计信息行
                if any(line.startswith(skip) for skip in [
                    '/Time Difference=',
                    '/Total pixel count=',
                    '/bias=',
                    '/STD=',
                    '/RMS=',
                    '/R=',
                    '/Effective pixel count=',
                    '/valresult=',
                    '/Product='
                ]):
                    continue
                
                # 处理文件名行，删除.txt后缀和产品名称
                if line.startswith('/HY file='):
                    line = line.replace('.txt', '')
                    for product in products:
                        line = line.replace(f'_{product}_', '_')
                elif line.startswith('/On-site file='):
                    line = line.replace('.txt', '')
                    for product in products:
                        line = line.replace(f'_{product}_', '_')
                
                basic_info.append(line)
            first_file = False
    
    # 生成单个输出文件
    output_filename = f'log_HY3A_TERRA_ALL_{time_str}.txt'
    
    # 准备写入内容
    output_lines = basic_info.copy()
    # 在适当位置插入合并的产品信息
    product_line = '/Product=' + '/'.join(sorted(products)) + '\n'
    
    # 找到合适的位置插入产品信息（通常在前几行）
    insert_position = min(3, len(output_lines))  # 假设在第3行或文件开头插入
    output_lines.insert(insert_position, product_line)
    
    # 写入新文件
    with open(os.path.join(input_dir, output_filename), 'w') as f:
        f.writelines(output_lines)

# 使用示例
if __name__ == "__main__":
    input_directory = r'C:\Users\H\Desktop\new_HY_check\code_12_11\moduel\test'
    process_reports(input_directory)