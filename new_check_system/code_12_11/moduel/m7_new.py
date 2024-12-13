import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from scipy.interpolate import griddata
import traceback

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


def main():

    output_dir = r'C:\Users\H\Desktop\new_HY_check\code_12_11\test_m'
    step7(output_dir, output_dir)

if __name__ == "__main__":
    main()