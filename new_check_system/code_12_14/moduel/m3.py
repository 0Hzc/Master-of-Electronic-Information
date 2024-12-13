import os
import numpy as np
import traceback


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
                    if values[-1] == '1':
                        flag_count += 1
                    else:
                        data_lines.append(line)
                
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
    
def main():
    window_size = 5

    output_test = r'C:\Users\18086\Desktop\hzc\code_110\moduel\m3test_output'

    # HY3A_flag_create(output_test,window_size)
    satellite_flag_create(output_test, 'TERRA',window_size)

if __name__ == '__main__':
    main()