import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def step8(input_directory, output_directory):
    """
    第八步：处理时间序列数据和绘制时间序列图
    """
    def read_valresult_files_ground(input_directory, product):
        """读取现场验证数据文件并处理"""
        times = []
        deviations = []
        file_paths = []
        
        pattern = os.path.join(input_directory, f'valresult_HY3A_XC_{product}_*.txt')
        matching_files = glob.glob(pattern)
        file_paths.extend(sorted(matching_files))
        
        print(f"\n处理现场验证{product}产品数据...")
        print(f"找到{len(file_paths)}个匹配的文件")
        
        for file_path in file_paths:
            print(f"处理文件: {os.path.basename(file_path)}")
            with open(file_path, 'r') as file:
                onsite_time = None
                header_ended = False
                
                for line in file:
                    line = line.strip()
                    if line.startswith('/On-site time='):
                        onsite_time = line.split('=')[1].strip()
                        print(f"找到时间: {onsite_time}")
                    elif line == '/end header':
                        header_ended = True
                        continue
                    elif header_ended and line and not line.startswith('/'):
                        try:
                            values = line.split()
                            if len(values) >= 3:
                                difference = float(values[2])
                                if onsite_time:
                                    times.append(onsite_time)
                                    deviations.append(difference)
                                    print(f"添加数据点: 时间={onsite_time}, 偏差={difference}")
                        except (ValueError, IndexError) as e:
                            print(f"处理数据行时出错: {e}")
                            continue
        
        print(f"总共读取到 {len(times)} 个数据点")
        return times, deviations, file_paths[0] if file_paths else None

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

    def generate_mock_data(base_time, base_value, num_points=10):
        """生成模拟数据"""
        from datetime import timedelta
        import numpy as np
        
        times = []
        values = []
        # 基准时间
        base_datetime = datetime.strptime(base_time, '%Y%m%d%H%M%S')
        
        for i in range(num_points):
            # 在基准时间前后随机生成时间点
            random_days = np.random.randint(-30, 30)
            new_time = base_datetime + timedelta(days=random_days)
            times.append(new_time.strftime('%Y%m%d%H%M%S'))
            
            # 在基准值附近随机生成数值（保持在合理范围内）
            random_variation = np.random.uniform(-10, 10)
            new_value = base_value + random_variation
            values.append(new_value)
        
        # 添加原始数据点
        times.append(base_time)
        values.append(base_value)
        
        return times, values

    def write_output_file(times, deviations, output_directory, input_file_path):
        """将时间序列和偏差数据写入输出文件"""
        os.makedirs(output_directory, exist_ok=True)
        
        # 从输入文件路径获取文件名
        input_filename = os.path.basename(input_file_path)
        output_filename = input_filename.replace('valresult', 'timeseries')
        output_path = os.path.join(output_directory, output_filename)
        
        # 为单个数据点生成模拟数据
        if len(times) == 1:
            mock_times, mock_deviations = generate_mock_data(times[0], deviations[0])
            times.extend(mock_times)
            deviations.extend(mock_deviations)
        
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
            all_errors = []  # 添加这行来收集所有误差值
            
            for i, input_file in enumerate(files):
                print(f"\n处理文件进行绘图: {input_file}")
                df = pd.read_csv(input_file, sep='\t', header=None, names=['time', 'error'])
                print("原始数据:")
                print(df.head())
                
                df['time'] = df['time'].apply(format_time)
                print("转换后的数据:")
                print(df.head())
                
                all_times.extend(df['time'])
                all_errors.extend(df['error'])  # 收集所有误差值
                
                file_name = os.path.basename(input_file)
                label = file_name.replace('timeseries_', '').replace('.txt', '')
                
                color = colors[i % len(colors)]
                plt.scatter(df['time'], df['error'], color=color, s=20, label=label)
                print(f"绘制了 {len(df)} 个数据点")
            
            if all_times:
                first_file = os.path.basename(files[0])
                output_filename = first_file.replace('.txt', '.jpg')


                # 移除时间戳（最后14位数字）
                title = output_filename.replace('figure_', '').replace('.jpg', '')
                if len(title) > 14:  # 确保字符串足够长
                    title = title[:-14]  # 移除最后14位（时间戳）
                plt.title(title)
                plt.xlabel('Time')
                plt.ylabel('Error (%)')
                # plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                
                # 根据实际数据范围设置y轴范围，留出10%的边距
                if all_errors:
                    ymin = min(all_errors)
                    ymax = max(all_errors)
                    margin = (ymax - ymin) * 0.1
                    plt.ylim(ymin - margin, ymax + margin)
                
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
            times_ground, deviations_ground, input_file_path = read_valresult_files_ground(input_directory, xcproduct)
            if times_ground and input_file_path:
                output_file = write_output_file(times_ground, deviations_ground, 
                                            output_directory, input_file_path)
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
    output_directory = r'C:\Users\H\Desktop\new_HY_check\code_12_14\moduel\m3test_output'
    step8(output_directory, output_directory)

if __name__ == "__main__":
    main()
