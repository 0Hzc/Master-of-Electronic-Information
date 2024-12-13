import schedule
import time
import subprocess
import configparser
import os
from datetime import datetime, timedelta
import logging

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scheduler.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def run_validation():
    """执行验证程序"""
    try:
        logging.info("开始执行验证程序")
        logging.info("正在准备运行setup.py...")
        
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(__file__)
        
        # 读取schedule配置文件
        schedule_config = configparser.ConfigParser()
        schedule_config_path = os.path.join(current_dir, 'schedule_config.ini')
        schedule_config.read(schedule_config_path, encoding='utf-8')
        
        # 创建临时的code4配置文件
        temp_config_path = os.path.join(current_dir, 'temp_config.ini')
        code4_config = configparser.ConfigParser()
        
        # 复制除[Schedule]之外的所有配置到新的配置文件
        for section in schedule_config.sections():
            if section != 'Schedule':
                code4_config[section] = {}
                for key, value in schedule_config[section].items():
                    code4_config[section][key] = value
        
        # 保存临时配置文件
        with open(temp_config_path, 'w', encoding='utf-8') as f:
            code4_config.write(f)
        
        logging.info("开始运行setup.py程序...")
        
        # 执行code4.py，使用临时配置文件
        script_path = os.path.join(current_dir, 'setup.py')
        env = os.environ.copy()
        env['CONFIG_PATH'] = temp_config_path  # 通过环境变量传递配置文件路径
        
        result = subprocess.run(
            ['python', script_path], 
            capture_output=True, 
            text=True,
            env=env
        )
        
        # 删除临时配置文件
        if os.path.exists(temp_config_path):
            os.remove(temp_config_path)
        
        if result.returncode == 0:
            logging.info("setup.py程序运行完成")
            if result.stdout:
                logging.info(f"输出信息：\n{result.stdout}")
        else:
            logging.error(f"setup.py程序运行失败：\n{result.stderr}")
            
    except Exception as e:
        logging.error(f"执行验证程序时发生错误：{str(e)}")

def load_schedule_config():
    """加载定时配置"""
    try:
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), 'schedule_config.ini')
        
        if not os.path.exists(config_path):
            # 如果配置文件不存在，创建默认配置
            config['Schedule'] = {
                'enabled': 'true',
                'run_time': '00:00',  # 每天运行时间
                'interval_hours': '24'  # 运行间隔（小时）
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            logging.info("已创建默认配置文件")
        
        config.read(config_path, encoding='utf-8')
        return config
        
    except Exception as e:
        logging.error(f"加载配置文件时发生错误：{str(e)}")
        return None

def write_task_info(config, output_dir):
    """写入任务信息到txt文件"""
    try:
        # 获取当前时间作为文件名
        current_time = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = os.path.join(output_dir, f"task_{current_time}.txt")
        
        # 准备写入的内容
        content = []
        content.append(f"任务设定启动时间：{config['Schedule']['run_time']}")
        
        # 添加待检验数据信息
        content.append("\n待检验数据：")
        content.append(f"l2a_file: {config['HY3A']['l2a_file']}")
        content.append(f"l2b_file: {config['HY3A']['l2b_file']}")
        content.append(f"l2c_file: {config['HY3A']['l2c_file']}")
        
        # 根据source_type添加检验源数据信息
        content.append("\n检验源数据：")
        source_type = config['VALIDATION']['source_type']
        if source_type == 'TERRA':
            content.append(f"oc_file: {config['TERRA']['oc_file']}")
            content.append(f"sst_file: {config['TERRA']['sst_file']}")
        
        # 写入文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        logging.info(f"任务信息已写入文件：{filename}")
        
    except Exception as e:
        logging.error(f"写入任务信息时发生错误：{str(e)}")

def main():
    """主函数"""
    setup_logging()
    logging.info("程序启动")
    
    # 加载配置
    config = load_schedule_config()
    if not config:
        logging.error("无法加载配置，程序退出")
        return
    
    # 获取当前时间和设定运行时间
    current_time = datetime.now()
    run_time_str = config['Schedule']['run_time']
    
    # 解析运行时间
    run_hour, run_minute = map(int, run_time_str.split(':'))
    run_time = current_time.replace(hour=run_hour, minute=run_minute, second=0, microsecond=0)
    
    # 如果设定时间已经过去，等待到第二天的这个时间
    if run_time < current_time:
        run_time = run_time + timedelta(days=1)
    
    # 计算需要等待的时间
    wait_time = (run_time - current_time).total_seconds()
    
    logging.info(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"设定运行时间: {run_time_str}")
    logging.info(f"等待 {int(wait_time/60)} 分 {int(wait_time%60)} 秒后开始运行...")
    
    # 等待到设定时间
    time.sleep(wait_time)
    
    try:
        logging.info("=== 开始执行验证任务 ===")
        start_time = datetime.now()
        
        # 直接执行一次验证程序
        run_validation()
        
        # 写入任务信息
        # 确保输出目录存在
        output_dir = config['PATH']['output_dir']
        os.makedirs(output_dir, exist_ok=True)
        
        # 修改write_task_info函数调用，传入输出目录
        write_task_info(config, output_dir)
        
        logging.info("=== 验证任务执行完成 ===")
        end_time = datetime.now()
        duration = end_time - start_time
        minutes = duration.seconds // 60
        seconds = duration.seconds % 60
        logging.info(f"总运行时间: {minutes}分{seconds}秒")
        
    except Exception as e:
        logging.error(f"执行过程中发生错误：{str(e)}")


if __name__ == '__main__':
    main()