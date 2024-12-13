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

# 新增：辅助函数
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
    
    satellite_info = None
    source_data = None
    
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

if __name__ == "__main__":
    time_size = 5
    space_size = 5
    font_path = r"C:\Windows\Fonts\msyhl.ttc"
    output_dir = r"C:\Users\H\Desktop\new_HY_check\code_12_11\moduel\test"
    create_satellite_report(output_dir, output_dir, font_path, time_size, space_size)