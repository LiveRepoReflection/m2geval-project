"""
获取predict_middle_code
"""

import tqdm
from openai import OpenAI
from config import config
import argparse
import re
from utils import utils
import time
import os
from pathlib import Path
import concurrent.futures
import threading
from config import model_manager
import sys
from utils.logger import setup_logger
import logging
import calculate_ed
from datetime import datetime
from inferencepkg.AnthropicSeries import AnthropicRequest


logger_info = setup_logger("DeepSeek-R1", logging.INFO)
logger_error = setup_logger("DeepSeek-R1", logging.ERROR)

def process_single_item(item, language, model, lock, item_index, total_items):
    """
    处理单个数据项的函数
    """
    try:
        # 从JSONL数据中提取字段
        prefix_code = item["inference_info"].get('prefix_code', '')
        middle_code = item["inference_info"].get('middle_code', '')
        suffix_code = item["inference_info"].get('suffix_code', '')
        context_code = item.get('context_code', '')
        skeleton = item["inference_info"].get('class_skeleton', item["inference_info"].get('function_skeleton', "Current task doesn't need skeleton"))
        code_description = item["inference_info"].get('code_description', '')
        language = item["inference_info"].get('language_type', 'python')
        task_type = item["inference_info"].get('fill_type', 'CLASS_TYPE')
        created_task_model = item["task_instance_info"].get('created_task_model', "")
        time.sleep(1)
        # 如果fuzz_similarity_raw不为空，说明已经计算过了，直接返回原始数据
        if created_task_model.lower() == model.lower():
            with lock:
                print(f"第 {item_index+1} 条数据已经计算过，因为推理模型和创建task的模型一致{model, created_task_model}")
            return item, item_index
        else:
            with lock:
                print(f"虽然第 {item_index+1} 条数据计算过，但是当前推理模型{model}与创建任务模型{created_task_model}不同，开始API调用")

        with lock:
            print(f"\n线程开始处理第 {item_index+1}/{total_items} 条数据...")
            print(f"处理的语言是{language}")
        
        # 调用推理函数
        result = inference_middle_code(
            prefix_code=prefix_code,
            suffix_code=suffix_code,
            context_code=context_code,
            skeleton=skeleton,
            code_description=code_description,
            task_type=task_type,
            language=language,
            model=model
        )
        
        # 保存结果
        result_item = item.copy()  # 复制原始数据
        result_item.update({
            "inference_content": {
                "inference_model": model,
                "inference_result": result,
                "inference_time": datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            }
        })
        
        with lock:
            print(f"第 {item_index+1} 条数据处理完成")
        
        return result_item, item_index
        
    except Exception as e:
        with lock:
            print(f"处理第 {item_index+1} 条数据时发生错误: {e}")
            logger_error.error(
                        f"{os.path.basename(__file__)}中 {model} 在 {language} 任务 {task_type} 执行失败: {e}, 异常类型: {type(e).__name__}, 异常详情: {str(e)}\n"
                    ,exc_info=True)
        
        # 即使出错也保存原始数据
        error_item = item.copy()
        error_item['generated_code'] = ''
        error_item['error'] = str(e)
        return error_item, item_index

def process_test_data(test_data, language, output_file, model, max_workers=None):
    """
    多线程处理测试数据，对每条记录进行推理
    """

    if max_workers is None:
        max_workers = os.cpu_count() // 2
    
    print(f"使用 {max_workers} 个线程进行并发处理")
    
    results = [None] * len(test_data)  # 预分配结果列表，保持顺序
    lock = threading.Lock()
    
    # 使用ThreadPoolExecutor进行并发处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_index = {
            executor.submit(process_single_item, item, language, model, lock, i, len(test_data)): i 
            for i, item in enumerate(test_data)
        }
        
        completed_count = 0
        # 处理完成的任务
        for future in concurrent.futures.as_completed(future_to_index):
            try:
                result_item, original_index = future.result()
                results[original_index] = result_item  # 按原始顺序存储结果
                completed_count += 1
                
                with lock:
                    print(f"\n总进度: {completed_count}/{len(test_data)} 条数据已完成")
                
                # 定期保存结果（每处理10条或全部完成时）
                if completed_count % 10 == 0 or completed_count == len(test_data):
                    # 过滤掉None值（未完成的任务）
                    current_results = [r for r in results if r is not None]
                    utils.write_jsonl_file(current_results, output_file)
                    with lock:
                        print(f"已保存 {len(current_results)} 条结果到文件")
                    
            except Exception as e:
                original_index = future_to_index[future]
                with lock:
                    print(f"任务 {original_index+1} 执行失败: {e}")
                    logger_error.error(
                        f"{model} 在 {language} 任务 {original_index+1} 执行失败: {e}, 异常类型: {type(e).__name__}, 异常详情: {str(e)} 输出文件夹为{output_file}\n"
                    ,exc_info=True)

                
                # 创建错误项
                error_item = test_data[original_index].copy()
                error_item['generated_code'] = ''
                error_item['error'] = str(e)
                results[original_index] = error_item
                completed_count += 1
    
    # 过滤掉None值并返回最终结果
    final_results = [r for r in results if r is not None]
    return final_results

def inference_middle_code(prefix_code, suffix_code, context_code, skeleton, code_description, task_type, language="python", model=None, max_input_token=64):
    print(f"当前处理的语言为 {language}")
    system_prompt = f"""
            As a {language} code generation expert, you will receive:
            1. prefix_code - Code preceding the target segment
            2. suffix_code - Code following the target segment  
            3. [TASK_DESCRIPTION] - Functional requirements for the target code

            **Execute precisely**:
            1. Analyze the complete program flow (prefix + suffix)
            2. Generate ONLY the code fulfilling [TASK_DESCRIPTION]
            3. Pay attention to your output format, EXCLUSIVELY in this format, like markdown syntax:
            4. If task is about class or function, there will be a skeleton, your code must obey the skeleton.
            ```{language}
            [TASK_BEGIN]
            {{generated_code}}
            [TASK_END]
            ```
            I WILL USE RE MATCH, IF DON'T MATCH WITH FORMAT ABOVE, YOUR ANSWER IS WRONG!!!
    """

    user_prompt = f"""
    {task_type}
    

    Current File:
    ```{language}
    {prefix_code}
    [TASK_START]

    [TASK_DESCRIPTION {code_description}]

    [SKELETON {skeleton}]

    [TASK_END]
    {suffix_code}
    ```

    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    if "o1" in model.lower():
        # o1不支持system
        messages = [
            {"role": "user", "content": f"{system_prompt} \n\n {user_prompt}"}
        ]

    apikey, base_url = config.CLOSED_API, None
    modelManager = model_manager.ModelManager(model_name=model)
    base_url, if_inference = modelManager.load_from_file()

    # # 使用Anthropic客户端
    # if "claude" in model.lower() or "anthropic" in model.lower():
    #     response = AnthropicRequest(model, apikey, [{"role": "user", "content": f"{system_prompt} \n\n {user_prompt}"}])
    #     return response


    # 使用OpenAI客户端
    client = OpenAI(api_key=apikey, base_url=base_url)
    inference_answer = ""
    if "Qwen3" in model:
        import re
        match_pattern = r"Qwen3-[1-9]\d*B-Chat"
        if re.match(match_pattern, model):
            if_inference = False
            print(f"目前测试{model}的非思考模式 需要再user_prompt后面加上 \\nothink")
            user_prompt += " \\nothink"
    print(f"{model} 开始输出")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            timeout=60,
            stream=True
        )
        print("模型开始输出推理答案")
        for chunk in response:
            if not chunk.choices or not chunk.choices[0].delta:
                continue
            delta = chunk.choices[0].delta
            if delta.content is not None:
                inference_answer += delta.content
                # print(delta.content, end="", flush=True)
            # 检查是否完成
            if chunk.choices[0].finish_reason:
                print(f"\n\n已完成 完成原因 {chunk.choices[0].finish_reason}")
                break
    except Exception as e:
        print(f"{model} API调用失败 {e}")
        logger_error.error(
                    f"{model} 在 {__file__}的 {language} 任务 {task_type}  执行失败: {e}, 异常类型: {type(e).__name__}, 异常详情: {str(e)}\n"
                ,exc_info=True)
    return inference_answer.split("</think>")[-1].strip()

def parse_args():
    parser = argparse.ArgumentParser(description="Argument Parser Example")
    parser.add_argument("--language", "-language", type=str, default="python", help="Process Language")
    parser.add_argument("--model", "-model", type=str, default="deepseek-v3", help="Inference model")
    parser.add_argument("--max-workers", "-max-workers", type=int, default=os.cpu_count() // 2, 
                       help=f"Maximum number of worker threads (default: {os.cpu_count() // 2})")
    parser.add_argument("--max_input_token", "-max_input_token", type=int, default=64, 
                       help="Maximum input token limit in K (default: 64, will be multiplied by 1024)")
    args = parser.parse_args()
    return args

def parse_code(inference_result, language) -> str:
    """
    解析中间的代码并返回
    匹配 ``` [code] ``` 格式，从第二行开始返回代码
    """
    pattern = rf'```{re.escape(language)}\s*\[TASK_BEGIN\]([\s\S]*?)\[TASK_END\]\s*```'
    match = re.search(pattern, inference_result)
    if match:
        logger_info.info(f"{os.path.basename(__file__)}: 第一次正则匹配(```模式)获取到了代码为{match.group(1).strip()}")
        return match.group(1).strip()
    else:
        logger_error.error(f"{os.path.basename(__file__)}: 没有获取到代码 当前代码为{inference_result} 将使用第二次[TASK_BEGIN]模式匹配"
        ,exc_info=True)
    
    pattern = rf'\[TASK_BEGIN\]([\s\S]*?)\[TASK_END\]'
    match = re.search(pattern, inference_result)
    if match:
        logger_info.info(f"{os.path.basename(__file__)}: 第二次正则匹配([TASK_BEGIN]模式)获取到了代码为{match.group(1).strip()}")
        return match.group(1).strip()
    else:
        logger_error.error(f"{os.path.basename(__file__)}: 没有获取到代码 当前代码为{inference_result}"
        ,exc_info=True)

    pattern = rf'```{re.escape(language)}\s*([\s\S]*?)\s*```'
    match = re.search(pattern, inference_result)
    if match:
        logger_info.info(f"{os.path.basename(__file__)}: 第三次正则匹配(直接```模式)获取到了代码为{match.group(1).strip()}")
        return match.group(1).strip()
    else:
        logger_error.error(f"{os.path.basename(__file__)}: 没有获取到代码 当前代码为{inference_result}"
        ,exc_info=True)
    return None


def get_output_path(input_file_path, language, model):
    """
    根据输入文件路径生成输出文件路径
    例如: ./bench/python/sqlparse_class.jsonl -> ./result/python/{model}/inference/sqlparse_class_result.jsonl
    """
    input_path = Path(input_file_path)
    filename = input_path.stem  # 获取不带扩展名的文件名
    
    # 创建输出目录路径
    output_dir = Path(f"./result/{language}/{model}/inference")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成输出文件名
    output_filename = f"{filename}_inference_result.jsonl"
    return str(output_dir / output_filename)

if __name__ == '__main__':

    args = parse_args()
    language = args.language.lower()
    model = args.model
    max_workers = args.max_workers

    logger_error = setup_logger(model, logging.ERROR)
    logger_info = setup_logger(model, logging.INFO)
    
    if model not in config.MODELS_LIST:
        import sys
        print("当前模型不在测试列表中")
        sys.exit(1)
    
    print(f"配置信息: 语言={language}, 模型={model}, 最大线程数={max_workers}")
    
    input_path = f"./bench/{language}/"
    
    # 扫描所有.jsonl文件
    jsonl_files = utils.scan_jsonl_files(input_path)
    
    if not jsonl_files:
        print(f"在 {input_path} 中没有找到 .jsonl 文件")
        exit(1)
    
    print(f"找到 {len(jsonl_files)} 个 .jsonl 文件: {jsonl_files}")
    
    # 处理每个文件 但目前还是单线程处理一个文件 所以还是很慢
    for jsonl_file in tqdm.tqdm(jsonl_files):
        # 添加日志记录功能
        
        # 读取测试数据
        test_data = utils.read_jsonl_file(jsonl_file)
        if not test_data:
            print(f"文件 {jsonl_file} 没有有效数据，跳过")
            continue
        
        # 生成输出路径
        output_path = get_output_path(jsonl_file, language, model)
        print(f"输出路径: {output_path}")
        logger_info.info(f"正在处理文件 {jsonl_file} 输出路径为 {output_path}")
        # 多线程处理测试数据
        print(f"开始多线程处理 {len(test_data)} 条测试数据...")
        results = process_test_data(test_data, language=language, output_file=output_path, max_workers=max_workers, model=model)
        
        # 保存最终结果
        print(f"正在保存最终结果到: {output_path}")
        utils.save_results_to_jsonl(results, output_path)
        print(f"文件 {jsonl_file} 处理完成！")
    
    print("\n所有文件处理完成！")