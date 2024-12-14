import os
import numpy as np
import traceback

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
    
def main():
    input_path = r'C:\Users\H\Desktop\new_HY_check\output'
    output_path = r'C:\Users\H\Desktop\new_HY_check\code_12_14\moduel\m3test_output'
    # satellite_validation(input_path, output_path)
    xc_validation(output_path, output_path)

if __name__ == '__main__':
    main()
