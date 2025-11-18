import json
import re
import os
from pathlib import Path
from utils import utils
import argparse
from fuzzywuzzy import fuzz
from utils.logger import setup_logger
import logging
from calculate import similarity

logger_info = setup_logger("DeepSeek-R1", logging.INFO)
logger_error = setup_logger("DeepSeek-R1", logging.ERROR)

# 全局相似度计算器实例
calculator = None

def parse_args():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='计算代码相似度')
    parser.add_argument('--language', type=str, required=True, help='编程语言')
    parser.add_argument('--model', type=str, required=True, help='模型')
    return parser.parse_args()

def get_output_path(input_file, language, model):
    """
    生成相似度计算的输出文件路径
    将输出文件夹改为 ./result/{language}/{model}/similarity/
    """
    input_path = Path(input_file)
    
    # 构建新路径: ./result/{language}/{model}/similarity/
    output_dir = Path('./result') / language / model / 'similarity'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 修改文件名
    filename = input_path.stem
    if filename.endswith('_inference_result'):
        new_filename = filename.replace('_inference_result', '_similarity_result')
    else:
        new_filename = f"{filename}_similarity_result"
    
    return output_dir / f"{new_filename}.jsonl"
    

    
def calculate_similarity(input_path: str, output_path: str):
    """
    计算代码相似度的主函数
    """
    results = []
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    # 检查创建task的model和当前的model是否一致
                    created_task_model = data["task_instance_info"]["created_task_model"]
                    if created_task_model.lower() == model.lower(): # 创建task的model和当前model一致就不重新计算
                        print(f"第{line_num}行：已存在相似度数据 并且创建任务的模型{created_task_model}与推理模型{model}一致，跳过计算 ")
                        results.append(data)
                        continue
                    else:
                        print(f"第{line_num}行：即使已存在相似度数据 但是创建任务的模型{created_task_model}与推理模型{model}不一致，需要重新计算相似度 ")

                    
                    # 获取数据
                    true_code = data["inference_info"].get('middle_code')
                    inference_code = data["inference_content"].get("inference_result")
                    language_type = data["inference_info"].get('language_type', 'python')
                    
                    # 步骤1：从predict_middle_code中提取代码
                    predict_code = calculator.extract_code_from_predict(inference_code, language_type)
                    if model == "Qwen3-8B-My-Instruct" or model == "Qwen3-8B-RL-GSPO" or model == "Qwen3-8B-RL-GRPO":
                        predict_code = inference_code
                    if not true_code:
                        print(f"第{line_num}行：true_code 为空，跳过")
                        continue
                    elif not predict_code:
                        print(f"第{line_num}行：predict_code 为空，跳过")
                        continue
                    
                    # 步骤2：计算编辑距离
                    editdistance_result = calculator.calculate_edit_distance(true_code, predict_code, language_type)
                    # 保存原始数据并添加计算结果
                    result = data.copy()
                    result.update({
                        "editdistance_info": editdistance_result
                    })
                    
                    results.append(result)
                    
                    print(f"第{line_num}行处理完成，编辑距离: {editdistance_result['edit_distance']}")
                    
                except json.JSONDecodeError as e:
                    print(f"第{line_num}行JSON解析错误: {e}")
                    continue
                except Exception as e:
                    print(f"第{line_num}行处理出错: {e}")
                    continue
        
        # 保存结果
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        print(f"处理完成，共处理 {len(results)} 条数据，结果保存到: {output_path}")
        
    except FileNotFoundError:
        print(f"输入文件不存在: {input_path}")
    except Exception as e:
        print(f"处理过程中发生错误: {e}")

if __name__ == "__main__":
    args = parse_args()
    language = args.language.lower()
    model = args.model
    input_path = f"./result/{language}/{model}/inference"
    logger_info = setup_logger(model, logging.INFO)
    logger_error = setup_logger(model, logging.ERROR)
    
    # 扫描所有.jsonl文件
    jsonl_files = utils.scan_jsonl_files(input_path)
    calculator = similarity.SimilarityCalculator()
    
    if not jsonl_files:
        print(f"在 {input_path} 中没有找到 .jsonl 文件")
        exit(1)
    
    print(f"找到 {len(jsonl_files)} 个 .jsonl 文件: {jsonl_files}")
    
    # 处理每个文件
    for jsonl_file in jsonl_files:
        print(f"\n正在处理文件: {jsonl_file}")
        
        # 使用get_output_path函数生成输出文件路径
        output_file = get_output_path(jsonl_file, language, model)
        
        print(f"输出路径: {output_file}")
        
        # 计算相似度
        calculate_similarity(jsonl_file, output_file)
        
        print(f"文件 {jsonl_file} 处理完成！")
    
    print("\n所有文件处理完成！")