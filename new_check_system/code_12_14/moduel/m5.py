import numpy as np
import os
import traceback
from scipy import interpolate
from datetime import datetime

def process_satellite_spacematch(input_dir, output_dir, target_sensor, source_type):
    """
    处理卫星数据空间匹配
    """
    # 卫星命名规则配置
    SATELLITE_NAMING_RULES = {
        'AQUA': {
            'prefix': 'AQUA',
            'output_prefix': 'AQUA1',
            'lat_format': 'AQUA_Lat',
            'lon_format': 'AQUA_Lon',
            'flag_format': 'AQUA_flag1',
        },
        'TERRA': {
            'prefix': 'TERRA',
            'output_prefix': 'TERRA1',
            'lat_format': 'TERRA_Lat',
            'lon_format': 'TERRA_Lon',
            'flag_format': 'TERRA_flag1',
        },
        'SNPP': {
            'prefix': 'SNPP',
            'output_prefix': 'SNPP1',
            'lat_format': 'SNPP_Lat',
            'lon_format': 'SNPP_Lon',
            'flag_format': 'SNPP_flag1',
        },
        'JPSS': {
            'prefix': 'JPSS',
            'output_prefix': 'JPSS1',
            'lat_format': 'JPSS_Lat',
            'lon_format': 'JPSS_Lon',
            'flag_format': 'JPSS_flag1',
        }
    }


    def read_timeresult():
        """读取时间匹配结果文件"""
        # 获取所有匹配的时间结果文件
        timeresult_files = [f for f in os.listdir(input_dir)
                        if f.startswith(f'timeresult_{target_sensor}_{source_type}_')]
        
        if not timeresult_files:
            print(f"未找到{target_sensor}和{source_type}的时间匹配结果文件")
            return None

        print(f"\n找到 {len(timeresult_files)} 个时间匹配结果文件:")
        for f in timeresult_files:
            print(f"- {f}")

        match_results = []
        for timeresult_file in timeresult_files:
            try:
                with open(os.path.join(input_dir, timeresult_file), 'r') as f:
                    lines = f.readlines()
                    if len(lines) < 3:
                        print(f"无效的时间匹配结果文件: {timeresult_file}")
                        continue
                    match_results.append({
                        'target_file': lines[0].strip(),
                        'source_file': lines[1].strip(),
                        'time_diff': float(lines[2].strip())
                    })
            except Exception as e:
                print(f"处理文件 {timeresult_file} 时出错: {e}")
                continue

        print(f"成功读取 {len(match_results)} 个匹配结果")
        return match_results if match_results else None

    def process_single_match(target_file, source_file, time_diff):
        """处理单个匹配对的空间匹配"""
        try:
            # 从文件名中提取信息
            target_parts = target_file.split('_')
            source_parts = source_file.split('_')
            
            target_sensor = target_parts[0]
            source_type = source_parts[0]

            target_time = target_parts[-1].replace('.txt', '')
            source_time = source_parts[-1].replace('.txt', '')
            
            # 提取参数类型
            if any(part.startswith('Rrs') for part in target_parts):
                param_type = next(part for part in target_parts if part.startswith('Rrs'))
            elif 'AOT' in target_file:
                param_type = 'AOT'
            elif 'chl' in target_file.lower():
                param_type = 'chl'
            elif 'sst' in target_file.lower():
                param_type = 'sst'
            elif 'ipar' in target_file.lower():
                param_type = 'ipar'
            elif 'Kd' in target_file:
                param_type = 'Kd'
            else:
                print(f"无法识别的参数类型: {target_file}")
                return False
                
            print(f"\n处理文件对: {target_file} - {source_file}")
            print(f"参数类型: {param_type}")
            
            # 读取数据
            target_lat = np.genfromtxt(os.path.join(input_dir, f"{target_sensor}_lat_{target_time}.txt"))
            target_lon = np.genfromtxt(os.path.join(input_dir, f"{target_sensor}_lon_{target_time}.txt"))
            target_flag = np.genfromtxt(os.path.join(input_dir, f"{target_sensor}_flag1_{target_time}.txt"))
            
            naming_rule = SATELLITE_NAMING_RULES[source_type]
            source_lat = np.genfromtxt(os.path.join(input_dir, f"{naming_rule['lat_format']}_{source_time}.txt"))
            source_lon = np.genfromtxt(os.path.join(input_dir, f"{naming_rule['lon_format']}_{source_time}.txt"))
            source_flag = np.genfromtxt(os.path.join(input_dir, f"{naming_rule['flag_format']}_{source_time}.txt"))
            source_data = np.genfromtxt(os.path.join(input_dir, source_file))
            
            # 处理无效值和插值
            source_data[source_flag == 1] = np.nan
            valid = ~np.isnan(source_data)
            if not np.any(valid):
                print("警告：没有有效的源数据点进行插值")
                return False
                
            interpolated_data = interpolate.griddata(
                points=(source_lon[valid], source_lat[valid]),
                values=source_data[valid],
                xi=(target_lon, target_lat),
                method='linear',
                fill_value=np.nan
            )
            
            # 更新标识
            mask = (target_flag == 1) | (np.isnan(interpolated_data))
            interpolated_data[mask] = np.nan
            target_flag[mask] = 1
            
            # 保存结果
            interpolated_filename = f"{naming_rule['output_prefix']}_{param_type}_{source_time}.txt"
            flag_filename = f"{target_sensor}_flag1_{param_type}_{target_time}.txt"
            result_filename = f"spaceresult_{target_sensor}_{source_type}_{param_type}_{target_time}.txt"
            
            np.savetxt(os.path.join(output_dir, interpolated_filename), interpolated_data, fmt='%.6f')
            np.savetxt(os.path.join(output_dir, flag_filename), target_flag, fmt='%d')
            
            with open(os.path.join(output_dir, result_filename), 'w') as f:
                f.write(f"{target_file}\n")
                f.write(f"{source_file}\n")
                f.write(f"{time_diff:.1f}\n")
                
            return True
            
        except Exception as e:
            print(f"处理匹配对失败: {e}")
            return False
        

    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 读取时间匹配结果
        match_results = read_timeresult()
        if not match_results:
            return False
            
        # 处理每个匹配结果
        success_count = 0
        for result in match_results:
            if process_single_match(**result):
                success_count += 1
                
        print(f"\n处理完成:")
        
        return success_count > 0
        
    except Exception as e:
        print(f"处理卫星数据匹配失败: {e}")
        traceback.print_exc()
        return False


def process_xc_spacematch(input_dir, output_dir, target_sensor, window_size):
    """
    处理现场数据空间匹配
    """
    def process_single_match(target_file, source_file, time_diff):
        """处理单个匹配对"""
        try:
            # 提取基本信息
            target_parts = target_file.split('_')
            target_time = target_parts[-1].replace('.txt', '')
            
            # 读取目标数据
            target_data = np.genfromtxt(os.path.join(input_dir, target_file))
            target_lat = np.genfromtxt(os.path.join(input_dir, f"{target_sensor}_lat_{target_time}.txt"))
            target_lon = np.genfromtxt(os.path.join(input_dir, f"{target_sensor}_lon_{target_time}.txt"))
            target_flag = np.genfromtxt(os.path.join(input_dir, f"{target_sensor}_flag1_{target_time}.txt"))
            
            # 重塑数据为二维数组
            total_size = target_data.size
            for i in range(1000, 6000):
                if total_size % i == 0:
                    rows = i
                    cols = total_size // i
                    break
            
            target_data = target_data.reshape(rows, cols)
            target_lat = target_lat.reshape(rows, cols)
            target_lon = target_lon.reshape(rows, cols)
            target_flag = target_flag.reshape(rows, cols)
            
            # 读取现场数据文件
            with open(os.path.join(input_dir, source_file), 'r') as f:
                for line in f:
                    if line.startswith('Latitude:'):
                        xcf_lat = float(line.split(':')[1])
                    elif line.startswith('Longitude:'):
                        xcf_lon = float(line.split(':')[1])
                    elif line and not line.startswith(('Data:', 'Date')):
                        parts = line.split()
                        if len(parts) >= 3:
                            xcf_time = datetime.strptime(f"{parts[0]}{parts[1]}", '%Y%m%d%H%M%S')
                            xcf_value = float(parts[2])
                            break
            
            # 找到最近的像元
            distances = np.sqrt((target_lat - xcf_lat)**2 + (target_lon - xcf_lon)**2)
            min_idx = np.unravel_index(np.argmin(distances), distances.shape)
            center_row, center_col = min_idx[0], min_idx[1]
                   
            # 检查是否在边界
            half_size = (window_size - 1) // 2
            if (center_row < half_size or 
                center_row >= rows - half_size or
                center_col < half_size or 
                center_col >= cols - half_size):
                print(f"匹配点在图像边界，跳过处理")
                return False
            
            # 计算窗口统计值
            window_data = target_data[center_row-half_size:center_row+half_size+1, 
                                    center_col-half_size:center_col+half_size+1]
            window_flag = target_flag[center_row-half_size:center_row+half_size+1, 
                                    center_col-half_size:center_col+half_size+1]
            
            # 获取有效数据
            valid_data = window_data[window_flag == 0]
            
            if len(valid_data) == 0:
                print(f"窗口内没有有效数据")
                return False
            
            # 计算统计值
            mean_value = np.mean(valid_data)
            valid_ratio = len(valid_data) / (window_size * window_size)
            cv = np.std(valid_data) / mean_value if mean_value != 0 else None
            
            # 保存结果
            result_filename = f"spaceresult_{target_sensor}_XC_{target_parts[1]}_{target_time}.txt"
            with open(os.path.join(output_dir, result_filename), 'w') as f:
                f.write(f"{target_file}\n")                    # 第1行：待检验数据文件名
                f.write(f"{source_file}\n")                    # 第2行：检验源数据文件名
                f.write(f"{center_row}\n")                     # 第3行：匹配位置行号
                f.write(f"{center_col}\n")                     # 第4行：匹配位置列号
                f.write(f"{mean_value:.4f}\n")                # 第5行：区域平均值
                f.write(f"{valid_ratio:.4f}\n")               # 第6行：有效像元比例
                f.write(f"{cv:.4f}\n" if cv is not None else "nan\n")  # 第7行：CV值
                f.write(f"{xcf_time.strftime('%Y%m%d%H%M%S')}\n")  # 第8行：检验源观测时间
                f.write(f"{xcf_value:.4f}\n")                 # 第9行：检验源观测值
                f.write(f"{time_diff:.1f}\n")                 # 第10行：时间差
            
            return True
            
        except Exception as e:
            print(f"处理匹配对失败: {e}")
            traceback.print_exc()
            return False

    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 读取时间匹配结果
        timeresult_files = [f for f in os.listdir(input_dir) 
                          if f.startswith(f'timeresult_{target_sensor}_XC_')]
        
        if not timeresult_files:
            print("未找到现场数据的时间匹配结果文件")
            return False
        
        # 处理每个匹配结果
        success_count = 0
        for timeresult_file in timeresult_files:
            try:
                with open(os.path.join(input_dir, timeresult_file), 'r') as f:
                    lines = f.readlines()
                    if len(lines) >= 4:  # 确保有足够的行数
                        if process_single_match(
                            target_file=lines[0].strip(),
                            source_file=lines[1].strip(),
                            time_diff=float(lines[3].strip())  # 使用第4行的时间差
                        ):
                            success_count += 1
                            
            except Exception as e:
                print(f"处理文件 {timeresult_file} 失败: {e}")
                continue
        
        print(f"处理完成，成功处理 {success_count} 个文件")
        return success_count > 0
        
    except Exception as e:
        print(f"处理现场数据匹配失败: {e}")
        traceback.print_exc()
        return False
    
def main():
    input_dir = r'C:\Users\H\Desktop\new_HY_check\output'
    output_dir = r'C:\Users\H\Desktop\new_HY_check\output'
    target_sensor = 'HY3A'
    source_type = 'TERRA'
    window_size = 3
    process_satellite_spacematch(input_dir, output_dir, target_sensor, source_type)
    # process_xc_spacematch(input_dir, output_dir, target_sensor, window_size)

if __name__ == "__main__":
    main()