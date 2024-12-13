import os
import re
from datetime import datetime
import traceback

def process_satellite_timematch(input_dir, output_dir, target_sensor, source_type, time_threshold):
    """
    处理卫星数据间的时间匹配
    """
    # 参数映射字典
    PARAM_MAPPING = {
        'AQUA': {
            'Rrs412': 'Rrs412', 
            'Rrs443': 'Rrs443', 
            'Rrs490': 'Rrs488',
            'Rrs520': 'Rrs531', 
            'Rrs565': 'Rrs555', 
            'Rrs670': 'Rrs667',
            'Rrs750': None, 
            'Rrs865': None, 
            'sst': 'sst', 
            'AOT': 'AOT',
            'chl': 'chl',
            'Kd': 'Kd',
            'ipar': 'ipar',
        },
        'TERRA': {
            'Rrs412': 'Rrs412',
            'Rrs443': 'Rrs443', 
            'Rrs490': 'Rrs488',
            'Rrs520': 'Rrs531', 
            'Rrs565': 'Rrs555', 
            'Rrs670': 'Rrs667',
            'Rrs750': None, 
            'Rrs865': None, 
            'sst': 'sst', 
            'AOT': 'AOT',
            'chl': 'chl',
            'Kd': 'Kd',
            'ipar': 'ipar',
        },
        'SNPP': {
            'Rrs412': 'Rrs410', 
            'Rrs443': 'Rrs443', 
            'Rrs490': 'Rrs486',
            'Rrs520': None, 
            'Rrs565': 'Rrs551', 
            'Rrs670': 'Rrs671',
            'Rrs750': None, 
            'Rrs865': None, 
            'sst': 'sst', 
            'AOT': 'AOT',
            'chl': 'chl',
            'Kd': 'Kd',
            'ipar': None,
        },
        'JPSS': {
            'Rrs412': 'Rrs411', 
            'Rrs443': 'Rrs445', 
            'Rrs490': 'Rrs489',
            'Rrs565': 'Rrs556', 
            'Rrs670': 'Rrs667', 
            'Rrs750': None,
            'Rrs865': None, 
            'sst': 'sst', 
            'AOT': 'AOT',
            'chl': 'chl',
            'Kd': 'Kd',
            'ipar': None,
        },
    }

    def extract_datetime_from_filename(filename):
        """从文件名中提取时间信息"""
        time_str = re.search(r'\d{14}', filename)
        if time_str:
            return datetime.strptime(time_str.group(), '%Y%m%d%H%M%S')
        return None

    def calculate_time_difference(time1, time2):
        """计算两个时间的差值（小时）"""
        time_diff = abs(time1 - time2)
        return time_diff.total_seconds() / 3600

    def save_match_result(result_file, target_file, source_file, time_diff):
        """保存匹配结果"""
        try:
            with open(os.path.join(output_dir, result_file), 'w') as f:
                f.write(f"{target_file}\n")
                f.write(f"{source_file}\n")
                f.write(f"{time_diff:.1f}\n")
            print(f"成功保存匹配结果到: {result_file}")
        except Exception as e:
            print(f"保存匹配结果失败: {str(e)}")

    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n开始处理卫星数据时间匹配...")
        print(f"目标传感器: {target_sensor}")
        print(f"检验源: {source_type}")
        print(f"时间阈值: {time_threshold}小时")
        
        # 获取目标传感器的数据文件
        target_files = [f for f in os.listdir(input_dir) 
                       if f.startswith(f"{target_sensor}_") and 
                       any(x.lower() in f.lower() for x in ['Rrs', 'sst', 'AOT', 'chl','Kd', 'ipar']) and 
                       f.endswith('.txt')]
        
        if not target_files:
            print(f"未找到{target_sensor}的数据文件")
            return False
          
        # 定义参数列表
        target_bands = ['Rrs412', 'Rrs443', 'Rrs490', 'Rrs520', 'Rrs565', 
                       'Rrs670', 'Rrs750', 'Rrs865']
        other_params = ['sst', 'AOT', 'chl', 'Kd', 'ipar']
        
        # 处理每个目标文件
        for target_file in target_files:
            # 提取时间信息
            target_time = extract_datetime_from_filename(target_file)
            if not target_time:
                print(f"无法从文件名提取时间: {target_file}")
                continue
            
            # 识别参数类型
            param_type = None
            for band in target_bands:
                if band in target_file:
                    param_type = band
                    break
                if not param_type:
                    for param in other_params:
                        if param in target_file:    # 如果文件名中包含参数名
                            param_type = param      # 设置参数类型
                            break  
            
            if not param_type:
                print(f"无法识别参数类型: {target_file}")
                continue
           
            # 生成结果文件名
            result_filename = f"timeresult_{target_sensor}_{source_type}_{param_type}_" \
                            f"{target_time.strftime('%Y%m%d%H%M%S')}.txt"
            
            # 获取对应的源参数名
            source_param = PARAM_MAPPING[source_type].get(param_type)
            if not source_param:
                print(f"无对应参数: {param_type}")
                open(os.path.join(output_dir, result_filename), 'w').close()
                continue
                
            # 查找源文件
            source_files = [f for f in os.listdir(input_dir) 
                          if f.startswith(f"{source_type}_") and 
                          source_param.lower() in f.lower()]
            
            if not source_files:
                print(f"未找到匹配的源文件: {source_param}")
                open(os.path.join(output_dir, result_filename), 'w').close()
                continue
                
            # 查找最小时间差的文件
            min_diff = float('inf')
            matching_file = None
            
            for source_file in source_files:
                source_time = extract_datetime_from_filename(source_file)
                if source_time:
                    time_diff = calculate_time_difference(target_time, source_time)
                    if time_diff < min_diff:
                        min_diff = time_diff
                        matching_file = source_file
            
            # 检查是否在时间阈值内
            if matching_file and min_diff <= time_threshold:
                save_match_result(result_filename, target_file, matching_file, min_diff)
            else:
                print(f"未找到在{time_threshold}小时内的匹配文件")
                open(os.path.join(output_dir, result_filename), 'w').close()
        
        # 保存时间阈值信息
        with open(os.path.join(output_dir, 'timesize.txt'), 'w') as f:
            f.write(f"{time_threshold}")
            
        return True
        
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        traceback.print_exc()
        return False

def process_xc_timematch(input_dir, output_dir, target_sensor, time_threshold):
    """
    处理现场数据时间匹配
    """
    def extract_datetime_from_filename(filename):
        """从文件名中提取时间信息"""
        time_str = re.search(r'\d{14}', filename)
        if time_str:
            return datetime.strptime(time_str.group(), '%Y%m%d%H%M%S')
        return None

    def calculate_time_difference(time1, time2):
        """计算两个时间的差值（小时）"""
        time_diff = abs(time1 - time2)
        return time_diff.total_seconds() / 3600

    def extract_time_from_line(line):
        """从现场数据行中提取时间信息"""
        try:
            parts = line.strip().split()
            if len(parts) >= 2:
                date = parts[0]
                time = parts[1]
                datetime_str = f"{date}{time}"
                return datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
        except Exception as e:
            print(f"时间解析错误: {str(e)}")
            return None

    def save_match_result(result_file, target_file, xcf_file, match_time, time_diff):
        """保存匹配结果"""
        try:
            with open(os.path.join(output_dir, result_file), 'w') as f:
                f.write(f"{target_file}\n")
                f.write(f"{xcf_file}\n")
                f.write(f"{match_time.strftime('%Y%m%d%H%M%S')}\n")
                f.write(f"{time_diff:.1f}\n")
            print(f"成功保存匹配结果到: {result_file}")
        except Exception as e:
            print(f"保存匹配结果失败: {str(e)}")

    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n开始处理现场数据时间匹配...")
        print(f"目标传感器: {target_sensor}")
        print(f"时间阈值: {time_threshold}小时")
        
        # 获取目标传感器的数据文件
        target_files = [f for f in os.listdir(input_dir) 
                       if f.startswith(f"{target_sensor}_") and 
                       any(x in f for x in ['Rrs', 'sst', 'AOT', 'chl', 'nLw', 'CDOM', 'TSM']) and 
                       f.endswith('.txt')]
        
        print("\n找到的目标文件:")
        for f in target_files:
            print(f)

        # 查找对应的现场数据文件
        xc_files = [f for f in os.listdir(input_dir) 
                       if f.startswith("XCf_") and 
                       any(x in f for x in ['Rrs', 'sst', 'AOT', 'Chl',  'nLw', 'CDOM', 'TSM']) and 
                       f.endswith('.txt')]
        

        print("\n找到的现场数据文件:")  # 添加打印
        for f in xc_files:
            print(f)

        if not target_files:
            print(f"未找到{target_sensor}的数据文件")
            return False


        if not xc_files:
            print(f"未找到{xc_files}的数据文件")
            return False
        
        # 处理每个目标文件
        for target_file in target_files:
            print(f"\n正在处理目标文件: {target_file}")

            # 提取时间信息
            target_time = extract_datetime_from_filename(target_file)
            if not target_time:
                print(f"无法从文件名提取时间: {target_file}")
                continue
            
            # 获取参数类型
            param_type = target_file.split('_')[1]
            print(f"参数类型: {param_type}")

            matching_xc_files = [f for f in xc_files if f.lower().startswith(f"xcf_{param_type.lower()}_")]
            print(f"匹配的现场数据文件: {matching_xc_files}")

            if not matching_xc_files:
                print(f"未找到参数{param_type}的现场数据文件")
                continue


            # 生成结果文件名
            result_filename = f"timeresult_{target_sensor}_XC_{param_type}_" \
                            f"{target_time.strftime('%Y%m%d%H%M%S')}.txt"
            
            # 查找最佳匹配
            min_diff = float('inf')
            best_match = None
            best_match_time = None
            
            # 遍历所有匹配的现场数据文件
            for xc_file in matching_xc_files:
                xc_path = os.path.join(input_dir, xc_file)
                try:
                    with open(xc_path, 'r', encoding='utf-8') as f:
                        # 跳过前四行（标题行）
                        for _ in range(4):
                            next(f)                     
                        # 处理数据行
                        for line in f:
                            xc_time = extract_time_from_line(line)
                            if xc_time:
                                time_diff = calculate_time_difference(target_time, xc_time)
                                if time_diff < min_diff:
                                    min_diff = time_diff
                                    best_match = xc_file
                                    best_match_time = xc_time

                except Exception as e:
                    print(f"处理文件{xc_file}时出错: {str(e)}")
                    continue

            # 保存最佳匹配结果
            if best_match and min_diff <= time_threshold:
                save_match_result(result_filename, target_file, best_match, 
                                best_match_time, min_diff)
            else:
                print(f"未找到在{time_threshold}小时内的匹配记录")
                open(os.path.join(output_dir, result_filename), 'w').close()

        # 保存时间阈值信息
        with open(os.path.join(output_dir, 'timesize.txt'), 'w') as f:
            f.write(f"{time_threshold}")
            
        return True
        
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        traceback.print_exc()
        return False

def main():
    input_dir = r'C:\Users\H\Desktop\new_HY_check\output'
    output_dir = r'C:\Users\H\Desktop\new_HY_check\output'
    target_sensor = 'HY3A'
    source_type = 'TERRA'
    time_threshold = 20000
    process_satellite_timematch(input_dir, output_dir, target_sensor, source_type, time_threshold)
    # process_xc_timematch(input_dir, output_dir, target_sensor, time_threshold)

if __name__ == '__main__':
    main()