"""知识提取配置管理器"""
from enum import Enum
from typing import Tuple, List
import langextract as lx


class ConfigType(Enum):
    """配置类型枚举"""
    GENERAL = "general"
    ZIWEI_DOUSHU = "ziwei_doushu"

    @classmethod
    def get_display_name(cls, config_type: "ConfigType") -> str:
        """获取配置类型的显示名称"""
        display_names = {
            cls.GENERAL: "通用文档",
            cls.ZIWEI_DOUSHU: "紫微斗数"
        }
        return display_names.get(config_type, config_type.value)


def get_config(config_type: ConfigType) -> Tuple[str, List[lx.data.ExampleData]]:
    """
    获取指定类型的配置
    
    Args:
        config_type: 配置类型枚举
        
    Returns:
        (prompt, examples) 元组
    """
    if config_type == ConfigType.ZIWEI_DOUSHU:
        from .prompts import ziwei_doushu
        return ziwei_doushu.PROMPT, ziwei_doushu.EXAMPLES
    else:
        from .prompts import general
        return general.PROMPT, general.EXAMPLES
