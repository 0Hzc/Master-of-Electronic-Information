import os
import netCDF4 as nc
import numpy as np
import traceback
import re
import pandas as pd
from datetime import timedelta, datetime

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
    
def main():
    input_file_oc = r'C:\Users\18086\Desktop\hzc\input\TERRA_MODIS.20231011T020501.L2.OC.NRT.nc'
    input_file_sst = r'C:\Users\18086\Desktop\hzc\input\TERRA_MODIS.20231011T020501.L2.SST.nc'
    input_file_aop = r'C:\Users\18086\Desktop\hzc\input\AOPRes_NH_TripletAOP_0008_20241114000000.txt'
    input_file_wqp = r'C:\Users\18086\Desktop\hzc\input\WQP_NH_ECO_Triplet_BBFL2W-5776_20241106000000.txt'
    input_file_aot = r'C:\Users\18086\Desktop\hzc\input\AOT_Yantai_CE318TS9_1602_202109170000.txt'
    input_file_ctd = r'C:\Users\18086\Desktop\hzc\input\CTD_NH_PZWY200-2_241021_20241106000000.txt'
    output_dir = r'C:\Users\18086\Desktop\hzc\code_110\moduel\m2test_output'

    process_satellite_check_data(input_file_oc, input_file_sst, output_dir)
    # process_xc_check_data(input_file_aop, input_file_wqp, input_file_aot, input_file_ctd, output_dir)

if __name__ == '__main__':
    main()