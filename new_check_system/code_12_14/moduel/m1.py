import os
import h5py
from datetime import timedelta, datetime
import traceback



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
    
def main():
    input_file_l2a = r'C:\Users\H\Desktop\new_HY_check\input\H3A_OPER_OCT_L2A_20231011T022500_20231011T023000_26671_10.h5'
    input_file_l2b = r'C:\Users\H\Desktop\new_HY_check\input\H3A_OPER_OCT_L2B_20231011T022500_20231011T023000_26671_10.h5'
    input_file_l2c = r'C:\Users\H\Desktop\new_HY_check\input\H3A_OPER_OCT_L2C_20231011T022500_20231011T023000_26671_10.h5'
    output_dir = r'C:\Users\H\Desktop\new_HY_check\output'
    process_hy_data(input_file_l2a,input_file_l2b,input_file_l2c, output_dir)

if __name__ == '__main__':
    main()