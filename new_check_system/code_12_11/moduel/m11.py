from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader  
from reportlab.lib import colors
import os
import re
import glob


def read_report_data(input_dir):
    report_data_list = []
    
    # 遍历所有report_开头且包含指定产品名的文件
    for f in [f for f in os.listdir(input_dir) if f.startswith("report_")]:
        try:
            with open(os.path.join(input_dir, f), 'r', encoding='utf-8') as file:
                lines = file.readlines()
                report_data = {}
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue  
                    # 分割键值对
                    if '=' in line:
                        key, value = line.split('=', 1)
                        report_data[key] = value
                
                report_data_list.append(report_data)
                # print(f"Read data from {f}: {report_data}")  # 打印读取的数据
                
        except Exception as e:
            print(f"Error reading file {f}: {str(e)}")
            
    return report_data_list


def extract_info_from_filenames(input_dir):
    # 获取目录中的所有文件
    files = os.listdir(input_dir)
    
    # 定义正则表达式模式来匹配文件名中的信息
    pattern = r"report_(\w+)_(\w+)_(\w+)_(\w+)"
    
    # 初始化变量
    satellite_info = None
    source_data = None
    
    # 遍历文件列表
    for file in files:
        match = re.match(pattern, file)
        if match:
            # 提取匹配的组
            satellite_info, source_data, product,time_info = match.groups()
            break  # 假设所有文件的格式一致，只需提取一次即可
    
    return satellite_info, source_data, product ,time_info

def create_satellite_report(input_path, output_dir, font_path,time_size,space_size):
    """
    创建卫星产品检验报告PDF
    """
    # 获取卫星信息和源数据信息
    satellite_info, source_data, product ,time_info = extract_info_from_filenames(input_path)
    satellite_num = satellite_info[2:] if satellite_info.startswith('HY') else 'XX'

    output_file = f"{satellite_info}_{source_data}_{time_info}.pdf"
    output_path = os.path.join(output_dir, output_file)
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建PDF文件
    c = canvas.Canvas(output_path, pagesize=A4)
    
    
    # 设置字体和大小
    pdfmetrics.registerFont(TTFont('SimSun', font_path))

    c.setFont('SimSun', 16)
    
    # 获取页面宽度，用于居中显示
    page_width = A4[0]
    
    # 写入主标题
    title = f"HY-{satellite_num}卫星二级产品检验报告"
    title_width = c.stringWidth(title, 'SimSun', 16)
    x = (page_width - title_width) / 2
    y = A4[1] - 2.5*cm  # 主标题的y坐标
    c.drawString(x, y, title)


    # 设置正文字体大小
    c.setFont('SimSun', 12)

    # 定义左边距和行间距
    left_margin = 2*cm  # 左边距2厘米
    line_height = 0.8*cm  # 行高0.8厘米
    
    # 写入其他信息，从主标题下方2厘米开始
    y_start = y - 2*cm  # 第一行的起始位置
    
    # 准备内容标签
    labels = [
        "待检验卫星：",
        "检验源数据：",
        "时间窗口：",
        "空间窗口：",
        "",  # 空行
        "数据文件匹配情况："
    ]
    
    # 创建源数据映射字典
    source_mapping = {
        'AQUA': 'MODIS-AQUA',
        'TERRA': 'MODIS-TERRA',
        'JPSS': 'VIIRS-JPSS',
        'SNPP': 'VIIRS-SNPP'
    }

    # 转换source_data
    formatted_source = source_mapping.get(source_data, source_data)
    
    # 准备内容值
    values = [
        satellite_info,
        formatted_source,
        f"{str(time_size)}小时",
        f"{str(space_size)}x{str(space_size)}",
        "",  # 空行
        ""   # 数据文件匹配情况暂时不需要值
    ]
#----------------------------------------------------------------------------------#前置行内容
    # 绘制每一行
    for i, (label, value) in enumerate(zip(labels, values)):
        y_position = y_start - (i * line_height)
        
        # 如果是空行，跳过绘制
        if label == "":
            continue

        # 绘制标签（黑色）
        c.setFillColorRGB(0, 0, 0)  # 设置黑色
        c.drawString(left_margin, y_position, label)
        
        # 计算值的起始位置（在标签后面）
        value_x = left_margin + c.stringWidth(label, 'SimSun', 12)
        
        # 如果有值，用红色绘制
        if value:
            c.setFillColorRGB(1, 0, 0)  # 设置红色
            c.drawString(value_x, y_position, value)
#---------------------------------------------------------------------------------------#绘制匹配表格
    
    # 计算表格的起始 y 坐标，确保不与之前的内容重叠
    table_y_start = y_start - len(labels) * line_height - 6.6 * cm  

    # 读取所有 report_ 文件的数据
    report_data_list = read_report_data(input_path)

    # 准备表格数据
    table_data = [["待检验数据", "检验源数据", "时间差（h）"]]

    for report_data in report_data_list:
        hy_file = report_data.get("/HY file", "")
        on_site_file = report_data.get("/On-site file", "")
        time_difference = report_data.get("/Time Difference", "")
        table_data.append([hy_file, on_site_file, time_difference])

    # 创建表格
    table = Table(table_data)

    # 设置表格样式
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 居中对齐
        ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),  # 表头字体
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # 表头底部填充
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # 设置表格网格线为黑色
    ]))

    # 在 PDF 中添加表格
    table.wrapOn(c, A4[0], A4[1])
    table.drawOn(c, left_margin, table_y_start)

#-----------------------------------------------------------------------------------------------------#
    # 在表格绘制完成后，计算新的起始y坐标
    current_y = table_y_start - len(table_data) - 1 * cm  # 减少间距

    # 读取所有report文件的数据
    report_data_list = read_report_data(input_path)

    # 遍历每个report的数据
    j = 0
    for report_data in report_data_list:
        if j == 0: j =1
        # 检查是否需要新页面
        if current_y < 3 * cm:
            c.showPage()
            c.setFont('SimSun', 12)
            current_y = A4[1] - 3 * cm  # 重置y坐标

        # 获取产品名称
        product = report_data.get("/Product", "")
        total_pixel = report_data.get("/Total pixel count", "")
        effective_pixel = report_data.get("/Effective pixel count", "")
        val_pixel = report_data.get("/valresult", "")

        # 创建源数据映射字典
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
        # 转换source_data
        formatted_product = product_mapping.get(product, product)

        # 绘制产品标题
        c.setFillColorRGB(1, 0, 0)  # 红色
        product_title = f"{j}.{formatted_product}产品检验结果"
        j += 1
        c.drawString(left_margin, current_y, product_title)
        
        # 更新y坐标，向下移动
        current_y -=  line_height

        # 绘制像元数据
        c.setFillColorRGB(0, 0, 0)  # 设置黑色
        pixel_data = [
            f"待检验数据总像元数：{total_pixel}",
            f"待检验数据有效像元数：{effective_pixel}",
            f"待检验数据参与检验像元数：{val_pixel}",
            f'检验结果：'
        ]

        # 绘制每行像元数据
        for line in pixel_data:
            c.drawString(left_margin, current_y, line)
            current_y -= line_height


#------------------------------------------------------------------------------------------------#插入第二个表格
        # 获取检验结果数据
        bias = report_data.get("/bias", "")
        std = report_data.get("/STD", "")
        rms = report_data.get("/RMS", "")
        r = report_data.get("/R", "")

        # 准备表格数据
        table2_data = [
            ["bias", bias],
            ["STD", std],
            ["RMS", rms],
            ["R", r]
        ]

        # 创建表格
        table2 = Table(table2_data)

        # 设置表格样式
        table2.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 居中对齐
            ('FONTNAME', (0, 0), (-1, -1), 'SimSun'),  # 字体
            ('GRID', (0, 0), (-1, -1), 1, colors.black),  # 设置表格网格线为黑色
        ]))

        # 在 PDF 中添加表格
        table2.wrapOn(c, A4[0], A4[1])
        table2.drawOn(c, left_margin, current_y - 2 * cm)  # 留出2厘米的间距

        # 更新y坐标
        current_y -= 2.5 * cm
#------------------------------------------------------------------------------------------------#插入图片

        # 检查第一张图片所需空间
        required_space = 300 + 3 * line_height  # 图片高度 + 文字和间距
        if current_y < required_space:
            c.showPage()
            c.setFont('SimSun', 12)
            current_y = A4[1] - 3 * cm

        # 添加"检验结果统计图："文字
        c.setFont('SimSun', 12)
        c.setFillColorRGB(0, 0, 0)  # 黑色
        c.drawString(left_margin, current_y, "检验结果统计图：")

        # 更新y坐标
        current_y -= line_height

        # 构建第一个图片文件名
        map_image_name = f"map_{satellite_info}_{source_data}_{product}_"
        # 查找匹配的图片文件
        map_image_path = None
        for file in os.listdir(input_path):
            if file.startswith(map_image_name):
                map_image_path = os.path.join(input_path, file)
                break

        if map_image_path and os.path.exists(map_image_path):
            # 插入第一张图片
            img = ImageReader(map_image_path)
            img_width = 350  # 设置图片宽度
            img_height = 250  # 设置图片高度
            x = (A4[0] - img_width) / 2  # 居中显示
            c.drawImage(img, x, current_y - img_height, width=img_width, height=img_height)
            
            # 更新y坐标
            current_y -= (img_height + line_height)
            
            # 添加图片文件名（居中）
            filename = os.path.basename(map_image_path)
            filename_width = c.stringWidth(filename, 'SimSun', 12)
            x = (A4[0] - filename_width) / 2
            c.drawString(x, current_y, filename)

        # 检查第二张图片所需空间
        current_y -= 2 * line_height
        required_space = 300 + 3 * line_height  # 图片高度 + 文字和间距
        if current_y < required_space:
            c.showPage()
            c.setFont('SimSun', 12)
            current_y = A4[1] - 3 * cm

        # 构建第二个图片文件名
        pixel_image_name = f"valstastic_{satellite_info}_{source_data}_{product}_"
        # 查找匹配的图片文件
        pixel_image_path = None
        for file in os.listdir(input_path):
            if file.startswith(pixel_image_name):
                pixel_image_path = os.path.join(input_path, file)
                break

        if pixel_image_path and os.path.exists(pixel_image_path):
            # 插入第二张图片
            img = ImageReader(pixel_image_path)
            img_width = 300  # 设置图片宽度
            img_height = 250  # 设置图片高度
            x = (A4[0] - img_width) / 2  # 居中显示
            c.drawImage(img, x, current_y - img_height, width=img_width, height=img_height)
            # 直接更新y坐标到图片底部，不添加额外间距
            current_y -= img_height
            
            # 添加图片文件名（居中）
            filename = os.path.basename(pixel_image_path)
            filename_width = c.stringWidth(filename, 'SimSun', 12)
            x = (A4[0] - filename_width) / 2
            c.drawString(x, current_y, filename)

        # 为下一个产品留出空间
        current_y -= 3 * cm

        # 检查是否需要新页面
        if current_y < 5 * cm:
            c.showPage()
            c.setFont('SimSun', 12)
            current_y = A4[1] - 3 * cm

#------------------------------------------------------------------------------------------------#
        # 在每个产品数据块之间留出额外空间
        # current_y -= 4 * line_height

    c.save()

if __name__ == "__main__":
    time_size = 5
    space_size = 5
    font_path = r"C:\Windows\Fonts\msyhl.ttc"
    output_dir = r"C:\Users\H\Desktop\new_HY_check\code\moduel\temp"
    create_satellite_report(output_dir,output_dir, font_path,time_size,space_size)
