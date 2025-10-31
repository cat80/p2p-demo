import logging
import os
import yaml
import argparse
import logging.config
log = logging.getLogger(__name__)


def deep_merge(source: dict, destination: dict) -> dict:
    """
    深度合并两个字典 (source 合并到 destination)
    """
    for key, value in source.items():
        if isinstance(value, dict) and key in destination and isinstance(destination[key], dict):
            # 递归合并字典
            destination[key] = deep_merge(value, destination[key])
        else:
            # 否则, source 的值直接覆盖 destination 的值
            destination[key] = value
    return destination


def setup_logging(config_path='logging_config.yaml'):
    """
    (1) 自动加载日志配置
    """
    # 确保日志目录存在
    log_dir = "logs"
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            print(f"警告: 无法创建日志目录 {log_dir}. {e}")
    try:
        if not os.path.isfile(config_path):
            # 如果指定日志配置不存在，则查找当前文件config/logging_config.yaml
            current_dir = os.path.dirname(  os.path.abspath(__file__))
            config_path = os.path.join(current_dir,'config/logging_config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            log_config = yaml.safe_load(f.read())
            logging.config.dictConfig(log_config)
        logging.info(f"日志系统配置成功。加载配置:{config_path}")

    except FileNotFoundError:
        logging.basicConfig(level=logging.INFO)
        logging.warning(f"未找到日志配置文件 {config_path}，使用基础配置。")
    except Exception as e:
        logging.basicConfig(level=logging.INFO)
        logging.error(f"加载日志配置失败: {e}，使用基础配置。")


def load_app_config():
    """
    (2) 按你的优先级加载应用配置:
    (A) 命令行 -> (B) 环境配置 -> (C) 基础配置 -> (D) 硬编码
    """

    # (D) 硬编码默认值 (最低优先级)
    config = {
        'p2p': {
            'data_dir': './data_hardcoded',
            'listen_port': 1989,
        }
    }

    # (C) 基础配置 (config/base_config.yaml)
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, 'config/base_config.yaml')

        with open(config_path, 'r', encoding='utf-8') as f:
            base_config = yaml.safe_load(f)
            config = deep_merge(base_config, config)
        logging.info("加载基础配置 (base_config.yaml) 成功。")
    except FileNotFoundError:
        logging.warning("未找到 base_config.yaml，跳过。")

    # --- 开始处理 (A) 命令行 ---
    # 我们需要先解析命令行, 才能知道要加载哪个 (B) 环境配置
    parser = argparse.ArgumentParser(description='My P2P Node')

    # (A.1) 这个参数用来指定加载哪个 (B) 环境配置
    parser.add_argument(
        '--env-config',
        type=str,
        help='(可选) 指定要加载的环境配置文件路径 (例如: config/dev_config.yaml)'
    )

    # (A.2) 这些是最高优先级的具体配置
    parser.add_argument(
        '--data-dir',
        type=str,
        help='(最高优先级) 覆盖数据目录'
    )
    parser.add_argument(
        '--port',
        type=int,
        help='(最高优先级) 覆盖监听端口'
    )

    # 解析命令行参数
    args = parser.parse_args()

    # --- 处理完毕 ---

    # (B) 环境配置 (由 --env-config 指定)
    if args.env_config:
        try:
            with open(args.env_config, 'r', encoding='utf-8') as f:
                env_config = yaml.safe_load(f)
                config = deep_merge(env_config, config)
            logging.info(f"加载环境配置 ({args.env_config}) 成功。")
        except FileNotFoundError:
            logging.error(f"指定的--env-config文件未找到: {args.env_config}")
        except Exception as e:
            logging.error(f"加载--env-config文件失败: {e}")
    else:
        logging.info("未指定 --env-config，跳过环境配置。")

    # (A) 命令行具体配置 (最高优先级覆盖)
    if args.data_dir:
        config['p2p']['data_dir'] = args.data_dir
        logging.info(f"配置被命令行覆盖: data_dir = {args.data_dir}")
    if args.port:
        config['p2p']['listen_port'] = args.port
        logging.info(f"配置被命令行覆盖: listen_port = {args.port}")

    return config

# 在模块加载时，就执行加载配置的操作


# 定义一些常量
MAGIC_BYTES = b'\xab\xcd\xcd\xef' # 定义区块的头

# 初始的代币奖励数量
INITIAL_BLOCK_REWARD = 10 * 100_000_000 # 10个奖励
REWARD_CUTOFF_BLOCKS = 2100000 # 每210万个区块减半

# 难度调整区块数，目前一分钟一个区块，每一周调整一次难度
ADJUSTMENT_INTERVAL = 10080
TARGET_TIMESPAN = 10080 * 60  # 一周的秒数
# INITIAL_BITS = 2083236893 503497599
INITIAL_BITS =  503842407
# 定义区块状态的常量
BLOCK_STATUS_VALID = 1  # 表示区块头和内容都已完全验证
BLOCK_STATUS_FORK = 0 # 表示区块为侧链
BLOCK_STATUS_INVALID = -1 # 表示区块头和内容有为废除区域，一般重组失败后置为无效