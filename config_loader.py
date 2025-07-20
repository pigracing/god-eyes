import tomli
from pathlib import Path

def load_config(path: str = "config.toml") -> dict:
    """加载并解析TOML配置文件"""
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"配置文件 '{path}' 未找到。请根据模板创建它。")

    with open(config_path, "rb") as f:
        try:
            return tomli.load(f)
        except tomli.TOMLDecodeError as e:
            raise ValueError(f"配置文件 '{path}' 格式错误: {e}")