import json
import os
import sys
from . import config

class ModelManager:
    """
    模型配置
    """
    def __init__(self, config_file=None, model_name="DeepSeek-R1"):
        """
        外部配置json文件从中加载对应model_name的url等关键信息
        """
        if config_file is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(current_dir, "model_config.json")
        self.config_file = config_file
        self.model_name = model_name
        if model_name not in config.MODELS_LIST:
            print(f"__init__ 异常退出 原因是 {model_name} 不在 {config.MODELS_LIST} 中")
            sys.exit(1)
    
    def load_from_file(self):
        """
        从config.json中获取对应的信息 主要是url、if_inference
        返回url与if_inference
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding="utf-8") as f:
                    configs = json.load(f)
                    # print(configs)
                    if self.model_name in configs:
                        url = configs[self.model_name]["url"]
                        if_inference = configs[self.model_name]["if_inference"]
                        return url, if_inference
                    else:
                        print(f"{self.model_name} 不在 {config.MODELS_LIST} 中")
                        return "", False
            except Exception as e:
                print(f"Error loading from file Line 24 {self.config_file}: {e}")
                return "", False
        else:
            print(f"{self.config_file}文件不存在")
            return "", False