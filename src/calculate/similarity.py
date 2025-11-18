import re
from utils import utils
from utils.logger import setup_logger
import logging
from transformers import AutoTokenizer, AutoModel
from pathlib import Path
import inspect
import os
import editdistance
from datetime import datetime
import torch

class SimilarityCalculator:
    """代码相似度和复杂度计算器"""
    
    def __init__(self):
        # Load小一点的模型 加载时间会更短
        self.logger_info = setup_logger("SimilarityCalculator", logging.INFO)
        self.logger_error = setup_logger("SimilarityCalculator", logging.ERROR)
        self.embedding_model_name = "Qwen2.5-Coder-0.5B"
        self.tokenizer_path = Path("./models/models/Qwen/Qwen2.5-Coder-0.5B") # 注意如果是从外部使用的话 包的路径需要修改
        self.embedding_path = Path("./models/models/Qwen") / self.embedding_model_name
        self.device = torch.device("cuda:7" if torch.cuda.is_available() else "cpu")
        
        # 初始化tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.tokenizer_path,
            local_files_only=True,
            trust_remote_code=True,
        )
        self.logger_info.info(f"成功加载tokenizer: Qwen2.5-Coder-0.5B")
        
    def extract_code_from_predict(self, predict_text, language_type):
        """
        从predict_middle_code中提取代码
        """
        self.logger_info.info(f"{__file__}中 原始预测文本为: {predict_text}")
        if not predict_text:
            return ""
        
        # 匹配TASK_BEGIN到TASK_END之间的内容 re.escape的用途是防止类似于c++的语言被匹配成正则的元符号
        pattern = rf'```{re.escape(language_type)}\s*\[TASK_BEGIN\]([\s\S]*?)\[TASK_END\]\s*```'
        match = re.search(pattern, predict_text)
        if match:
            self.logger_info.info(f"{os.path.basename(__file__)}: 第一次正则匹配(```模式)获取到了代码为{match.group(1).strip()}")
            return match.group(1).strip()
        else:
            self.logger_error.error(f"{os.path.basename(__file__)}: 第一次正则没有获取到代码 当前代码为{predict_text} 将使用第二次[TASK_BEGIN]模式匹配"
            ,exc_info=True)
        
        pattern = rf'\[TASK_BEGIN\]([\s\S]*?)\[TASK_END\]'
        match = re.search(pattern, predict_text)
        if match:
            self.logger_info.info(f"{os.path.basename(__file__)}: 第二次正则匹配([TASK_BEGIN]模式)获取到了代码为{match.group(1).strip()}")
            return match.group(1).strip()
        else:
            self.logger_error.error(f"{os.path.basename(__file__)}: 第二次正则没有获取到代码 当前代码为{predict_text}"
            ,exc_info=True)

        pattern = rf"```{re.escape(language_type)}\s*([\s\S]*?)\s*```"
        match = re.search(pattern, predict_text)
        if match:
            self.logger_info.info(f"{os.path.basename(__file__)}: 第三次正则匹配(没有label模式)获取到了代码为{match.group(1).strip()}")
            return match.group(1).strip()
        else:
            self.logger_error.error(f"{os.path.basename(__file__)}: 第三次正则没有获取到代码 当前代码为{predict_text}"
            ,exc_info=True)
        return None
    

    def calculate_edit_distance(self, true_code, predict_code, language):
        """计算代码分词之后的id数组的编辑距离"""
        true_code_clean = utils.remove_comments(true_code, language)
        predict_code_clean = utils.remove_comments(predict_code, language)
        
        # 使用tokenizer分词
        true_tokens = list(self.tokenizer(true_code_clean, add_special_tokens=False)['input_ids'])
        predict_tokens = list(self.tokenizer(predict_code_clean, add_special_tokens=False)['input_ids'])

        edit_val = editdistance.eval(predict_tokens, true_tokens)
        max_len = max(len(true_tokens), len(predict_tokens))

        return {
            "edit_distance": round((1 - edit_val / max_len) * 100, 4), # predict_tokens越差 edit_distance也应该越差
            "calculate_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "true_code_clean": true_code_clean,
            "predict_code_clean": predict_code_clean
        }

    def calculate_cosine_similarity(self, true_code, predict_code, language):
        """使用embedding信息来计算余弦相似度 ‼️ 未完成 有很多问题"""
        true_code_clean = utils.remove_comments(true_code, language)
        predict_code_clean = utils.remove_comments(predict_code, language)
        
        def get_embedding(code):
            """获取code对应的embedding"""
            inputs = self.tokenizer(
                code,
                return_tensors="pt",
                truncation=True,
                max_length=8192,
                padding=True,
            ).to(self.device)

            with torch.no_grad():
                outputs = self.embedding_model(**inputs)

            embedding = outputs.last_hidden_state.mean(dim=1).squeeze()
            return embedding.cpu()
        true_code_embedding = get_embedding(true_code_clean).to(self.device)
        predict_code_embedding = get_embedding(predict_code_clean).to(self.device)
        cosine_sim = torch.nn.functional.cosine_similarity(true_code_embedding, predict_code_embedding, dim=0)
        return {
            "cosine_similarity": cosine_sim.item(),
            "calculate_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "true_code_clean": true_code_clean,
            "predict_code_clean": predict_code_clean
        }
            

