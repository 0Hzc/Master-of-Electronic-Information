import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np
from collections import defaultdict

def step9(input_directory, output_directory):
    """
    第九步：处理星地检验和星星检验数据，生成统计结果和图表
    """
    # 设置字体
    plt.rcParams['font.family'] = 'SimHei'
 
    def get_timestamp():
        """获取时间戳"""
        return datetime.now().strftime("%Y%m%d%H%M%S")
    
    def extract_timestamp_from_files(files):
        """从文件名中提取时间戳"""
        timestamps = []
        for file in files:
            parts = file.split('_')
            if len(parts) >= 4:
                try:
                    # 假设最后一部分包含时间戳
                    timestamp = parts[-1].split('.')[0]
                    if len(timestamp) == 14:  # 确保是完整的时间戳格式
                        timestamps.append(timestamp)
                except:
                    continue
        
        return timestamps[0] if timestamps else get_timestamp()


    def read_valresult_file(file_path):
        """读取验证结果文件"""
        # print(f"正在读取验证结果文件: {file_path}")
        try:
            result = {
                'header': {},
                'data': [],
                'filename': os.path.basename(file_path)
            }
            
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                data_start = False
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line == '/begin header':
                        continue
                    elif line == '/end header':
                        data_start = True
                    elif line.startswith('/'):
                        if '=' in line:
                            key, value = line[1:].split('=', 1)
                            result['header'][key.strip()] = value.strip()
                    elif data_start:
                        try:
                            values = line.split('\t')
                            if len(values) >= 2:  # 确保至少有两列数据
                                result['data'].append(values)
                        except ValueError:
                            continue
            
            return result
        except Exception as e:
            print(f"读取验证文件时出错 {file_path}: {str(e)}")
            return None

    def read_spaceresult_file(file_path):
        """读取空间结果文件"""
        # print(f"正在读取空间结果文件: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                if len(lines) >= 3:
                    return {
                        'hy_file': lines[0].strip(),
                        'compare_file': lines[1].strip(),
                        'time_diff': float(lines[2].strip())
                    }
        except Exception as e:
            print(f"读取空间结果文件时出错 {file_path}: {str(e)}")
            return None


    def extract_satellite_type(filename):
        """从文件名中提取卫星类型"""
        if 'TERRA' in filename.upper():
            return 'TERRA'
        elif 'AQUA' in filename.upper():
            return 'AQUA'
        elif 'SNPP' in filename.upper():
            return 'SNPP'
        elif 'JPSS' in filename.upper():
            return 'JPSS'
        return 'UNKNOWN'  # 默认返回值

    def analyze_star_check(valresults, spaceresults, input_directory):
        """分析星星检验结果"""
        total_pixels = 0
        valid_pixels = 0
        
        time_diff_counts = {
            "<0.5h": 0,
            "0.5~1h": 0,
            "1~1.5h": 0,
            "1.5~3h": 0,
            ">3h": 0
        }
        
        # 从valresults中获取产品名称
        product = None
        if valresults and len(valresults) > 0:
            filename = valresults[0].get('filename', '')
            parts = filename.split('_')
            if len(parts) >= 4:
                product = parts[3].split('.')[0]
        
        if not product:
            print("无法确定产品名称")
            return None, None, None, None, None
        
        # 初始化difference_counts
        if product == 'sst':
            difference_counts = {
                'min_diff': float('inf'),
                'max_diff': float('-inf'),
                'differences': []
            }
        else:
            difference_counts = {
                "<10": 0,
                "10~30": 0,
                "30~50": 0,
                "50~100": 0,
                ">100": 0
            }
        
        # 在input_directory中查找对应的HY3A文件
        hy3a_file = None
        product_file_mapping = {
            'AOT': 'HY3A_AOT_',
            'chl': 'HY3A_chl_a_',
            'Kd': 'HY3A_Kd_',
            'sst': 'HY3A_sst_',
            'Rrs412': 'HY3A_Rrs412_',
            'Rrs443': 'HY3A_Rrs443_',
            'Rrs490': 'HY3A_Rrs490_',
            'Rrs520': 'HY3A_Rrs520_',
            'Rrs565': 'HY3A_Rrs565_',
            'Rrs670': 'HY3A_Rrs670_',
            'ipar': 'HY3A_ipar_'
        }
        
        file_prefix = product_file_mapping.get(product)
        if file_prefix:
            for filename in os.listdir(input_directory):
                if filename.startswith(file_prefix) and not filename.startswith(file_prefix + 'flag1'):
                    hy3a_file = os.path.join(input_directory, filename)
                    break
        
        if not hy3a_file:
            print(f"未找到产品 {product} 对应的HY3A文件")
            return None, None, None, None, None
        
        # print(f"找到产品文件: {hy3a_file}")
        
        # 读取HY3A文件并计算有效值个数
        try:
            with open(hy3a_file, 'r') as file:
                # print(f"正在读取文件: {hy3a_file}")
                # print("文件前3行内容:")
                # for i, line in enumerate(file):
                #     if i < 3:
                #         print(line.strip())
                #     else:
                #         break

                file.seek(0)

                total_lines = 0
                invalid_count = 0
                for line in file:
                    total_lines += 1
                    try:
                        value = float(line.strip())
                        if (abs(value + 999.000000) < 0.000001 or
                            abs(value + 999.0) < 0.000001 or
                            abs(value + 999) < 0.000001 or
                            value < -900):
                            invalid_count += 1
                            # if invalid_count < 5:
                            #     print(f"发现无效值: {value}")
                    except ValueError as e:
                        invalid_count += 1
                
                total_pixels = total_lines - invalid_count
                # print(f"总行数: {total_lines}")
                # print(f"无效值数量: {invalid_count}")
                # print(f"有效值数量: {total_pixels}")
        except Exception as e:
            print(f"读取HY3A文件失败: {e}")
            return None, None, None, None, None
        
        # 处理valresults数据
        for result in valresults:
            if 'header' in result:
                valid_pixels += int(result['header'].get('Effective pixel count', 0))
                
                for row in result['data']:
                    try:
                        diff = float(row[-1])
                        if product == 'sst':
                            difference_counts['min_diff'] = min(difference_counts['min_diff'], diff)
                            difference_counts['max_diff'] = max(difference_counts['max_diff'], diff)
                            difference_counts['differences'].append(diff)
                        else:
                            if diff < 10:
                                difference_counts["<10"] += 1
                            elif diff < 30:
                                difference_counts["10~30"] += 1
                            elif diff < 50:
                                difference_counts["30~50"] += 1
                            elif diff < 100:
                                difference_counts["50~100"] += 1
                            else:
                                difference_counts[">100"] += 1
                    except (ValueError, IndexError):
                        continue
        
        # 处理spaceresults数据
        for result in spaceresults:
            time_diff = result['time_diff']
            if time_diff < 0.5:
                time_diff_counts["<0.5h"] += 1
            elif time_diff < 1.0:
                time_diff_counts["0.5~1h"] += 1
            elif time_diff < 1.5:
                time_diff_counts["1~1.5h"] += 1
            elif time_diff < 3.0:
                time_diff_counts["1.5~3h"] += 1
            else:
                time_diff_counts[">3h"] += 1
        
        # 如果是SST产品，处理收集的差异数据
        if product == 'sst' and difference_counts['differences']:
            min_diff = difference_counts['min_diff']
            max_diff = difference_counts['max_diff']
            
            # 创建5个均匀的区间
            interval = (max_diff - min_diff) / 5
            new_counts = {
                f"{min_diff:.1f}~{min_diff+interval:.1f}": 0,
                f"{min_diff+interval:.1f}~{min_diff+2*interval:.1f}": 0,
                f"{min_diff+2*interval:.1f}~{min_diff+3*interval:.1f}": 0,
                f"{min_diff+3*interval:.1f}~{min_diff+4*interval:.1f}": 0,
                f"{min_diff+4*interval:.1f}~{max_diff:.1f}": 0
            }
            
            # 统计每个区间的数量
            for diff in difference_counts['differences']:
                for i, (key, _) in enumerate(new_counts.items()):
                    lower = min_diff + i * interval
                    upper = min_diff + (i + 1) * interval if i < 4 else max_diff + 0.1
                    if lower <= diff < upper:
                        new_counts[key] += 1
                        break
            
            difference_counts = new_counts
        
        # 从第一个验证结果文件名中获取卫星类型
        satellite_type = 'UNKNOWN'
        if valresults and len(valresults) > 0:
            filename = valresults[0].get('filename', '')
            satellite_type = extract_satellite_type(filename)
        
        # 返回卫星类型作为新的返回值
        return total_pixels, valid_pixels, time_diff_counts, difference_counts, satellite_type


    def analyze_ground_validation(valresults, spaceresults):
        """分析星地检验结果"""
        valid_images = len(valresults)
        
        time_diff_counts = {
            "<0.5h": 0,
            "0.5~1h": 0,
            "1~1.5h": 0,
            "1.5~3h": 0,
            ">3h": 0
        }
        
        valid_ratio_counts = {
            "=1": 0,
            "0.9~1": 0,
            "0.8~0.9": 0,
            "0.6~0.8": 0,
            "<0.6": 0
        }
        
        cv_value_counts = {
            "<0.05": 0,
            "0.05~0.1": 0,
            ">0.1": 0
        }
        
        # 从valresults中获取产品名称
        product = None
        if valresults and len(valresults) > 0:
            filename = valresults[0].get('filename', '')
            parts = filename.split('_')
            if len(parts) >= 4:
                product = parts[3].split('.')[0]
        
        # 根据产品类型初始化difference_counts
        if product == 'sst':
            difference_counts = {
                'min_diff': float('inf'),
                'max_diff': float('-inf'),
                'differences': []
            }
        else:
            difference_counts = {
                "<10": 0,
                "10~30": 0,
                "30~50": 0,
                "50~100": 0,
                ">100": 0
            }
        
        for result in valresults:
            for row in result['data']:
                try:
                    diff = float(row[-1])
                    if product == 'sst':
                        difference_counts['min_diff'] = min(difference_counts['min_diff'], diff)
                        difference_counts['max_diff'] = max(difference_counts['max_diff'], diff)
                        difference_counts['differences'].append(diff)
                    else:
                        if diff < 10:
                            difference_counts["<10"] += 1
                        elif diff < 30:
                            difference_counts["10~30"] += 1
                        elif diff < 50:
                            difference_counts["30~50"] += 1
                        elif diff < 100:
                            difference_counts["50~100"] += 1
                        else:
                            difference_counts[">100"] += 1
                except (ValueError, IndexError):
                    continue
        
        # 如果是SST产品，处理收集的差异数据
        if product == 'sst' and difference_counts['differences']:
            min_diff = difference_counts['min_diff']
            max_diff = difference_counts['max_diff']
            
            # 创建5个均匀的区间
            interval = (max_diff - min_diff) / 5
            new_counts = {
                f"{min_diff:.1f}~{min_diff+interval:.1f}": 0,
                f"{min_diff+interval:.1f}~{min_diff+2*interval:.1f}": 0,
                f"{min_diff+2*interval:.1f}~{min_diff+3*interval:.1f}": 0,
                f"{min_diff+3*interval:.1f}~{min_diff+4*interval:.1f}": 0,
                f"{min_diff+4*interval:.1f}~{max_diff:.1f}": 0
            }
            
            # 统计每个区间的数量
            for diff in difference_counts['differences']:
                for i, (key, _) in enumerate(new_counts.items()):
                    lower = min_diff + i * interval
                    upper = min_diff + (i + 1) * interval if i < 4 else max_diff + 0.1
                    if lower <= diff < upper:
                        new_counts[key] += 1
                        break
            
            difference_counts = new_counts
        
        return valid_images, time_diff_counts, valid_ratio_counts, cv_value_counts, difference_counts

    def generate_satellite_statistics_file(filename, total_pixels, valid_pixels, 
                                        time_diff_counts, difference_counts, product):
        """生成卫星交叉验证统计文件"""
        product_names = {
            'AOT': '气溶胶光学厚度',
            'chl': '叶绿素浓度',
            'Kd': '漫衰减系数',
            'sst': '海表温度',
            'Rrs412': '412nm遥感反射率',
            'Rrs443': '443nm遥感反射率',
            'Rrs490': '490nm遥感反射率',
            'Rrs520': '520nm遥感反射率',
            'Rrs565': '565nm遥感反射率',
            'Rrs670': '670nm遥感反射率'
        }
        product_name = product_names.get(product, product)
        
        print(f"\n=== 正在生成{product_name}统计文件 ===")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"{product_name}统计结果：\n")
                f.write(f"总像元数：{total_pixels}\t有效检验像元数：{valid_pixels}\n\n")
                
                f.write("时间差分布情况：\n")
                for key, value in time_diff_counts.items():
                    f.write(f"{key}:{value}\n")
                f.write("\n")
                
                f.write("检验结果情况：\n")
                for key, value in difference_counts.items():
                    f.write(f"{key}：{value}\n")
            
            print(f"{product_name}统计文件生成成功")
        except Exception as e:
            print(f"生成统计文件时出错: {str(e)}")

    def generate_ground_statistics_file(filename, valid_images, time_diff_counts, 
                                      valid_ratio_counts, cv_value_counts, 
                                      difference_counts, product):
        """生成现场验证统计文件"""
        product_names = {
            'AOT': '气溶胶光学厚度',
            'chl': '叶绿素浓度',
            'Kd': '漫衰减系数',
            'sst': '海表温度',
            'Rrs412': '412nm遥感反射率',
            'Rrs443': '443nm遥感反射率',
            'Rrs490': '490nm遥感反射率',
            'Rrs520': '520nm遥感反射率',
            'Rrs565': '565nm遥感反射率',
            'Rrs670': '670nm遥感反射率'
        }
        product_name = product_names.get(product, product)
        
        print(f"\n=== 正在生成{product_name}现场验证统计文件: {filename} ===")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"{product_name}现场验证统计结果：\n")
                f.write(f"有效检验影像数：{valid_images}\n\n")
                
                f.write("时间差分布情况：\n")
                for key, value in time_diff_counts.items():
                    f.write(f"{key}:{value}\n")
                f.write("\n")
                
                f.write("空间窗口内有效像元比例分布情况：\n")
                for key, value in valid_ratio_counts.items():
                    f.write(f"{key}:{value}\n")
                f.write("\n")
                
                f.write("空间窗口内CV值分布情况：\n")
                for key, value in cv_value_counts.items():
                    f.write(f"{key}:{value}\n")
                f.write("\n")
                
                f.write("检验结果情况：\n")
                for key, value in difference_counts.items():
                    f.write(f"{key}%：{value}\n")
            
            print(f"{product_name}现场验证统计文件生成成功")
        except Exception as e:
            print(f"生成统计文件时出错: {str(e)}")

    def generate_satellite_plots(valid_pixels, total_pixels, time_diff_counts, 
                            difference_counts, output_directory, product, satellite_type, timestamp=None):
        """生成卫星交叉验证统计图"""
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        product_names = {
            'AOT': '气溶胶光学厚度',
            'chl': '叶绿素浓度',
            'Kd': '漫衰减系数',
            'sst': '海表温度',
            'Rrs412': '412nm遥感反射率',
            'Rrs443': '443nm遥感反射率',
            'Rrs490': '490nm遥感反射率',
            'Rrs520': '520nm遥感反射率',
            'Rrs565': '565nm遥感反射率',
            'Rrs670': '670nm遥感反射率'
        }
        product_name = product_names.get(product, product)

        if timestamp is None:
            timestamp = get_timestamp()
        base_name = f"HY3A_{satellite_type}_{product}_{timestamp}"
        
        # 1. 有效检验像元比例饼图
        plt.figure(figsize=(10, 8))
        # print(f"total_pixels: {total_pixels}")
        # print(f"valid_pixels: {valid_pixels}")
        
        invalid_pixels = max(0, total_pixels - valid_pixels)
        valid_pixels = max(0, valid_pixels)
        
        if total_pixels > 0:
            sizes = [valid_pixels, invalid_pixels]
            labels = ['有效检验像元数', '无效像元数']
            plt.pie(sizes, labels=labels, autopct='%1.1f%%')
            plt.title(f"{product_name}有效检验像元比例")
            pixel_output = os.path.join(output_directory, f"pixelstastic_{base_name}.jpg")
            plt.savefig(pixel_output)
            plt.close()
            print(f"生成卫星 {product} 有效像元比例图")
        else:
            print(f"警告: {product} 没有有效的像元数据")
            plt.close()
        
        # 2. 时间差分布饼图
        if any(time_diff_counts.values()):
            plt.figure(figsize=(10, 8))
            sizes = list(time_diff_counts.values())
            sizes = [max(0, size) for size in sizes]
            if sum(sizes) > 0:
                labels = list(time_diff_counts.keys())
                plt.pie(sizes, labels=labels, autopct='%1.1f%%')
                plt.title(f"{product_name}时间差分布情况")
                time_output = os.path.join(output_directory, f"timestastic_{base_name}.jpg")
                plt.savefig(time_output)
                plt.close()
                print(f"生成卫星 {product} 时间差分布图")
            else:
                print(f"警告: {product} 没有有效的时间差数据")
                plt.close()
        
        # 3. 检验结果分布饼图
        if any(difference_counts.values()):
            plt.figure(figsize=(10, 8))
            sizes = list(difference_counts.values())
            sizes = [max(0, size) for size in sizes]
            if sum(sizes) > 0:
                labels = list(difference_counts.keys())
                plt.pie(sizes, labels=labels, autopct='%1.1f%%')
                plt.title(f"{product_name}检验结果情况")
                val_output = os.path.join(output_directory, f"valstastic_{base_name}.jpg")
                plt.savefig(val_output)
                plt.close()
                print(f"生成卫星 {product} 检验结果分布图")
            else:
                print(f"警告: {product} 没有有效的检验结果数据")
                plt.close()

    def generate_ground_plots(time_diff_counts, valid_ratio_counts, cv_value_counts, 
                         difference_counts, output_directory, product, timestamp=None):
        """生成现场验证统计图"""
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        product_names = {
            'AOT': '气溶胶光学厚度',
            'chl': '叶绿素浓度',
            'Kd': '漫衰减系数',
            'sst': '海表温度',
            'Rrs412': '412nm遥感反射率',
            'Rrs443': '443nm遥感反射率',
            'Rrs490': '490nm遥感反射率',
            'Rrs520': '520nm遥感反射率',
            'Rrs565': '565nm遥感反射率',
            'Rrs670': '670nm遥感反射率'
        }
        product_name = product_names.get(product, product)

        if timestamp is None:
            timestamp = get_timestamp()

        base_name = f"HY3A_XC_{product}_{timestamp}"

        # 1. 时间差分布饼图
        if any(time_diff_counts.values()):
            plt.figure(figsize=(10, 8))
            sizes = list(time_diff_counts.values())
            labels = list(time_diff_counts.keys())
            plt.pie(sizes, labels=labels, autopct='%1.1f%%')
            plt.title(f"{product_name}时间差分布情况")
            time_output = os.path.join(output_directory, f"timestastic_{base_name}.jpg")
            plt.savefig(time_output)
            plt.close()
            print(f"生成现场 {product} 时间差分布图")
        
        # 2. 有效像元比例分布饼图
        if any(valid_ratio_counts.values()):
            plt.figure(figsize=(10, 8))
            sizes = list(valid_ratio_counts.values())
            labels = list(valid_ratio_counts.keys())
            plt.pie(sizes, labels=labels, autopct='%1.1f%%')
            plt.title(f"{product_name}空间窗口内有效像元比例")
            ratio_output = os.path.join(output_directory, f"ratiostastic_{base_name}.jpg")
            plt.savefig(ratio_output)
            plt.close()
            print(f"生成现场 {product} 有效像元比例图")
        
        # 3. CV值分布饼图
        if any(cv_value_counts.values()):
            plt.figure(figsize=(10, 8))
            sizes = list(cv_value_counts.values())
            labels = list(cv_value_counts.keys())
            plt.pie(sizes, labels=labels, autopct='%1.1f%%')
            plt.title(f"{product_name}空间窗口内CV值分布")
            cv_output = os.path.join(output_directory, f"CVstastic_{base_name}.jpg")
            plt.savefig(cv_output)
            plt.close()
            print(f"生成现场 {product} CV值分布图")
        
        # 4. 检验结果分布饼图
        if any(difference_counts.values()):
            plt.figure(figsize=(10, 8))
            sizes = list(difference_counts.values())
            labels = list(difference_counts.keys())
            plt.pie(sizes, labels=labels, autopct='%1.1f%%')
            plt.title(f"{product_name}检验结果情况")
            val_output = os.path.join(output_directory, f"valstastic_{base_name}.jpg")
            plt.savefig(val_output)
            plt.close()
            print(f"生成现场 {product} 检验结果分布图")




    try:
        # print("\n=== 开始处理数据 ===")
        
        # 分别存储卫星数据和现场数据
        satellite_data = {}  # 卫星数据
        insitu_data = {}    # 现场数据
        
        # 读取并分类所有文件
        for filename in os.listdir(input_directory):
            file_path = os.path.join(input_directory, filename)
            
            if filename.startswith('valresult_') or filename.startswith('spaceresult_'):
                parts = filename.split('_')
                if len(parts) >= 4:
                    # 判断是卫星数据还是现场数据
                    if 'XC' in filename:  # 现场数据
                        product = parts[3].split('.')[0]
                        if product not in insitu_data:
                            insitu_data[product] = {
                                'valresults': [],
                                'spaceresults': []
                            }
                        
                        if filename.startswith('valresult_'):
                            result = read_valresult_file(file_path)
                            if result:
                                insitu_data[product]['valresults'].append(result)
                        elif filename.startswith('spaceresult_'):
                            result = read_spaceresult_file(file_path)
                            if result:
                                insitu_data[product]['spaceresults'].append(result)
                    
                    else:  # 卫星数据
                        product = parts[3].split('.')[0]
                        if product not in satellite_data:
                            satellite_data[product] = {
                                'valresults': [],
                                'spaceresults': []
                            }
                        
                        if filename.startswith('valresult_'):
                            result = read_valresult_file(file_path)
                            if result:
                                satellite_data[product]['valresults'].append(result)
                        elif filename.startswith('spaceresult_'):
                            result = read_spaceresult_file(file_path)
                            if result:
                                satellite_data[product]['spaceresults'].append(result)

        # 获取时间戳
        timestamp = extract_timestamp_from_files(os.listdir(input_directory))
                                
        # 处理卫星数据
        print("\n处理卫星交叉验证数据...")
        for product, data in satellite_data.items():
            if data['valresults']:
                total_pixels, valid_pixels, time_diff_counts, difference_counts, satellite_type = analyze_star_check(
                    data['valresults'], data['spaceresults'], input_directory)
                
                # 生成统计文件
                stats_filename = os.path.join(output_directory, 
                    f"resstastic_HY3A_{satellite_type}_{product}_{timestamp}.txt")
                generate_satellite_statistics_file(
                    stats_filename,
                    total_pixels,
                    valid_pixels,
                    time_diff_counts,
                    difference_counts,
                    product
                )
                
                # 生成统计图
                generate_satellite_plots(
                    valid_pixels,
                    total_pixels,
                    time_diff_counts,
                    difference_counts,
                    output_directory,
                    product,
                    satellite_type,
                    timestamp
                )
        
        # 处理现场数据
        print("\n处理现场验证数据...")
        for product, data in insitu_data.items():
            if data['valresults']:
                # print(f"\n处理现场 {product} 产品数据...")
                valid_images, time_diff_counts, valid_ratio_counts, cv_value_counts, difference_counts = analyze_ground_validation(
                    data['valresults'], data['spaceresults'])
                
                # 生成统计文件
                stats_filename = os.path.join(output_directory, 
                    f"stastic_HY3A_XC_{product}_{timestamp}.txt")
                generate_ground_statistics_file(
                    stats_filename,
                    valid_images,
                    time_diff_counts,
                    valid_ratio_counts,
                    cv_value_counts,
                    difference_counts,
                    product
                )
                
                # 生成统计图
                generate_ground_plots(
                    time_diff_counts,
                    valid_ratio_counts,
                    cv_value_counts,
                    difference_counts,
                    output_directory,
                    product,
                    timestamp
                )
        
        return True
    except Exception as e:
        print(f"步骤9执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
def main():
    input_directory = r'C:\Users\H\Desktop\new_HY_check\code_12_11\moduel\test'
    output_directory = r'C:\Users\H\Desktop\new_HY_check\output'
    step9(input_directory, input_directory)

if __name__ == '__main__':
    main()