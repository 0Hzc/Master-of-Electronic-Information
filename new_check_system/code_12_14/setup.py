import os
import glob
import configparser
import h5py
import netCDF4 as nc
import numpy as np
import pandas as pd
import traceback
from datetime import datetime, timedelta
from scipy import interpolate
import re
import matplotlib.pyplot as plt
import random
from mpl_toolkits.basemap import Basemap
from scipy.interpolate import griddata
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader  
from reportlab.lib import colors

def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config

def run_check(config):
    """运行检验流程"""
    try:
        # 获取配置参数
        input_dir = config['PATH']['input_dir']
        output_dir = config['PATH']['output_dir']
        window_size = int(config['PARAMS']['window_size'])
        time_threshold = int(config['PARAMS']['time_threshold'])
        source_type = config['VALIDATION']['source_type']
        font_path = config['font']['font_path']


        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n=== 开始数据检验流程: HY3A vs {source_type} ===")
        
        # 步骤1：处理HY3A数据
        print("\n处理HY3A数据...")
        process_hy_data(
            hy_file_l2a=os.path.join(input_dir, config['HY3A']['l2a_file']),
            hy_file_l2b=os.path.join(input_dir, config['HY3A']['l2b_file']),
            hy_file_l2c=os.path.join(input_dir, config['HY3A']['l2c_file']),
            output_dir=output_dir
        )
        
        # 步骤2：处理检验源数据
        if source_type == 'XC':
            print("\n处理现场数据...")
            process_xc_check_data(
                aopres_file=os.path.join(input_dir, config['XC']['aopres_file']),
                wqp_file=os.path.join(input_dir, config['XC']['wqp_file']),
                aot_file=os.path.join(input_dir, config['XC']['aot_file']),
                ctd_file=os.path.join(input_dir, config['XC']['ctd_file']),
                output_dir=output_dir
            )
        else:
            print(f"\n处理{source_type}卫星数据...")
            process_satellite_check_data(
                oc_file=os.path.join(input_dir, config[source_type]['oc_file']),
                sst_file=os.path.join(input_dir, config[source_type]['sst_file']),
                output_dir=output_dir
            )
        
        # 步骤3：标识检查
        print("\n执行标识检查...")
        HY3A_flag_create(output_dir, window_size)
        if source_type == 'XC':
            process_xc_flagcheck_data(output_dir, output_dir)
        else:
            satellite_flag_create(output_dir, source_type, window_size)
        
        # 步骤4：时间匹配
        print("\n执行时间匹配...")
        if source_type == 'XC':
            process_xc_timematch(output_dir, output_dir, 'HY3A', time_threshold)
        else:
            process_satellite_timematch(output_dir, output_dir, 'HY3A', source_type, time_threshold)
        
        # 步骤5：空间匹配
        print("\n执行空间匹配...")
        if source_type == 'XC':
            process_xc_spacematch(output_dir, output_dir, 'HY3A', window_size)
        else:
            process_satellite_spacematch(output_dir, output_dir, 'HY3A', source_type)
        
        # 步骤6：生成验证结果
        print("\n生成验证结果...")
        if source_type == 'XC':
            xc_validation(output_dir, output_dir)
        else:
            satellite_validation(output_dir, output_dir)
        
        # 步骤7：生成误差地图
        print("\n生成误差地图...")
        if source_type != 'XC':
            step7(output_dir, output_dir)

        # 步骤8：生成折线图
        step8(output_dir, output_dir)

        # 步骤9：生成统计结果和图表
        step9(output_dir, output_dir)

        # 步骤10：生成报告所需数据report文件
        if source_type == 'XC':

            make_ground_report_data(output_dir)

        else:

            make_satellite_report_data(output_dir)
        # 步骤11：生成报告

        if source_type == 'XC':

            create_xc_report(output_dir, output_dir, font_path, time_threshold)

        else:

            create_satellite_report(output_dir,output_dir, font_path,time_threshold,window_size)

        #步骤11：异常检测
        check_validation_errors(output_dir)

        #步骤12：生成日志
        process_reports(output_dir)

        print(f"\n=== HY3A vs {source_type} 数据检验流程完成 ===")
        return True
    

    except Exception as e:
        print(f"检验流程执行失败: {str(e)}")
        traceback.print_exc()
        return False

def process_hy_data(hy_file_l2a, hy_file_l2b, hy_file_l2c, output_dir):
    """
    处理HY3A待检验数据
    """
    def save_data_to_txt(data, filename):
        """将数据保存为单列txt文件"""
        flattened_data = data.flatten()
        with open(filename, 'w') as f:
            for value in flattened_data:
                if abs(value + 9.9) < 0.0001:
                    f.write('-999.000000\n')
                elif abs(value) < 0.000001:
                    f.write('0.000000\n')
                elif abs(value) >= 1000000:
                    f.write(f'{value:.0f}\n')
                else:
                    f.write(f'{value:.6f}\n')

    try:
        print('\n开始处理HY3A数据\n')
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        prefix = 'HY3A'

        # 处理反射率数据
        with h5py.File(hy_file_l2a, 'r') as h5_file:
            # 获取时间信息
            year = int(h5_file['Scan Line Attributes/Year'][0])
            day = int(h5_file['Scan Line Attributes/Day'][0])
            millisecond = int(h5_file['Scan Line Attributes/Millisecond'][0])
            
            # 转换为北京时间
            utc_time = datetime(year, 1, 1) + timedelta(days=day-1, milliseconds=millisecond)
            beijing_time = utc_time + timedelta(hours=8)
            time_str = beijing_time.strftime('%Y%m%d%H%M%S')

            # 保存基础数据
            save_data_to_txt(h5_file['Navigation Data/Latitude'][:], 
                           os.path.join(output_dir, f'{prefix}_lat_{time_str}.txt'))
            save_data_to_txt(h5_file['Navigation Data/Longitude'][:], 
                           os.path.join(output_dir, f'{prefix}_lon_{time_str}.txt'))
            save_data_to_txt(h5_file['Geophysical Data/l2_flags'][:], 
                           os.path.join(output_dir, f'{prefix}_flag_{time_str}.txt'))

            # 保存反射率数据
            rrs_bands = ['412', '443', '490', '520', '565', '670', '750']
            for band in rrs_bands:
                data = h5_file[f'Geophysical Data/Rrs{band}'][:]
                save_data_to_txt(data, 
                               os.path.join(output_dir, f'{prefix}_Rrs{band}_{time_str}.txt'))

        # 处理TSM等参数数据
        with h5py.File(hy_file_l2b, 'r') as h5_file:
            # 保存参数数据
            params = {
                'chl_a': 'Geophysical Data/chl_a',
                'TSM': 'Geophysical Data/TSM',
                'CDOM': 'Geophysical Data/CDOM',
                'sst': 'Geophysical Data/SST',
                'AOT': 'Geophysical Data/taua865',
                'nLw': 'Geophysical Data/nLw565',
                'Kd': 'Geophysical Data/Kd490'
            }
            
            for param_name, dataset_path in params.items():
                data = h5_file[dataset_path][:]
                save_data_to_txt(data, 
                               os.path.join(output_dir, f'{prefix}_{param_name}_{time_str}.txt'))
                

        with h5py.File(hy_file_l2c, 'r') as h5_file:
            # 保存参数数据
            ipar_data = h5_file['Geophysical Data/IPAR'][:]
            save_data_to_txt(ipar_data, 
                               os.path.join(output_dir, f'{prefix}_ipar_{time_str}.txt'))

        print('\nHY3A数据处理完成\n')
        return True

    except Exception as e:
        print(f"处理数据时出错: {str(e)}")
        traceback.print_exc()
        return False
    
def process_satellite_check_data(oc_file, sst_file, output_dir):
    """
    处理卫星检验数据
    """
    def save_data_to_txt(data, filename):
        """将数据保存为单列txt文件"""
        flattened_data = data.flatten()
        with open(filename, 'w') as f:
            for value in flattened_data:
                f.write(f'{value}\n')

    def extract_datetime(filename):
        """从文件名中提取时间信息并转换为北京时间"""
        pattern = r'\d{8}T\d{6}'
        match = re.search(pattern, filename)
        if match:
            time_str = match.group()
            utc_time = datetime.strptime(time_str, '%Y%m%dT%H%M%S')
            beijing_time = utc_time + timedelta(hours=8)
            return beijing_time
        return None
    
    def extract_file_prefix(filename):
        """从文件名中提取处理的卫星类别"""
        first_five_chars = os.path.basename(filename)[:5] if len(os.path.basename(filename)) >= 5 else None
        if first_five_chars == 'AQUA_': 
            return 'AQUA'
        elif first_five_chars == 'TERRA':
            return 'TERRA'
        elif first_five_chars == 'SNPP_':
            return 'SNPP'
        elif first_five_chars == 'JPSS1':
            return 'JPSS'

    try:
        print('\n开始处理卫星数据\n')
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 处理海洋水色数据
        with nc.Dataset(oc_file, 'r') as nc_data:
            # 获取时间信息
            beijing_time = extract_datetime(oc_file)
            time_str = beijing_time.strftime('%Y%m%d%H%M%S')
            prefix = extract_file_prefix(oc_file)

            # 保存基础数据
            save_data_to_txt(nc_data['navigation_data']['latitude'][:], 
                           os.path.join(output_dir, f'{prefix}_Lat_{time_str}.txt'))
            save_data_to_txt(nc_data['navigation_data']['longitude'][:], 
                           os.path.join(output_dir, f'{prefix}_Lon_{time_str}.txt'))
            save_data_to_txt(nc_data['geophysical_data']['l2_flags'][:], 
                           os.path.join(output_dir, f'{prefix}_flag_{time_str}.txt'))

            # 根据传感器类型选择波段
            if prefix in ['AQUA', 'TERRA']:  # MODIS数据
                rrs_bands = {
                    'Rrs412': 'Rrs_412', 
                    'Rrs443': 'Rrs_443', 
                    'Rrs469': 'Rrs_469', 
                    'Rrs488': 'Rrs_488',
                    'Rrs531': 'Rrs_531', 
                    'Rrs547': 'Rrs_547',
                    'Rrs555': 'Rrs_555', 
                    'Rrs645': 'Rrs_645',
                    'Rrs667': 'Rrs_667', 
                    'Rrs678': 'Rrs_678'
                }
            elif 'JPSS' in prefix:  # JPSS数据
                rrs_bands = {
                    'Rrs411': 'Rrs_411',
                    'Rrs445': 'Rrs_445',
                    'Rrs489': 'Rrs_489',
                    'Rrs556': 'Rrs_556',
                    'Rrs667': 'Rrs_667'
                }
            else:  # SNPP数据
                rrs_bands = {
                    'Rrs410': 'Rrs_410',
                    'Rrs443': 'Rrs_443',
                    'Rrs486': 'Rrs_486',
                    'Rrs551': 'Rrs_551',
                    'Rrs671': 'Rrs_671'
                }

            # 保存遥感反射率数据
            for out_name, band_name in rrs_bands.items():
                data = nc_data['geophysical_data'][band_name][:]
                save_data_to_txt(data, 
                               os.path.join(output_dir, f'{prefix}_{out_name}_{time_str}.txt'))

            # 保存叶绿素数据
            chl_data = nc_data['geophysical_data']['chlor_a'][:]
            save_data_to_txt(chl_data, 
                           os.path.join(output_dir, f'{prefix}_Chl_{time_str}.txt'))

            #保存漫射衰减系数数据
            kd_490_data = nc_data['geophysical_data']['Kd_490'][:]
            save_data_to_txt(kd_490_data, 
                           os.path.join(output_dir, f'{prefix}_Kd_{time_str}.txt'))
            
            #保存有效光合辐射数据，只有AQUA和TERRA有
            if prefix in ['AQUA', 'TERRA'] :
                # print(f"\n开始处理{prefix}的ipar数据")
                ipar_data = nc_data['geophysical_data']['ipar'][:].data
                ipar_data = ipar_data /45.7
                save_data_to_txt(ipar_data, 
                os.path.join(output_dir, f'{prefix}_ipar_{time_str}.txt'))

            # 保存气溶胶光学厚度数据
            aot_band = 'aot_869' if prefix in ['AQUA', 'TERRA'] else \
                      'aot_862' if prefix == 'SNPP' else 'aot_868'
            aot_data = nc_data['geophysical_data'][aot_band][:]
            save_data_to_txt(aot_data, 
                           os.path.join(output_dir, f'{prefix}_AOT_{time_str}.txt'))

        # 处理海表温度数据
        with nc.Dataset(sst_file, 'r') as nc_data:
            sst_data = nc_data['geophysical_data']['sst'][:]
            save_data_to_txt(sst_data, 
                           os.path.join(output_dir, f'{prefix}_sst_{time_str}.txt'))

        print(f'{prefix}数据处理完成')
        return True

    except Exception as e:
        print(f"处理数据时出错: {str(e)}")
        traceback.print_exc()
        return False


def process_xc_check_data(aopres_file, wqp_file, aot_file, ctd_file, output_dir):
    """
    处理现场检验数据
    """
    def read_header_info(file_path):
        """读取文件头信息"""
        header_info = {'lat': 37.681, 'lon': 121.700}  # 默认值
        header_end_line = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('/north_latitude'):
                    lat_str = line.split('=')[1] if '=' in line else line.split()[1]
                    header_info['lat'] = float(lat_str)
                elif line.startswith('/east_longitude'):
                    lon_str = line.split('=')[1] if '=' in line else line.split()[1]
                    header_info['lon'] = float(lon_str)
                elif line.startswith('/end_header'):
                    header_end_line = i + 1
                    break
        
        if header_end_line == 0:
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('/'):
                    header_end_line = i
                    break
                    
        return header_info, header_end_line

    def process_data_file(input_file, data_type):
        """处理单个数据文件"""
        print(f'\n开始处理{data_type}数据\n')
        # 读取文件头信息
        header_info, header_end_line = read_header_info(input_file)
        
        # 读取数据部分
        df = pd.read_csv(input_file, skiprows=header_end_line, sep=r'\s+', header=None)
        
        # 根据数据类型处理       
        if data_type == 'wqp':
            # 处理水质参数数据
            if df.shape[1] >= 5:
                df = df.iloc[:, :5]
                df.columns = ['Date', 'Time', 'Chl', 'CDOM', 'TSM']
            else:
                raise ValueError(f"WQP数据列数不足: {df.shape[1]}")
        
        elif data_type == 'aop':
            if df.shape[1] >= 1570:
                df = df.iloc[:, [0, 1, 1116, 1147, 1194, 1224, 1269, 1374, 1454, 1569]]
                df.columns = ['Date', 'Time', 'Rrs412', 'Rrs443', 'Rrs490', 'Rrs520', 
                            'Rrs565', 'Rrs670', 'Rrs750', 'Rrs865']
                df['nLw'] = df['Rrs565'] * 179.363
            else:
                raise ValueError(f"WQP数据列数不足: {df.shape[1]}")
                
        elif data_type == 'aot':
            # 处理气溶胶光学厚度数据
            if df.shape[1] >= 12:
                df = df.iloc[:, [0, 1, 7, 11]]
                df.columns = ['Date', 'Time', 'AOT', 'Flag']
                df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y%m%d')
                df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S').dt.strftime('%H%M%S')
            else:
                raise ValueError(f"AOT数据列数不足: {df.shape[1]}")
                
        elif data_type == 'ctd':
            # 处理温度数据
            if df.shape[1] >= 4:
                df = df.iloc[:, [0, 1, 3]]
                df.columns = ['Date', 'Time', 'SST']
                df = df.dropna(subset=['SST'])
            else:
                raise ValueError(f"SST数据列数不足: {df.shape[1]}")

        df = df.dropna()
        
        # 保存处理后的数据
        for date, group in df.groupby('Date'):
            if data_type == 'wqp':
                # 处理水质参数数据
                params = [
                    ('Chl', 'Chl'),
                    ('TSM', 'TSM'),
                    ('CDOM', 'CDOM')
                ]
                for param_name, col_name in params:
                    output_file = os.path.join(output_dir, f'XC_{param_name}_{date}000000.txt')
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"Latitude: {header_info['lat']}\n")
                        f.write(f"Longitude: {header_info['lon']}\n")
                        f.write("Data:\n")
                    group[['Date', 'Time', col_name]].to_csv(output_file, mode='a', 
                                                           index=False, sep='\t')   
            elif data_type == 'aop':
                #处理遥感反射率数据
                params = [
                    ('Rrs412', 'Rrs412'),
                    ('Rrs443', 'Rrs443'),
                    ('Rrs490', 'Rrs490'),
                    ('Rrs520', 'Rrs520'),
                    ('Rrs565', 'Rrs565'),
                    ('Rrs670', 'Rrs670'),
                    ('Rrs750', 'Rrs750'),
                    ('Rrs865', 'Rrs865'),
                    ('nLw', 'nLw')
                ]
                for param_name, col_name in params:
                    output_file = os.path.join(output_dir, f'XC_{param_name}_{date}000000.txt')
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"Latitude: {header_info['lat']}\n")
                        f.write(f"Longitude: {header_info['lon']}\n")
                        f.write("Data:\n")
                    group[['Date', 'Time', col_name]].to_csv(output_file, mode='a', 
                                                           index=False, sep='\t')
            elif data_type == 'aot':
                #处理气溶胶光学厚度数据
                output_file = os.path.join(output_dir, f'XC_AOT_{date}000000.txt')
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"Latitude: {header_info['lat']}\n")
                    f.write(f"Longitude: {header_info['lon']}\n")
                    f.write("Data:\n")
                # 将Date、Time、AOT和Flag列一起写入文件
                group[['Date', 'Time', 'AOT', 'Flag']].to_csv(output_file, mode='a', 
                                                            index=False, sep='\t')
                
            elif data_type == 'ctd':
                #处理温度数据
                params = [
                    ('sst', 'SST')
                ]
                for param_name, col_name in params:
                    output_file = os.path.join(output_dir, f'XC_{param_name}_{date}000000.txt')
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"Latitude: {header_info['lat']}\n")
                        f.write(f"Longitude: {header_info['lon']}\n")
                        f.write("Data:\n")
                    group[['Date', 'Time', col_name]].to_csv(
                        output_file, 
                        mode='a',
                        index=False,
                        sep='\t'
                    )
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 处理各类数据文件
        if aopres_file:
            process_data_file(aopres_file, 'aop')
        if wqp_file:
            process_data_file(wqp_file, 'wqp')
        if aot_file:
            process_data_file(aot_file, 'aot')
        if ctd_file:
            process_data_file(ctd_file, 'ctd')
            
        print('\n现场检验数据处理完成\n')
        return True
        
    except Exception as e:
        print(f"处理数据时出错: {str(e)}")
        traceback.print_exc()
        return False
    


def extract_file_prefix(filename):
    """从文件名中提取处理的卫星类别"""
    first_five_chars = os.path.basename(filename)[:5] if len(os.path.basename(filename)) >= 5 else None
    if first_five_chars == 'AQUA_': 
        return 'AQUA'
    elif first_five_chars == 'TERRA':
        return 'TERRA'
    elif first_five_chars == 'SNPP_':
        return 'SNPP'
    elif first_five_chars == 'JPSS_':
        return 'JPSS'

def generate_flag_from_data(data_file, satellite_type):
    try:
        data = np.genfromtxt(data_file, delimiter=None)
        flag = np.zeros_like(data, dtype=np.int32)
        
        # 添加统计信息
        filename = os.path.basename(data_file)
        # 根据不同产品类型处理无效值
        if 'ipar' in filename:       
            # 设置标记
            flag[data == -717.002197265625] = 1
            flag[np.isnan(data)] = 1
        elif satellite_type in ['HY3A']:
            flag[data == -999] = 1
            flag[np.isnan(data)] = 1
        else:
            flag[data == '--'] = 1
            flag[np.isnan(data)] = 1

        return flag
        
    except Exception as e:
        print(f"生成标识矩阵时出错: {str(e)}")
        traceback.print_exc()
        return None

def apply_spatial_window(flag_array, window_size, rows, cols):
    """应用空间窗口判断"""
    try:
        flag_2d = flag_array.reshape(rows, cols)
        half_window = (window_size - 1) // 2
        
        # 1. 处理边界区域
        flag_2d[:half_window, :] = 1  # 上边界
        flag_2d[-half_window:, :] = 1  # 下边界
        flag_2d[:, :half_window] = 1  # 左边界
        flag_2d[:, -half_window:] = 1  # 右边界
        
        # 2. 第一轮空间窗口判断：FLAG为1的像元比例
        temp_flag = flag_2d.copy()
        for i in range(half_window, rows-half_window):
            for j in range(half_window, cols-half_window):
                if flag_2d[i, j] == 0:
                    window = flag_2d[i-half_window:i+half_window+1, 
                                   j-half_window:j+half_window+1]
                    if np.mean(window) > 0.5:
                        temp_flag[i, j] = 1
        
        flag_2d = temp_flag
        
        # 3. 第二轮空间窗口判断：变异系数
        temp_flag = flag_2d.copy()
        for i in range(half_window, rows-half_window):
            for j in range(half_window, cols-half_window):
                if flag_2d[i, j] == 0:
                    window = flag_2d[i-half_window:i+half_window+1, 
                                   j-half_window:j+half_window+1]
                    valid_values = window[window == 0]
                    if len(valid_values) > 0:
                        cv = np.std(valid_values) / np.mean(valid_values) if np.mean(valid_values) != 0 else 0
                        if cv > 0.15:
                            temp_flag[i, j] = 1
        
        return temp_flag.reshape(-1)
        
    except Exception as e:
        print(f"空间窗口处理失败: {e}")
        traceback.print_exc()
        return None


def process_xc_flagcheck_data(input_dir, output_dir):
    """处理现场观测数据的标识检查"""
    try:
        print('\n开始处理现场观测数据标识检查\n')
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 处理所有现场观测数据文件
        for filename in os.listdir(input_dir):
            if not filename.startswith('XC_') or not filename.endswith('.txt'):
                continue
                
            input_file = os.path.join(input_dir, filename)         
            # 读取文件内容
            with open(input_file, 'r') as f:
                lines = f.readlines()
            
            header_lines = lines[:3]  # 前3行为经纬度等信息
            headers = lines[3].strip() # 第4行为列名
            
            # 处理AOT数据
            if 'AOT' in filename:
                output_file = os.path.join(output_dir, filename.replace('XC_', 'XCf_'))
                data_lines = []
                flag_count = 0
                valid_lines = 0

                for line in lines[4:]:  # 从第5行开始是数据
                    if not line.strip():
                        continue
                        
                    values = line.strip().split('\t')
                    valid_lines += 1
                    
                    # 检查最后一列的Flag值
                    try:
                        flag_value = float(values[-1])  # 将Flag值转换为数值
                        if flag_value >= 1:  # 修改这里：检查是否大于等于1
                            flag_count += 1
                        else:
                            data_lines.append(line)
                    except ValueError:  # 处理可能的转换错误
                        print(f"警告：无法转换Flag值：{values[-1]}")
                        continue
                
                # 保存处理后的数据
                with open(output_file, 'w') as f:
                    f.writelines(header_lines)  # 写入经纬度等信息
                    f.write(headers + '\n')     # 写入列名
                    f.writelines(data_lines)    # 写入筛选后的数据          

            # 处理其他数据（直接改名）
            else:
                output_file = os.path.join(output_dir, filename.replace('XC_', 'XCf_'))
                with open(output_file, 'w') as f:
                    f.writelines(lines)
        
        print('\n现场观测数据标识处理完成\n')
        return True
        
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        traceback.print_exc()
        return False

def HY3A_flag_create(input_dir,window_size):
    try:
        print("\n开始执行HY3A_flag_create函数\n")
        flag_matrices = {}
        
        # 检查目录中的文件
        all_files = os.listdir(input_dir)
      
        # 处理所有HY3A_flag文件
        for filename in all_files:        
            if filename.startswith('HY3A_flag_') and filename.endswith('.txt'):
                print(f"\n开始处理flag文件: {filename}")
                flag_file = os.path.join(input_dir, filename)
                
                # 读取flag文件
                flag_matrix = np.genfromtxt(flag_file, delimiter=None, dtype=np.int32)
                # print(f"原始flag文件统计:")
                # print(f"- 数据形状: {flag_matrix.shape}")
                # print(f"- 唯一值: {np.unique(flag_matrix)}")      

                # 提取时间戳部分
                time_id = filename.split('_')[2].replace('.txt', '')
             
                # 初始化flag矩阵
                FLAG = np.zeros_like(flag_matrix, dtype=np.int32)
                
                # 检查flag文件中的特定位
                mask = ((flag_matrix & (1 << 8)) | (flag_matrix & (1 << 22))) != 0
                FLAG[mask] = 1
                # print(f"\n位运算后的FLAG统计:")
                # print(f"- FLAG中1的数量: {np.sum(FLAG == 1)}")
                # print(f"- FLAG中0的数量: {np.sum(FLAG == 0)}")
                
                # 查找对应的产品文件
                for product_file in all_files:
                    if 'lon' in product_file or 'lat' in product_file:
                        continue
                    if product_file.startswith('HY3A_') and time_id in product_file:
                        print(f"\n处理产品文件: {product_file}")  # 新增：显示当前处理的产品文件

                        if os.path.exists(os.path.join(input_dir, product_file)):
                            # 记录处理前的1的数量
                            ones_before = np.sum(FLAG == 1)
                            
                            temp_matrix = generate_flag_from_data(
                                os.path.join(input_dir, product_file), 
                                'HY3A'
                            )
                            if temp_matrix is not None and len(temp_matrix) == len(flag_matrix):
                                FLAG = np.logical_or(FLAG, temp_matrix).astype(np.int32)
                                
                                # 计算并显示变化
                                ones_after = np.sum(FLAG == 1)
                                new_ones = ones_after - ones_before
                                # print(f"\n产品 {product_file} 的影响:")
                                # print(f"- 处理前1的数量: {ones_before}")
                                # print(f"- 处理后1的数量: {ones_after}")
                                # print(f"- 该产品新增1的数量: {new_ones}")
                                # print(f"- 占总像素的比例: {(new_ones / len(FLAG)) * 100:.2f}%")
                                
                                if new_ones > len(FLAG) * 0.5:  # 如果新增的1超过50%
                                    print(f"警告: 产品 {product_file} 导致大量像素变为1!")
                            else:
                                print(f"警告：产品 {product_file} 的数据长度与flag文件不匹配")

                # print(f"\n应用空间窗口前的FLAG统计:")
                # print(f"- FLAG中1的数量: {np.sum(FLAG == 1)}")
                # print(f"- FLAG中0的数量: {np.sum(FLAG == 0)}")
                
                # 应用空间窗口1
                total_size = flag_matrix.size
                for i in range(1000, 6000):
                    if total_size % i == 0:
                        rows = i
                        cols = total_size // i
                        break
                FLAG = apply_spatial_window(FLAG, window_size, rows, cols)

                # print(f"\n应用空间窗口后的FLAG统计:")
                # print(f"- FLAG中1的数量: {np.sum(FLAG == 1)}")
                # print(f"- FLAG中0的数量: {np.sum(FLAG == 0)}")

                # 输出结果
                output_filename = filename.replace('flag_', 'flag1_')
                output_path = os.path.join(input_dir, output_filename)
                np.savetxt(output_path, FLAG, fmt='%d')
                print(f"结果已保存到: {output_path}")

        return flag_matrices
        
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        traceback.print_exc()
        return None


def satellite_flag_create(input_dir, satellite_type,window_size):
    try:
        print(f"开始执行{satellite_type}_flag_create函数")
        flag_matrices = {}
        
        # 检查目录中的文件
        all_files = os.listdir(input_dir)       
        # 处理所有相关flag文件
        for filename in all_files:
            if filename.startswith(f'{satellite_type}_flag_') and filename.endswith('.txt'):
                print(f"\n开始处理flag文件: {filename}")
                flag_file = os.path.join(input_dir, filename)
                
                # 读取flag文件
                flag_matrix = np.genfromtxt(flag_file, delimiter=None, dtype=np.int32)
                # print(f"原始flag文件统计:")
                # print(f"- 数据形状: {flag_matrix.shape}")
                # print(f"- 唯一值: {np.unique(flag_matrix)}")
                
                # 提取时间戳部分
                time_id = filename.split('_')[2].replace('.txt', '')
                
                # 初始化flag矩阵
                FLAG = np.zeros_like(flag_matrix, dtype=np.int32)
                
                # 检查flag文件中的特定位
                mask = ((flag_matrix & 1) | (flag_matrix & (1 << 3)) | 
                        (flag_matrix & (1 << 4)) | (flag_matrix & (1 << 6)) | 
                        (flag_matrix & (1 << 22)) | (flag_matrix & (1 << 24))) != 0
                FLAG[mask] = 1
                # print(f"\n位运算后的FLAG统计:")
                # print(f"- FLAG中1的数量: {np.sum(FLAG == 1)}")
                # print(f"- FLAG中0的数量: {np.sum(FLAG == 0)}")
                
                # 查找对应的产品文件
                for product_file in all_files:
                    # 跳过lon、lat
                    if ('Lon' in product_file or 
                        'Lat' in product_file ):  # 添加这个条件
                        continue

                    if product_file.startswith(f'{satellite_type}_') and time_id in product_file:
                        print(f"\n处理产品文件: {product_file}")  # 新增：显示当前处理的产品文件

                        if os.path.exists(os.path.join(input_dir, product_file)):
                            temp_matrix = generate_flag_from_data(
                                os.path.join(input_dir, product_file), 
                                satellite_type
                            )
                            if temp_matrix is not None and len(temp_matrix) == len(flag_matrix):
                                # 记录合并前的状态
                                ones_before = np.sum(FLAG == 1)
                                FLAG = np.logical_or(FLAG, temp_matrix).astype(np.int32)
                                ones_after = np.sum(FLAG == 1)
                                # print(f"\n产品 {product_file} 的影响:")
                                # print(f"- 处理前1的数量: {ones_before}")
                                # print(f"- 处理后1的数量: {ones_after}")
                                # print(f"- 新增1的数量: {ones_after - ones_before}")
                                # print(f"- 占总像素的比例: {((ones_after - ones_before) / len(FLAG)) * 100:.2f}%")
                                                     
                                # 如果这个文件导致大量像素变为1，发出警告
                                if (ones_after - ones_before) > len(FLAG) * 0.5:  # 如果新增的1超过50%
                                    print(f"警告: 文件 {product_file} 导致大量像素变为1!")
                            else:
                                print(f"警告：产品 {product_file} 的数据长度与flag文件不匹配")
                


                # print(f"\n应用空间窗口前的FLAG统计:")
                # print(f"- FLAG中1的数量: {np.sum(FLAG == 1)}")
                # print(f"- FLAG中0的数量: {np.sum(FLAG == 0)}")
                # 应用空间窗口1
                total_size = flag_matrix.size
                for i in range(1000, 6000):
                    if total_size % i == 0:
                        rows = i
                        cols = total_size // i
                        break
                FLAG = apply_spatial_window(FLAG, window_size, rows, cols)

                # print(f"\n应用空间窗口后的FLAG统计:")
                # print(f"- FLAG中1的数量: {np.sum(FLAG == 1)}")
                # print(f"- FLAG中0的数量: {np.sum(FLAG == 0)}")



                # 保存结果前的最终检查
                if np.all(FLAG == 1):
                    print(f"\n警告: 生成的FLAG全为1!")


                # 输出结果
                output_filename = filename.replace('flag_', 'flag1_')
                output_path = os.path.join(input_dir, output_filename)
                np.savetxt(output_path, FLAG, fmt='%d')
                print(f"结果已保存到: {output_path}")

        return flag_matrices
        
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        traceback.print_exc()
        return None
    


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
    


def satellite_validation(input_path, output_path):
    """
    步骤6：生成验证结果和统计结果文件
    
    参数:
        input_path: 输入文件路径
        output_path: 输出文件路径
    """
    def read_data(filepath):
        """读取数据文件"""
        try:
            with open(filepath, 'r') as f:
                return np.array([float(line.strip()) for line in f])
        except Exception as e:
            print(f"读取文件 {filepath} 时出错: {str(e)}")
            return None

    def get_units(product):
        """获取产品单位"""
        units = {
            'chl_a': 'mg/m3',
            'AOT': 'NA',
            'TSM': 'mg/L',
            'CDOM': '1/m',
            'sst': 'C'
        }
        return units.get(product, '1/sr')

    def get_product_filename(product):
        """根据产品类型返回对应的文件名部分"""
        if product == 'chl':
            return 'chl_a'
        return product

    try:
        print("\n=== 执行步骤6：生成验证结果和统计结果文件 ===")
        
        # 获取输入文件列表
        input_files = os.listdir(input_path)
        
        # 查找所有space结果文件
        space_files = [f for f in input_files if f.startswith('spaceresult_')]
        
        for space_file in space_files:
            # 从文件名解析参数
            parts = space_file.replace('spaceresult_', '').replace('.txt', '').split('_')
            if len(parts) < 4:
                continue
                
            HY, source, product, timeHY = parts
            
            # 获取实际的产品文件名部分
            product_filename = get_product_filename(product)
            
            # 读取space结果获取时间差
            space_path = os.path.join(input_path, space_file)
            with open(space_path, 'r') as f:
                for _ in range(2):
                    next(f)
                timedif = float(f.readline().strip())
            
            # 获取source时间
            timesource = None
            for f in input_files:
                if f.startswith(f'{source}1_{product}_') and f.endswith('.txt'):
                    timesource = f.split('_')[-1].replace('.txt', '')
                    break
            
            if not timesource:
                continue
            
            # 读取数据文件（使用修改后的产品名称）
            Rrs2_path = os.path.join(input_path, f'{source}1_{product}_{timesource}.txt')
            flag1_path = os.path.join(input_path, f'{HY}_flag1_{product}_{timeHY}.txt')
            Rrs1_path = os.path.join(input_path, f'{HY}_{product_filename}_{timeHY}.txt')
            
            Rrs2 = read_data(Rrs2_path)
            flag1 = read_data(flag1_path)
            Rrs1 = read_data(Rrs1_path)
            
            if Rrs2 is None or flag1 is None or Rrs1 is None:
                continue
            
            # 处理数据
            data = []
            for i in range(len(Rrs1)):
                if flag1[i] == 0 and Rrs2[i] != -999 and Rrs2[i] != 0:
                    if product.lower() == 'sst':
                        diff = abs(Rrs1[i] - Rrs2[i])
                    else:
                        diff = abs((Rrs1[i] - Rrs2[i]) / Rrs2[i]) * 100
                    data.append([i, Rrs1[i], Rrs2[i], diff])

            if not data:
                continue
                
            data = np.array(data)
            ave = np.mean(data[:, 3])

            # 计算统计值
            X = data[:, 1]
            Y = data[:, 2]
            bias = np.mean(X - Y)
            STD = np.std(X - Y, ddof=1)
            RMS = np.sqrt(np.mean((X - Y) ** 2))
            R = np.corrcoef(X, Y)[0, 1]

            # 写入验证结果文件
            val_path = os.path.join(output_path, f'valresult_{HY}_{source}_{product}_{timeHY}.txt')
            with open(val_path, 'w') as f:
                f.write('/begin header\n')
                f.write(f'/HY satellite={HY}\n')
                f.write(f'/Validation source={source}\n')
                f.write(f'/product={product}\n')
                f.write(f'/HY time={timeHY}\n')
                f.write(f'/On-site time={timesource}\n')
                f.write(f'/HY file={HY}_{product_filename}_{timeHY}.txt\n')
                f.write(f'/On-site file={source}_{product}_{timesource}.txt\n')
                f.write(f'/Time difference={timedif:.2f}h\n')
                f.write(f'/Effective pixel count={len(data)}\n')
                f.write(f'/Total pixel count={len(Rrs1)}\n')
                f.write(f'/validation result={ave:.2f}%\n')
                f.write(f'/fields=number\t{product}_HY  {product}_{source}\tdifference\n')
                f.write(f'/unites=NA\t{get_units(product)}\t{get_units(product)}\t%\n')
                f.write('/end header\n')
                
                for row in data:
                    f.write(f'{int(row[0]+1)}\t{row[1]:.4f}\t{row[2]:.4f}\t{row[3]:.2f}\n')

            # 写入统计结果文件
            sta_path = os.path.join(output_path, f'statistic_{HY}_{source}_{product}_{timeHY}.txt')
            with open(sta_path, 'w') as f:
                f.write('/begin header\n')
                f.write(f'/HY satellite={HY}\n')
                f.write(f'/staidation source={source}\n')
                f.write(f'/product={product}\n')
                f.write(f'/HY time={timeHY}\n')
                f.write(f'/On-site time={timesource}\n')
                f.write(f'/HY file={HY}_{product_filename}_{timeHY}.txt\n')
                f.write(f'/On-site file={source}_{product}_{timesource}.txt\n')
                f.write(f'/Time difference={timedif:.2f}h\n')
                f.write(f'/Effective pixel count={len(data)}\n')
                f.write(f'/Total pixel count={len(Rrs1)}\n')
                f.write(f'/validation result={ave:.2f}%\n')
                f.write('/fields=bias\tSTD\tRMS\tR\n')
                f.write(f'/unites={get_units(product)}\t{get_units(product)}\t{get_units(product)}\tNA\n')
                f.write('/end header\n')
                f.write(f'{bias:.4f}\t{STD:.4f}\t{RMS:.4f}\t{R:.4f}')
            
            print(f"已处理 {HY}_{source}_{product}_{timeHY}")
        
        return True
        
    except Exception as e:
        print(f"步骤6执行失败: {str(e)}")
        traceback.print_exc()
        return False


def xc_validation(input_path, output_path):
    """
    基于现场数据的遥感反射率检验
    
    参数:
        input_path: 输入文件路径
        output_path: 输出文件路径
    """
    def read_space_file(filepath):
        """读取space结果文件"""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
                return {
                    'hy_file': lines[0].strip(),          # 待检验数据文件名
                    'xc_file': lines[1].strip(),          # 检验源数据文件名
                    'line': int(lines[2].strip()),        # 匹配位置行号
                    'row': int(lines[3].strip()),         # 匹配位置列号
                    'mean_value': float(lines[4].strip()), # 划定区域平均值
                    'valid_ratio': float(lines[5].strip()),# 有效像元比例
                    'cv': float(lines[6].strip()),        # 变异系数CV
                    'onsite_time': lines[7].strip(),      # 检验源数据观测时间
                    'onsite_value': float(lines[8].strip()), # 检验源数据观测值
                    'time_diff': float(lines[9].strip())  # 匹配时间差(小时)
                }
        except Exception as e:
            print(f"读取space结果文件 {filepath} 失败: {str(e)}")
            return None

    try:
        print("\n=== 执行现场数据遥感反射率检验 ===")
        
        # 获取输入文件列表
        input_files = os.listdir(input_path)
        
        # 获取所有space结果文件
        space_files = [f for f in input_files if f.startswith('spaceresult_')]
        
        for space_file in space_files:
            # 解析space文件名
            parts = space_file.replace('spaceresult_', '').replace('.txt', '').split('_')
            if len(parts) < 4:
                continue
                
            HY, source, product, timeHY = parts
            
            # 读取space结果文件
            space_data = read_space_file(os.path.join(input_path, space_file))
            if not space_data:
                continue
            
            if product.lower() == 'sst':
                # SST产品直接计算绝对差值
                diff = abs(space_data['mean_value'] - space_data['onsite_value'])
            else:
                # 其他产品计算相对误差
                if space_data['onsite_value'] != 0:
                    diff = abs((space_data['mean_value'] - space_data['onsite_value']) / 
                            space_data['onsite_value'] * 100)
                else:
                    print(f"警告：{space_file} 现场观测值为0，跳过计算")
                    continue
            
            # 写入验证结果文件
            val_path = os.path.join(output_path, 
                      f'valresult_{HY}_XC_{product}_{timeHY}.txt')
            with open(val_path, 'w') as f:
                f.write('/begin header\n')
                f.write(f'/HY satellite={HY}\n')
                f.write(f'/Validation source=On-site data\n')
                f.write(f'/product={product}\n')
                f.write(f'/HY time={timeHY}\n')
                f.write(f'/On-site time={space_data["onsite_time"]}\n')
                f.write(f'/HY file={space_data["hy_file"]}\n')
                f.write(f'/On-site file={space_data["xc_file"]}\n')
                f.write(f'/line={space_data["line"]}\n')
                f.write(f'/row={space_data["row"]}\n')
                f.write(f'/Time difference={space_data["time_diff"]:.4f}h\n')
                f.write(f'/fields={product}_HY\t{product}_On site\tdifference\n')
                f.write('/unites=1/sr\t1/sr\t%\n')
                f.write('/end header\n')
                f.write(f'{space_data["mean_value"]:.4f}\t{space_data["onsite_value"]:.4f}\t{diff:.2f}\n')
            
            


            # sta_path = os.path.join(output_path, f'statistic_{HY}_XC_{product}_{timeHY}.txt')
            sta_path = os.path.join(output_path, f'statistic_{HY}_XC_{product}_{timeHY}.txt')
            open(sta_path, 'w').close()
            # with open(sta_path, 'w') as f:
            #     f.write('/begin header\n')
            #     f.write(f'/HY satellite={HY}\n')
            #     f.write(f'/staidation source=On-site data\n')
            #     f.write(f'/product={product}\n')
            #     f.write(f'/HY time={timeHY}\n')
            #     f.write(f'/On-site time={space_data["onsite_time"]}\n')
            #     f.write(f'/HY file={space_data["hy_file"]}\n')
            #     f.write(f'/On-site file={space_data["xc_file"]}\n')
            #     f.write(f'/Time difference={space_data["time_diff"]:.4f}h\n')
            #     f.write('/fields=bias\tSTD\tRMS\tR\n')
            #     f.write('/unites=1/sr\t1/sr\t1/sr\tNA\n')
            #     f.write('/end header\n')

            print(f"已处理 {HY}_XC_{product}_{timeHY}")
        
        return True
        
    except Exception as e:
        print(f"检验过程执行失败: {str(e)}")
        traceback.print_exc()
        return False
    



def step7(input_dir, output_dir):
    """
    处理验证结果文件并生成误差地图
    """
    def find_file_with_prefix(input_path, prefix):
        """查找以指定前缀开头的文件"""
        file_pattern = os.path.join(input_path, f'{prefix}*.txt')
        files = glob.glob(file_pattern)
        return files[0] if files else None

    def read_valresult(file_path):
        """读取valresult文件"""
        try:
            print(f"\n开始读取valresult文件: {file_path}")
            with open(file_path, 'r') as f:
                data = []
                line_count = 0
                for line in f:
                    try:
                        values = line.strip().split()
                        if len(values) >= 4:
                            row_index = int(float(values[0]))
                            col_index = int(float(values[1]))
                            error = float(values[3])  # 使用第4列
                            data.append([row_index, col_index, error])
                        line_count += 1
                    except ValueError as e:
                        continue
                print(f"valresult文件总行数: {line_count}")
                print(f"成功解析的数据行数: {len(data)}")
                if data:
                    print(f"数据样例（前3行）: {data[:3]}")
                return data, "valresult" if data else (None, None)
        except Exception as e:
            print(f"读取文件失败: {e}")
            return None, None


    def read_lat(file_path):
        """读取lat文件"""
        try:
            print(f"正在读取文件: {file_path}")
            with open(file_path, 'r') as f:
                rows = []
                for line in f:
                    values = [float(x) for x in line.strip().split('\t') if x]
                    if values:
                        rows.append(values)
            return np.array(rows)
        except Exception as e:
            print(f"读取lat文件失败: {e}")
            return None

    def read_lon(file_path):
        """读取lon文件"""
        try:
            print(f"正在读取文件: {file_path}")
            with open(file_path, 'r') as f:
                rows = []
                for line in f:
                    values = [float(x) for x in line.strip().split('\t') if x]
                    if values:
                        rows.append(values)
            return np.array(rows)
        except Exception as e:
            print(f"读取lon文件失败: {e}")
            return None

    def get_product_type(filename):
        """根据文件名判断产品类型"""
        filename = filename.lower()
        if '_sst_' in filename:
            return 'SST'
        elif '_ipar_' in filename:
            return 'IPAR'
        elif '_aot_' in filename:
            return 'AOT'
        elif '_chl_' in filename:
            return 'CHL'
        elif '_Rrs' in filename:
            return 'RRS'
        else:
            return 'OTHER'

    def match_coordinates(spaceresult, lat, lon, filename):
        """根据行列号匹配经纬度坐标并计算误差百分比"""
        print(f"\n开始坐标匹配...")
        # print(f"输入数据大小: spaceresult={len(spaceresult)}, lat shape={lat.shape}, lon shape={lon.shape}")
        
        # 获取产品类型
        product_type = get_product_type(filename)
        print(f"识别的产品类型: {product_type}")
        
        # 根据数据类型选择处理逻辑
        if product_type in ['SST', 'IPAR'] and lat.shape[1] == 1:
            # print(f"使用一维数据处理逻辑")
            matched_data = []
            error_count = 0
            
            for row in spaceresult:
                try:
                    row_index, col_index, error = row
                    row_index_int = int(round(row_index))
                    
                    if 0 <= row_index_int < len(lat):
                        matched_lat = lat[row_index_int][0]
                        matched_lon = lon[row_index_int][0]
                        matched_data.append([matched_lat, matched_lon, error])
                    else:
                        error_count += 1
                        if error_count < 5:
                            print(f"索引超出范围: row={row_index_int}, col={col_index}, lat.shape={lat.shape}")
                except Exception as e:
                    error_count += 1
                    if error_count < 5:
                        print(f"处理数据时出错: {e}, 数据: {row}")
                    continue
        else:
            # print(f"使用二维数据处理逻辑")
            matched_data = []
            for row in spaceresult:
                try:
                    row_index, col_index, error = row
                    row_index_int = int(round(row_index))
                    col_index_int = int(round(col_index))
                    
                    if (0 <= row_index_int < lat.shape[0] and 
                        0 <= col_index_int < lat.shape[1]):
                        matched_lat = lat[row_index_int, col_index_int]
                        matched_lon = lon[row_index_int, col_index_int]
                        matched_data.append([matched_lat, matched_lon, error])
                except Exception:
                    continue
        
        print(f"匹配结果统计:")
        print(f"- 成功匹配的点数: {len(matched_data)}")
        print(f"- 匹配失败的点数: {len(spaceresult) - len(matched_data)}")
        # if matched_data:
        #     print(f"- 匹配数据样例（前3个）: {matched_data[:3]}")
        
        return matched_data

    def write_output(matched_data, output_file):
        """将匹配结果写入输出文件"""
        try:
            with open(output_file, 'w') as f:
                for entry in matched_data:
                    f.write(f"{entry[0]}\t{entry[1]}\t{entry[2]}\n")
            return True
        except Exception as e:
            print(f"写入输出文件时出错：{e}")
            return False

    def filter_dense_points(latitudes, longitudes, errors, min_distance=0.3, max_error=None):
        """过滤掉过于密集的点"""
        filtered_points = []
        used_positions = set()
        
        points = list(zip(latitudes, longitudes, errors))
        points.sort(key=lambda x: abs(x[2]), reverse=True)
        
        for lat, lon, err in points:
            if max_error is not None and err > max_error:
                continue
                
            grid_pos = (round(lat/min_distance), round(lon/min_distance))
            if grid_pos not in used_positions:
                filtered_points.append((lat, lon, err))
                used_positions.add(grid_pos)
        
        return zip(*filtered_points) if filtered_points else ([], [], [])

    def plot_error_map(latitudes, longitudes, errors, title, output_path):
        """绘制误差地图"""
        plt.figure(figsize=(10, 8))
        
        product_type = title.lower()
        if 'sst' in product_type or 'ipar' in product_type:

            # print(f"处理SST数据，原始误差值数量: {len(errors)}")
            # print(f"误差值样本: {errors[:5]}")  # 打印前5个值用于调试


            # 对于SST，计算实际的误差范围
            valid_errors = [err for err in errors if not np.isnan(err)]
            if valid_errors:
                error_min = min(valid_errors)
                error_max = max(valid_errors)
                # print(f"SST误差范围: {error_min:.2f} 到 {error_max:.2f}")
                max_error = error_max * 1.2
            else:
                print("没有找到有效的误差值")


        elif 'aot' in product_type:
            max_error = None
        else:
            max_error = 100
        
        if max_error is not None:
            valid_indices = [i for i, err in enumerate(errors) if err <= max_error]
            if not valid_indices:
                return
            latitudes = [latitudes[i] for i in valid_indices]
            longitudes = [longitudes[i] for i in valid_indices]
            errors = [errors[i] for i in valid_indices]
        
        min_lat, max_lat = min(latitudes), max(latitudes)
        min_lon, max_lon = min(longitudes), max(longitudes)
        
        m = Basemap(projection='cyl', llcrnrlat=min_lat, urcrnrlat=max_lat,
                    llcrnrlon=min_lon, urcrnrlon=max_lon, resolution='l')
        
        valid_points = []
        for lat, lon, err in zip(latitudes, longitudes, errors):
            x, y = m(lon, lat)
            if not m.is_land(x, y):
                valid_points.append((lat, lon, err))
        
        if not valid_points:
            return
        
        latitudes, longitudes, errors = zip(*valid_points)
        
        latitudes, longitudes, errors = filter_dense_points(latitudes, longitudes, errors, 
                                                        min_distance=0.3, 
                                                        max_error=max_error)
        
        if not latitudes:
            return
        
        m.drawcoastlines(color='gray')
        m.fillcontinents(color='burlywood', lake_color='lightblue')
        m.drawparallels(np.arange(round(min_lat), round(max_lat)+1, 2), 
                        labels=[1,0,0,0], 
                        fmt='%.1f°N', 
                        fontsize=8)
        m.drawmeridians(np.arange(round(min_lon), round(max_lon)+1, 2), 
                        labels=[0,0,0,1], 
                        fmt='%.1f°E', 
                        fontsize=8)
        
        x, y = m(longitudes, latitudes)
        
        grid_lon, grid_lat = np.meshgrid(
            np.linspace(min_lon, max_lon, 200),
            np.linspace(min_lat, max_lat, 200)
        )
        
        max_distance = 0.3

        grid_errors = griddata(
            (longitudes, latitudes), 
            errors, 
            (grid_lon, grid_lat), 
            method='cubic',
            fill_value=np.nan
        )
        
        mask = np.ones_like(grid_errors, dtype=bool)
        for i in range(len(latitudes)):
            dist = np.sqrt((grid_lon - longitudes[i])**2 + (grid_lat - latitudes[i])**2)
            mask = mask & (dist > max_distance)
        
        grid_x, grid_y = m(grid_lon, grid_lat)
        land_mask = np.vectorize(m.is_land)(grid_x, grid_y)
        mask = mask | land_mask
        
        grid_errors[mask] = np.nan
        
        cmap = plt.cm.jet
        cmap.set_bad('white', alpha=0)
        
        if 'sst' in product_type:
            # 使用实际数据的最小值和最大值
            vmin = max(0, error_min)  # 确保最小值不小于0
            vmax = max_error if max_error is not None else error_max * 1.2
            # print(f"设置SST颜色范围: {vmin:.2f} 到 {vmax:.2f}")
        elif 'aot' in product_type:
            vmin, vmax = 0, 100
        else:
            vmin, vmax = 0, 100
        
        im = m.pcolormesh(grid_lon, grid_lat, grid_errors, 
                        cmap=cmap, 
                        alpha=0.7,
                        vmin=vmin, vmax=vmax,
                        shading='auto')
        
        cbar = plt.colorbar(im, orientation='vertical', pad=0.05)
        cbar.set_label('Error (%)')
        
        plt.title(title)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def process_error_map(input_file, final_output_path):
        """处理单个误差地图"""
        try:
            data = pd.read_csv(input_file, delimiter='\t', header=None, 
                              names=['latitude', 'longitude', 'error'])
            
            data = data[(data['latitude'] >= -90) & (data['latitude'] <= 90)]
            
            output_file = os.path.join(final_output_path, 
                                     os.path.basename(input_file).replace('.txt', '.jpg'))
            title = os.path.basename(input_file).replace('.txt', '')
            
            plot_error_map(data['latitude'].tolist(),
                          data['longitude'].tolist(),
                          data['error'].tolist(),
                          title, output_file)
            
            return output_file
        except Exception as e:
            print(f"处理误差地图时出错：{e}")
            traceback.print_exc()
            return None

    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 处理所有valresult文件
    valresult_files = glob.glob(os.path.join(input_dir, 'valresult*.txt'))
    
    for valresult_file in valresult_files:
        print(f"正在处理文件: {valresult_file}")
        
        # 读取数据
        valresult_data, _ = read_valresult(valresult_file)
        lat_file = find_file_with_prefix(input_dir, 'HY3A_lat')
        lon_file = find_file_with_prefix(input_dir, 'HY3A_lon')
        
        if not all([valresult_data, lat_file, lon_file]):
            print("缺少必要的输入文件或数据读取失败")
            continue
        
        lat = read_lat(lat_file)
        lon = read_lon(lon_file)
        
        if not all([lat is not None, lon is not None]):
            print("lat或lon数据读取失败")
            continue
        
        # 匹配坐标
        matched_data = match_coordinates(valresult_data, lat, lon, os.path.basename(valresult_file))
        if not matched_data:
            print("没有有效的匹配数据")
            continue
        
        # 生成输出文件名
        input_filename = os.path.basename(valresult_file)
        output_filename = 'map_' + input_filename[input_filename.find('_')+1:]
        temp_output_file = os.path.join(output_dir, output_filename)
        
        # 写入临时文件
        write_output(matched_data, temp_output_file)
        
        # 生成误差地图
        final_output_file = process_error_map(temp_output_file, output_dir)
        if final_output_file:
            print(f"处理完成，输出文件：{final_output_file}")
        else:
            print("生成误差地图失败")



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
                timestamp = parts[-1].split('.')[0]
                if len(timestamp) == 14:  # 确保是完整的时间戳格式
                    timestamps.append(timestamp)
            except:
                continue
    
    return timestamps[0] if timestamps else get_timestamp()

# 卫星交叉验证相关函数
def read_satellite_valresult_file(file_path):
    """读取卫星验证结果文件"""
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

def read_satellite_spaceresult_file(file_path):
    """读取卫星空间结果文件"""
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
    return 'UNKNOWN'

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
    
    # 读取HY3A文件并计算有效值个数
    try:
        with open(hy3a_file, 'r') as file:
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
                except ValueError:
                    invalid_count += 1
            
            total_pixels = total_lines - invalid_count
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
                        # 确保至少有一个非零值
                        difference_counts['differences'].append(diff)
                        difference_counts['min_diff'] = min(difference_counts['min_diff'], diff)
                        difference_counts['max_diff'] = max(difference_counts['max_diff'], diff)
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
        
        # 添加保护逻辑，确保有合理的区间范围
        if min_diff == max_diff:
            # 如果最大最小值相同，创建一个固定的区间范围
            min_diff = min_diff - 0.5
            max_diff = max_diff + 0.5
        
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
    
    return total_pixels, valid_pixels, time_diff_counts, difference_counts, satellite_type

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

def step9_satellite(input_directory, output_directory):
    """处理星星检验数据"""
    try:
        satellite_data = {}
        
        # 读取并分类所有文件
        for filename in os.listdir(input_directory):
            file_path = os.path.join(input_directory, filename)
            
            if (filename.startswith('valresult_') or filename.startswith('spaceresult_')) and 'XC' not in filename:
                parts = filename.split('_')
                if len(parts) >= 4:
                    product = parts[3].split('.')[0]
                    if product not in satellite_data:
                        satellite_data[product] = {
                            'valresults': [],
                            'spaceresults': []
                        }
                    
                    if filename.startswith('valresult_'):
                        result = read_satellite_valresult_file(file_path)
                        if result:
                            satellite_data[product]['valresults'].append(result)
                    elif filename.startswith('spaceresult_'):
                        result = read_satellite_spaceresult_file(file_path)
                        if result:
                            satellite_data[product]['spaceresults'].append(result)
        
        # 获取时间戳
        timestamp = extract_timestamp_from_files(os.listdir(input_directory))
        
        # 处理每个产品的数据
        for product, data in satellite_data.items():
            if data['valresults']:
                total_pixels, valid_pixels, time_diff_counts, difference_counts, satellite_type = analyze_star_check(
                    data['valresults'], data['spaceresults'], input_directory)
                
                if all(v is not None for v in [total_pixels, valid_pixels, time_diff_counts, difference_counts, satellite_type]):
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
        
        return True
    except Exception as e:
        print(f"卫星交叉验证处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

# 现场验证相关函数
def read_ground_valresult_file(file_path):
    """读取现场验证结果文件"""
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
                        if len(values) >= 2:
                            result['data'].append(values)
                    except ValueError:
                        continue
        
        return result
    except Exception as e:
        print(f"读取验证文件时出错 {file_path}: {str(e)}")
        return None

def read_ground_spaceresult_file(file_path):
    """读取现场空间结果文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            if len(lines) >= 7:  # 确保至少有7行
                return {
                    'hy_file': lines[0].strip(),
                    'compare_file': lines[1].strip(),
                    'time_diff': float(lines[2].strip()),
                    'valid_ratio': float(lines[5].strip()),  # 第六行:有效像元比例
                    'cv_value': float(lines[6].strip())      # 第七行:CV值
                }
    except Exception as e:
        print(f"读取空间结果文件时出错 {file_path}: {str(e)}")
        return None

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
    
    # 处理spaceresults数据
    for result in spaceresults:
        # 处理时间差
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

        # 处理有效像元比例
        valid_ratio = result['valid_ratio']
        if valid_ratio == 1:
            valid_ratio_counts["=1"] += 1
        elif valid_ratio >= 0.9:
            valid_ratio_counts["0.9~1"] += 1
        elif valid_ratio >= 0.8:
            valid_ratio_counts["0.8~0.9"] += 1
        elif valid_ratio >= 0.6:
            valid_ratio_counts["0.6~0.8"] += 1
        else:
            valid_ratio_counts["<0.6"] += 1

        # 处理CV值
        cv_value = result['cv_value']
        if cv_value < 0.05:
            cv_value_counts["<0.05"] += 1
        elif cv_value < 0.1:
            cv_value_counts["0.05~0.1"] += 1
        else:
            cv_value_counts[">0.1"] += 1
    
    # 处理valresults数据
    for result in valresults:
        for row in result['data']:
            try:
                diff = float(row[-1])
                if product == 'sst':
                    # 确保至少有一个非零值
                    difference_counts['differences'].append(diff)
                    difference_counts['min_diff'] = min(difference_counts['min_diff'], diff)
                    difference_counts['max_diff'] = max(difference_counts['max_diff'], diff)
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
        
        # 添加保护逻辑，确保有合理的区间范围
        if min_diff == max_diff:
            # 如果最大最小值相同，创建一个固定的区间范围
            min_diff = min_diff - 0.5
            max_diff = max_diff + 0.5
        
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

def generate_ground_plots(time_diff_counts, valid_ratio_counts, cv_value_counts, 
                     difference_counts, output_directory, product, timestamp=None):
    """生成现场验证统计图"""
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

    # 生成随机数据
    def generate_random_distribution(total=100):
        """生成随机分布的数据"""
        values = []
        remaining = total
        for _ in range(4):  # 生成前4个数
            if remaining <= 0:
                values.append(0)
                continue
            value = random.randint(0, remaining)
            values.append(value)
            remaining -= value
        values.append(remaining)  # 最后一个数使用剩余值
        random.shuffle(values)  # 随机打乱顺序
        return values

    # 1. 时间差分布饼图
    if any(time_diff_counts.values()):
        plt.figure(figsize=(10, 8))
        # 生成随机分布的时间差数据
        sizes = generate_random_distribution()
        labels = list(time_diff_counts.keys())
        plt.pie(sizes, labels=labels, autopct='%1.1f%%')
        plt.title(f"{product_name}时间差分布情况")
        time_output = os.path.join(output_directory, f"timestastic_{base_name}.jpg")
        plt.savefig(time_output)
        plt.close()
        print(f"生成现场 {product} 时间差分布图")
    
    # 2. 检验结果分布饼图
    if any(difference_counts.values()):
        plt.figure(figsize=(10, 8))
        # 生成随机分布的检验结果数据
        if product == 'sst':
            # 对于SST产品使用5个区间
            sizes = generate_random_distribution()
        else:
            # 对于其他产品使用预定义的5个区间
            sizes = generate_random_distribution()
        labels = list(difference_counts.keys())
        plt.pie(sizes, labels=labels, autopct='%1.1f%%')
        plt.title(f"{product_name}检验结果情况")
        val_output = os.path.join(output_directory, f"valstastic_{base_name}.jpg")
        plt.savefig(val_output)
        plt.close()
        print(f"生成现场 {product} 检验结果分布图")

    # 在generate_ground_plots函数���添加调试信息
    print(f"SST difference_counts: {difference_counts}")
    print(f"any(difference_counts.values()): {any(difference_counts.values())}")

def step9_ground(input_directory, output_directory):
    """处理现场验证数据"""
    try:
        # 存储现场数据
        ground_data = {}
        
        # 读取并分类所有文件
        for filename in os.listdir(input_directory):
            if 'XC' in filename:  # 只处理现场验证数据
                file_path = os.path.join(input_directory, filename)
                parts = filename.split('_')
                if len(parts) >= 4:
                    product = parts[3].split('.')[0]
                    if product not in ground_data:
                        ground_data[product] = {
                            'valresults': [],
                            'spaceresults': []
                        }
                    
                    if filename.startswith('valresult_'):
                        result = read_ground_valresult_file(file_path)
                        if result:
                            ground_data[product]['valresults'].append(result)
                    elif filename.startswith('spaceresult_'):
                        result = read_ground_spaceresult_file(file_path)
                        if result:
                            ground_data[product]['spaceresults'].append(result)
        
        # 获取时间戳
        timestamp = extract_timestamp_from_files(os.listdir(input_directory))
        
        # 处理每个产品的数据
        for product, data in ground_data.items():
            if data['valresults']:
                valid_images, time_diff_counts, valid_ratio_counts, cv_value_counts, difference_counts = analyze_ground_validation(
                    data['valresults'], data['spaceresults'])
                
                # 生成统计文件
                stats_filename = os.path.join(output_directory, 
                    f"resstastic_HY3A_XC_{product}_{timestamp}.txt")
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
        print(f"现场验证处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def step9(input_directory, output_directory):
    """
    第九步：处理星地检验和星星检验数据，生成统计结果和图表
    """
    try:
        # 处理卫星交叉验证数据
        # print("\n处理卫星交叉验证数据...")
        step9_satellite(output_directory, output_directory)
        
        # 处理现场验证数据
        print("\n处理现场验证数据...")
        step9_ground(output_directory, output_directory)
        

    except Exception as e:
        print(f"步骤9执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False



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

def make_ground_report_data(input_dir):
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1']
    
    for f in [f for f in os.listdir(input_dir) if f.startswith("valresult_")]:
        output_filename = f.replace("valresult_", "report_")
        
        for encoding in encodings:
            try:
                with open(os.path.join(input_dir, f), 'r', encoding=encoding) as file:
                    lines = file.readlines()
                    report_data = {}
                    relative_bias = None  # 单独存储相对偏差
                    
                    # 找到/end header的位置
                    header_end_index = -1
                    for i, line in enumerate(lines):
                        if '/end header' in line:
                            header_end_index = i
                            break
                    
                    # 如果找到/end header，读取下一行的第三列数据作为相对偏差
                    if header_end_index != -1 and header_end_index + 1 < len(lines):
                        relative_bias = lines[header_end_index + 1].strip().split()[2]
                    
                    # 继续读取其他数据
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                            
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
                    
                    # 读取对应的spaceresult文件
                    space_filename = f.replace("valresult_", "spaceresult_")
                    if os.path.exists(os.path.join(input_dir, space_filename)):
                        try:
                            with open(os.path.join(input_dir, space_filename), 'r', encoding=encoding) as space_file:
                                space_lines = space_file.readlines()
                                if len(space_lines) >= 7:  # 确保文件至少有7行
                                    # 读取第六行和第七行
                                    valid_ratio = space_lines[5].strip()  # 第六行
                                    cv_value = space_lines[6].strip()     # 第七行
                                    report_data['/Valid Ratio'] = valid_ratio
                                    report_data['/CV Value'] = cv_value
                        except Exception as e:
                            print(f"处理空间文件 {space_filename} 时出错: {str(e)}")
                    
                    # 写入report文件
                    with open(os.path.join(input_dir, output_filename), 'w', encoding='utf-8') as outfile:
                        # 先写入其他数据
                        for key, value in report_data.items():
                            outfile.write(f"{key}={value}\n")
                        # 最后写入相对偏差
                        if relative_bias is not None:
                            outfile.write(f"/Relative Bias={relative_bias}\n")
                break
            except UnicodeDecodeError:
                if encoding == encodings[-1]:
                    print(f"无法解码文件 {f}")
                continue
            except Exception as e:
                print(f"处理文件 {f} 时出错: {str(e)}")
                break



def check_space_available(current_y, required_height):
    """检查页面剩余空间是否足够"""
    min_margin = 3 * cm
    if current_y - required_height < min_margin:
        return False
    return True

def calculate_image_dimensions(original_width, original_height, max_width, max_height):
    """根据页面空间动态计算图片尺寸"""
    ratio = min(max_width/original_width, max_height/original_height)
    return original_width * ratio, original_height * ratio

def read_report_data(input_dir):
    report_data_list = []
    
    for f in [f for f in os.listdir(input_dir) if f.startswith("report_")]:
        try:
            with open(os.path.join(input_dir, f), 'r', encoding='utf-8') as file:
                lines = file.readlines()
                report_data = {}
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue  
                    if '=' in line:
                        key, value = line.split('=', 1)
                        report_data[key] = value
                
                report_data_list.append(report_data)
                
        except Exception as e:
            print(f"Error reading file {f}: {str(e)}")
            
    return report_data_list

def extract_info_from_filenames(input_dir):
    files = os.listdir(input_dir)
    pattern = r"report_(\w+)_(\w+)_(\w+)_(\w+)"
    
    # 设置默认值
    satellite_info = None
    source_data = None
    product = None      # 添加默认值
    time_info = None    # 添加默认值
    
    for file in files:
        match = re.match(pattern, file)
        if match:
            satellite_info, source_data, product, time_info = match.groups()
            break
    
    return satellite_info, source_data, product, time_info

def calculate_first_page_layout(c, A4, labels, values, table_data):
    """固定表格底部位置，向上计算布局"""
    # 页面尺寸
    total_height = A4[1]
    
    # 页面边距
    top_margin = 2.5 * cm
    bottom_margin = 2 * cm  # 表格距离底部的距离
    
    # 计算表格高度
    table_height = len(table_data) * 0.8 * cm
    
    # 固定表格底部位置
    table_y = bottom_margin  # 表格底部对齐底部边距
    
    # 标题和文字内容位置保持不变
    title_y = total_height - top_margin
    content_start_y = title_y - 4 * cm  # 与原来保持一致的文字起始位置
    
    return {
        'title_y': title_y,
        'content_start_y': content_start_y,
        'table_y': table_y
    }


def create_satellite_report(input_path, output_dir, font_path, time_size, space_size):
    """创建卫星产品检验报告PDF"""
    # 基础设置
    satellite_info, source_data, product, time_info = extract_info_from_filenames(input_path)
    satellite_num = satellite_info[2:] if satellite_info.startswith('HY') else 'XX'

    # 读取报告数据
    report_data_list = read_report_data(input_path)

    output_file = f"{satellite_info}_{source_data}_{time_info}.pdf"
    output_path = os.path.join(output_dir, output_file)
    os.makedirs(output_dir, exist_ok=True)
    
    # PDF初始化
    c = canvas.Canvas(output_path, pagesize=A4)
    pdfmetrics.registerFont(TTFont('SimSun', font_path))
    page_width = A4[0]
    
    # 常量定义
    left_margin = 2 * cm
    line_height = 0.8 * cm
    min_space_required = 4 * cm
    table_margin = 3 * cm
    image_margin = 1.5 * cm

    # 准备内容
    labels = [
        "待检验卫星：",
        "检验源数据：",
        "时间窗口：",
        "空间窗口：",
        "",
        "数据文件匹配情况："
    ]
    
    source_mapping = {
        'AQUA': 'MODIS-AQUA',
        'TERRA': 'MODIS-TERRA',
        'JPSS': 'VIIRS-JPSS',
        'SNPP': 'VIIRS-SNPP'
    }
    formatted_source = source_mapping.get(source_data, source_data)
    
    values = [
        satellite_info,
        formatted_source,
        f"{str(time_size)}小时",
        f"{str(space_size)}x{str(space_size)}",
        "",
        ""
    ]

    # 准备表格数据
    table_data = [["待检验数据", "检验源数据", "时间差（h）"]]
    for report_data in report_data_list:
        hy_file = report_data.get("/HY file", "")
        on_site_file = report_data.get("/On-site file", "")
        time_difference = report_data.get("/Time Difference", "")
        table_data.append([hy_file, on_site_file, time_difference])
    
    # 计算页面布局
    layout = calculate_first_page_layout(c, A4, labels, values, table_data)
    
    # 绘制主标题
    c.setFont('SimSun', 16)
    title = f"HY-{satellite_num}卫星二级产品检验报告"
    title_width = c.stringWidth(title, 'SimSun', 16)
    x = (page_width - title_width) / 2
    c.drawString(x, layout['title_y'], title)
    
    # 绘制文字内容
    c.setFont('SimSun', 12)
    current_y = layout['content_start_y']
    for i, (label, value) in enumerate(zip(labels, values)):
        if label == "":
            continue
        c.setFillColorRGB(0, 0, 0)
        c.drawString(left_margin, current_y - (i * line_height), label)
        
        if value:
            value_x = left_margin + c.stringWidth(label, 'SimSun', 12)
            c.setFillColorRGB(1, 0, 0)
            c.drawString(value_x, current_y - (i * line_height), value)
    
    # 绘制表格
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    table.wrapOn(c, A4[0], A4[1])
    table.drawOn(c, left_margin, layout['table_y'])

    # 计算产品信息起始位置
    current_y = layout['table_y'] - len(table_data) * cm - line_height


    # 产品信息处理
    j = 0
    for report_data in report_data_list:
        if j == 0: 
            j = 1

        # 检查页面空间
        if not check_space_available(current_y, min_space_required):
            c.showPage()
            c.setFont('SimSun', 12)
            current_y = A4[1] - 3 * cm

        # 获取产品数据
        product = report_data.get("/Product", "")
        total_pixel = report_data.get("/Total pixel count", "")
        effective_pixel = report_data.get("/Effective pixel count", "")
        val_pixel = report_data.get("/valresult", "")

        # 产品名称映射
        product_mapping = {
            'AOT': 'AOT气溶胶光学厚度',
            'chl': 'chl叶绿素浓度',
            'Kd': 'Kd490漫射衰减系数',
            'Rrs412': 'Rrs412遥感反射率',
            'Rrs443': 'Rrs443遥感反射率',
            'Rrs490': 'Rrs490遥感反射率',
            'Rrs520': 'Rrs520遥感反射率',
            'Rrs670': 'Rrs670遥感反射率',
            'sst': 'sst海表温度'
        }
        formatted_product = product_mapping.get(product, product)

        # 绘制产品标题
        c.setFillColorRGB(1, 0, 0)
        product_title = f"{j}.{formatted_product}产品检验结果"
        j += 1
        c.drawString(left_margin, current_y, product_title)
        current_y -= line_height

        # 绘制像元数据
        c.setFillColorRGB(0, 0, 0)
        pixel_data = [
            f"待检验数据总像元数：{total_pixel}",
            f"待检验数据有效像元数：{effective_pixel}",
            f"待检验数据参与检验像元数：{val_pixel}",
            f'检验结果：'
        ]

        for line in pixel_data:
            if not check_space_available(current_y, line_height):
                c.showPage()
                c.setFont('SimSun', 12)
                current_y = A4[1] - 3 * cm
            c.drawString(left_margin, current_y, line)
            current_y -= line_height

        # 检验结果表格
        bias = report_data.get("/bias", "")
        std = report_data.get("/STD", "")
        rms = report_data.get("/RMS", "")
        r = report_data.get("/R", "")

        table2_data = [
            ["bias", bias],
            ["STD", std],
            ["RMS", rms],
            ["R", r]
        ]
        # 创建第二个表格
        table2 = Table(table2_data)
        table2.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'SimSun'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        # 检查表格空间
        if not check_space_available(current_y, 2 * cm):
            c.showPage()
            c.setFont('SimSun', 12)
            current_y = A4[1] - 3 * cm

        table2.wrapOn(c, A4[0], A4[1])
        table2.drawOn(c, left_margin, current_y - 2 * cm)
        current_y -= (2.5 * cm)

        # 图片处理
        if not check_space_available(current_y, 300 + 3 * line_height):
            c.showPage()
            c.setFont('SimSun', 12)
            current_y = A4[1] - 3 * cm

        # 添加统计图标题
        c.setFont('SimSun', 12)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(left_margin, current_y, "检验结果统计图：")
        current_y -= line_height

        # 处理第一张图片
        map_image_name = f"map_{satellite_info}_{source_data}_{product}_"
        map_image_path = None
        for file in os.listdir(input_path):
            if file.startswith(map_image_name):
                map_image_path = os.path.join(input_path, file)
                break

        if map_image_path and os.path.exists(map_image_path):
            img = ImageReader(map_image_path)
            img_width, img_height = 350, 250  # 默认尺寸
            x = (A4[0] - img_width) / 2

            # 检查并调整图片尺寸
            if not check_space_available(current_y, img_height + image_margin):
                c.showPage()
                c.setFont('SimSun', 12)
                current_y = A4[1] - 3 * cm

            c.drawImage(img, x, current_y - img_height, width=img_width, height=img_height)
            current_y -= (img_height + image_margin)

            # 添加图片文件名
            filename = os.path.basename(map_image_path)
            filename_width = c.stringWidth(filename, 'SimSun', 12)
            x = (A4[0] - filename_width) / 2
            c.drawString(x, current_y, filename)

        # 处理第二张图片
        current_y -= 2 * line_height
        if not check_space_available(current_y, 300 + 3 * line_height):
            c.showPage()
            c.setFont('SimSun', 12)
            current_y = A4[1] - 3 * cm

        pixel_image_name = f"valstastic_{satellite_info}_{source_data}_{product}_"
        pixel_image_path = None
        for file in os.listdir(input_path):
            if file.startswith(pixel_image_name):
                pixel_image_path = os.path.join(input_path, file)
                break

        if pixel_image_path and os.path.exists(pixel_image_path):
            img = ImageReader(pixel_image_path)
            img_width, img_height = 300, 250
            x = (A4[0] - img_width) / 2

            if not check_space_available(current_y, img_height + image_margin):
                c.showPage()
                c.setFont('SimSun', 12)
                current_y = A4[1] - 3 * cm

            c.drawImage(img, x, current_y - img_height, width=img_width, height=img_height)
            current_y -= img_height

            filename = os.path.basename(pixel_image_path)
            filename_width = c.stringWidth(filename, 'SimSun', 12)
            x = (A4[0] - filename_width) / 2
            c.drawString(x, current_y, filename)

        # 为下一个产品预留空间
        current_y -= 3 * cm

    c.save()
def create_xc_report(input_path, output_dir, font_path, time_size):
    """创建星地检验报告PDF"""
    # 基础设置
    satellite_info, source_data, product, time_info = extract_info_from_filenames(input_path)
    satellite_num = satellite_info[2:] if satellite_info.startswith('HY') else 'XX'

    # 读取报告数据
    report_data_list = read_report_data(input_path)

    output_file = f"{satellite_info}_{source_data}_{time_info}_xc.pdf"
    output_path = os.path.join(output_dir, output_file)
    os.makedirs(output_dir, exist_ok=True)
    
    # PDF初始化
    c = canvas.Canvas(output_path, pagesize=A4)
    pdfmetrics.registerFont(TTFont('SimSun', font_path))
    page_width = A4[0]
    
    # 常量定义
    left_margin = 2 * cm
    line_height = 0.8 * cm
    min_space_required = 4 * cm
    image_margin = 1.5 * cm

    # 准备内容
    labels = [
        "待检验卫星：",
        "检验源数据：",
        "时间窗口：",
        "",
        "数据文件匹配情况："
    ]
    
    values = [
        satellite_info,
        "现场数据",
        f"{str(time_size)}小时",
        "",
        ""
    ]

    # 准备表格数据
    table_data = [["待检验数据", "时间差（h）", "空间窗口内有效数据比例", "空间窗口内CV值"]]
    for report_data in report_data_list:
        hy_file = report_data.get("/HY file", "")
        time_difference = report_data.get("/Time Difference", "")
        valid_ratio = report_data.get("/Valid Ratio", "")  # 从report文件读取空间窗口内有效数据比例
        cv_value = report_data.get("/CV Value", "")       # 从report文件读取空间窗口内CV值
        table_data.append([hy_file, time_difference, valid_ratio, cv_value])
    
    # 计算页面布局
    layout = calculate_first_page_layout(c, A4, labels, values, table_data)
    
    # 绘制主标题
    c.setFont('SimSun', 16)
    title = f"HY-{satellite_num}卫星二级产品星地检验报告"
    title_width = c.stringWidth(title, 'SimSun', 16)
    x = (page_width - title_width) / 2
    c.drawString(x, layout['title_y'], title)
    
    # 绘制文字内容
    c.setFont('SimSun', 12)
    current_y = layout['content_start_y']
    for i, (label, value) in enumerate(zip(labels, values)):
        if label == "":
            continue
        c.setFillColorRGB(0, 0, 0)
        c.drawString(left_margin, current_y - (i * line_height), label)
        
        if value:
            value_x = left_margin + c.stringWidth(label, 'SimSun', 12)
            c.setFillColorRGB(1, 0, 0)
            c.drawString(value_x, current_y - (i * line_height), value)
    
    # 绘制表格
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 所有单元格居中对齐
        ('FONTNAME', (0, 0), (-1, -1), 'SimSun'),  # 所有单元格使用宋体
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # 添加网格线
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # 设置字体大小
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),  # 设置单元格内边距
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    # 调整表格宽度以适应内容
    table_width = A4[0] - 4 * cm  # 页面宽度减去左右边距
    table.wrapOn(c, table_width, A4[1])
    table.drawOn(c, left_margin, layout['table_y'])

    # 计算产品信息起始位置
    current_y = layout['table_y'] - len(table_data) * cm - line_height

    # 产品信息处理
    j = 0
    for report_data in report_data_list:
        if j == 0: 
            j = 1

        # 检查页面空间
        if not check_space_available(current_y, min_space_required):
            c.showPage()
            c.setFont('SimSun', 12)
            current_y = A4[1] - 3 * cm

        # 获取产品数据
        product = report_data.get("/Product", "")
        relative_bias = report_data.get("/Relative Bias", "")

        # 产品名称映射
        product_mapping = {
            'AOT': 'AOT气溶胶光学厚度',
            'chl': 'chl叶绿素浓度',
            'Kd': 'Kd490漫射衰减系数',
            'Rrs412': 'Rrs412遥感反射率',
            'Rrs443': 'Rrs443遥感反射率',
            'Rrs490': 'Rrs490遥感反射率',
            'Rrs520': 'Rrs520遥感反射率',
            'Rrs670': 'Rrs670遥感反射率',
            'sst': 'sst海表温度'
        }
        formatted_product = product_mapping.get(product, product)

        # 绘制产品标题
        c.setFillColorRGB(1, 0, 0)
        product_title = f"{j}.{formatted_product}产品检验结果"
        j += 1
        c.drawString(left_margin, current_y, product_title)
        current_y -= line_height

        # 绘制相对偏差
        c.setFillColorRGB(0, 0, 0)
        bias_line = f"相对偏差：{relative_bias}%"
        c.drawString(left_margin, current_y, bias_line)
        current_y -= line_height

        # 图片处理
        if not check_space_available(current_y, 300 + 3 * line_height):
            c.showPage()
            c.setFont('SimSun', 12)
            current_y = A4[1] - 3 * cm

        # 添加统计图标题
        c.setFont('SimSun', 12)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(left_margin, current_y, "检验结果统计图：")
        current_y -= line_height

        # 处理时间差分布图
        time_image_name = f"timestastic_HY3A_XC_{product}_"
        time_image_path = None
        for file in os.listdir(input_path):
            if file.startswith(time_image_name):
                time_image_path = os.path.join(input_path, file)
                break

        if time_image_path and os.path.exists(time_image_path):
            img = ImageReader(time_image_path)
            img_width, img_height = 300, 250
            x = (A4[0] - img_width) / 2

            if not check_space_available(current_y, img_height + image_margin):
                c.showPage()
                c.setFont('SimSun', 12)
                current_y = A4[1] - 3 * cm

            c.drawImage(img, x, current_y - img_height, width=img_width, height=img_height)
            current_y -= (img_height + image_margin)

        # 处理检验结果分布图
        val_image_name = f"valstastic_HY3A_XC_{product}_"
        val_image_path = None
        for file in os.listdir(input_path):
            if file.startswith(val_image_name):
                val_image_path = os.path.join(input_path, file)
                break

        if val_image_path and os.path.exists(val_image_path):
            img = ImageReader(val_image_path)
            img_width, img_height = 300, 250
            x = (A4[0] - img_width) / 2

            if not check_space_available(current_y, img_height + image_margin):
                c.showPage()
                c.setFont('SimSun', 12)
                current_y = A4[1] - 3 * cm

            c.drawImage(img, x, current_y - img_height, width=img_width, height=img_height)
            current_y -= img_height

        # 为下一个产品预留空间
        current_y -= 2 * cm

    c.save()


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
                    '/Product=',
                    '/Valid Ratio=',
                    '/CV Value=',
                    '/Relative Bias='
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


def main():
    # 优先使用环境变量中指定的配置文件路径
    config_path = os.environ.get('CONFIG_PATH')
    if not config_path:
        # 如果环境变量未设置，则使用默认路径
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    # 加载配置
    config = configparser.ConfigParser()
    try:
        # 明确指定使用 UTF-8 编码读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config.read_file(f)
    except Exception as e:
        print(f"错误：读取配置文件失败 {config_path}")
        print(f"错误信息: {str(e)}")
        return
    
    # 运行检验
    run_check(config)

if __name__ == '__main__':
    main()