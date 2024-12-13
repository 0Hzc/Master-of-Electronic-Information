import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def step8(input_directory, output_directory):
    """
    第八步：处理时间序列数据和绘制时间序列图
    """
    def read_valresult_files(input_directory,product):
        """读取所有valresult_HY1C_XC文件并按顺序存储时间和偏差数据"""
        times = []
        deviations = []
        
        file_pattern = os.path.join(input_directory, f'valresult_HY3A_XC_{product}_*')
        file_paths = sorted(glob.glob(file_pattern))
        
        for file_path in file_paths:
            with open(file_path, 'r') as file:
                onsite_time = None
                for line in file:
                    line = line.strip()
                    if line.startswith('/On-site time='):
                        onsite_time = line.split('=')[1].strip()
                    elif line.startswith('/') or not line:
                        continue
                    else:
                        try:
                            hy_value, onsite_value, difference = map(float, line.split())
                            if onsite_time:
                                times.append(onsite_time)
                                deviations.append(difference)
                        except (ValueError, IndexError):
                            continue
        
        return times, deviations

    def read_valresult_files_satellite(input_directory, product):
        """读取所有valresult开头但不含XC的文件并处理星星检验数据"""
        times = []
        deviations = []
        file_paths = []
        
        # print(f"\n开始读取{product}产品的星星检验数据...")
        
        # 支持所有可能的卫星类型
        satellites = ['TERRA', 'AQUA', 'SNPP', 'JPSS']
        for satellite in satellites:
            pattern = os.path.join(input_directory, f'valresult_HY3A_{satellite}_{product}_*.txt')
            matching_files = glob.glob(pattern)
            file_paths.extend(sorted(matching_files))
        
        # print(f"找到{len(file_paths)}个匹配的文件:")
        for f in file_paths:
            print(f"- {f}")
        
        for file_path in file_paths:
            print(f"\n处理文件: {os.path.basename(file_path)}")
            with open(file_path, 'r') as file:
                onsite_time = None
                for line in file:
                    line = line.strip()
                    if line.startswith('/On-site time='):
                        onsite_time = line.split('=')[1].strip()
                        # print(f"找到观测时间: {onsite_time}")
                    elif line.startswith('/validation result='):
                        try:
                            deviation = float(line.split('=')[1].strip().rstrip('%'))
                            if onsite_time:
                                times.append(onsite_time)
                                deviations.append(deviation)
                                # print(f"找到验证结果: {deviation}%")
                        except (ValueError, IndexError) as e:
                            print(f"处理验证结果时出错: {e}")
                            continue
        
        # print(f"\n总共读取到{len(times)}组数据")
        # if times:
        #     # print("数据样例:")
        #     for t, d in zip(times[:3], deviations[:3]):
        #         # print(f"时间: {t}, 偏差: {d}%")
        #     if len(times) > 3:
        #         print("...")
        
        return times, deviations, file_paths[0] if file_paths else None  # 返回第一个匹配的文件路径

    def write_output_file(times, deviations, output_directory, input_file_path):
        """将时间序列和偏差数据写入输出文件"""
        os.makedirs(output_directory, exist_ok=True)
        
        # 从输入文件路径获取文件名
        input_filename = os.path.basename(input_file_path)
        # 将 'valresult' 替换为 'timeseries'
        output_filename = input_filename.replace('valresult', 'timeseries')
        
        # 构建完整的输出路径
        output_path = os.path.join(output_directory, output_filename)
        
        # 写入数据
        with open(output_path, 'w') as file:
            for time, deviation in zip(times, deviations):
                file.write(f"{time}\t{deviation:.4f}\n")
        
        return output_path

    def format_time(time_str):
        time_str = str(time_str).zfill(14)
        return datetime.strptime(time_str, '%Y%m%d%H%M%S')

    def plot_time_series(input_files, output_dir):
        """为每个产品生成单独的时间序列图"""
        # 按产品分组文件
        product_files = {}
        for input_file in input_files:
            filename = os.path.basename(input_file)
            parts = filename.split('_')
            if len(parts) >= 4:
                product = parts[3]  # 获取产品名称
                if product not in product_files:
                    product_files[product] = []
                product_files[product].append(input_file)
        
        # 为每个产品绘制图形
        for product, files in product_files.items():
            plt.figure(figsize=(12, 6))
            colors = ['b', 'r', 'g', 'c', 'm', 'y', 'k']
            all_times = []
            
            for i, input_file in enumerate(files):
                df = pd.read_csv(input_file, sep='\t', header=None, names=['time', 'error'])
                df['time'] = df['time'].apply(format_time)
                all_times.extend(df['time'])
                
                file_name = os.path.basename(input_file)
                label = file_name.replace('timeseries_', '').replace('.txt', '')
                
                color = colors[i % len(colors)]
                plt.plot(df['time'], df['error'], color=color, linewidth=1, label=label)
            
            if all_times:  # 确保有数据
                # 使用第一个文件的名称作为基础
                first_file = os.path.basename(files[0])
                # 将'.txt' 替换为 '.jpg'
                output_filename = first_file.replace('.txt', '.jpg')
                
                plt.title(output_filename.replace('figure_', '').replace('.jpg', ''))
                plt.xlabel('Time')
                plt.ylabel('Error (%)')
                plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                plt.ylim(0, 100)
                plt.gcf().autofmt_xdate()
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                output_file = os.path.join(output_dir, output_filename)
                plt.savefig(output_file, bbox_inches='tight')
                plt.close()

    try:
        os.makedirs(output_directory, exist_ok=True)
        
        satellite_products = ['AOT','chl','Kd','sst','Rrs412', 'Rrs443', 'Rrs490', 'Rrs520', 'Rrs565', 'Rrs670','ipar']
        xc_products = ['AOT','chl','nLw','sst','TSM','CDOM','Rrs412', 'Rrs443', 'Rrs490', 'Rrs520', 'Rrs565', 'Rrs670','Rrs750','Rrs865']

        # 第一步：处理数据并生成中间文件
        output_files = []
        
        # 处理星地检验数据
        for xcproduct in xc_products:
            times_ground, deviations_ground = read_valresult_files(input_directory,xcproduct)
            if times_ground:
                start_time = min(times_ground)
                end_time = max(times_ground)
                output_file = write_output_file(times_ground, deviations_ground, 
                                            output_directory, start_time, end_time, "ground",xcproduct)
                output_files.append(output_file)
        
        # 处理星星检验数据
        for product in satellite_products:
            times_satellite, deviations_satellite, input_file_path = read_valresult_files_satellite(input_directory, product)
            if times_satellite and input_file_path:
                output_file = write_output_file(times_satellite, deviations_satellite, 
                                              output_directory, input_file_path)
                output_files.append(output_file)
        
        # 第二步：绘制时间序列图
        if output_files:
            plot_time_series(output_files, output_directory)
            return True
        else:
            print("没有找到有效的数据文件")
            return False
            
    except Exception as e:
        print(f"步骤8执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
def main():
    input_directory = r'C:\Users\H\Desktop\new_HY_check\code_12_11\test_m'
    output_directory = r'C:\Users\H\Desktop\new_HY_check\code_12_11\test_m'
    step8(input_directory, output_directory)

if __name__ == "__main__":
    main()
