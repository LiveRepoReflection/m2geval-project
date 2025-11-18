import glob
import os

import editdistance
import tree_sitter_language_pack as tree_sitter_languages
from utils import utils
import numpy as np
import tqdm
import collections
import transformers
import argparse
from generate_description_by_LLM import generate_description
import inference 
from config import config
import concurrent.futures
from queue import Queue
import threading
import time
from datetime import datetime
import threading
from utils.logger import setup_logger
import logging

# 导入新的子模块
from create.parser_factory import get_parser, traverse_tree, get_definition_name, has_return_statement
from create.sampler_html import HtmlSampler
from create.sampler_code import CodeSampler
from create.skeletons import generate_class_skeleton, generate_function_skeleton
from create.concurrency import (
    get_zero_sampling_count, increment_zero_sampling_count,
    get_failed_attempts, increment_failed_attempts, check_max_failed_attempts
)
from calculate.similarity import SimilarityCalculator

logger_error = None
logger_info = None
thread_local_data = threading.local()
samples_per_repo = 5
calculator = None

# 全局变量申明

def create_samples(repo_root_path, repo_files_content, repo_name, repo_output_path, language, similarity_threshold=50.0, inference_model="deepseek-v3", max_workers=32):
    n_samples = samples_per_repo
    test_data = []
    middle_code_set = set()
    successful_samples = 0
    lock = threading.Lock()  # 用于保护共享资源

    
    def process_single_sample( worker_id):
        """处理单个样本的函数"""
        max_retries = 3
        for retry_count in range(max_retries):
            try:
                # 随机选择文件
                masked_file = np.random.choice(list(repo_files_content.keys()), size=1).tolist()[0]
                code = repo_files_content[masked_file]
                
                print(f"[Worker-{worker_id}] 选择文件: {masked_file.split('/')[-1]}")
                
                # 构建context_code
                context_code = {}
                for file_name in repo_files_content:
                    if file_name != masked_file:
                        new_file_name = file_name.replace(repo_root_path, "")
                        context_code[new_file_name] = repo_files_content[file_name]
                
                # 获取任务点
                print(f"[Worker-{worker_id}] 开始提取任务点... (重试 {retry_count + 1}/{max_retries})")
                return_tuple = None
                if language == "html":
                    html_parser = HtmlSampler()
                    return_tuple = html_parser.sample(code)
                else:
                    code_sampler = CodeSampler()
                    return_tuple = code_sampler.sample(code, language, ratio_list)
                
                if return_tuple is None:
                    print(f"[Worker-{worker_id}] 任务点提取失败: 仓库 {repo_name} 不满足条件 (重试 {retry_count + 1}/{max_retries})")
                    if retry_count == max_retries - 1:  # 最后一次重试
                        increment_failed_attempts()
                        print(f"[Worker-{worker_id}] 达到最大重试次数，全局失败计数: {get_failed_attempts()}")
                        return None, f"仓库 {repo_name} 不满足条件 (已重试{max_retries}次)"
                    continue 
                
                node_type = return_tuple[0]
                if node_type is None:
                    print(f"[Worker-{worker_id}] 任务点提取失败: 节点类型为None (重试 {retry_count + 1}/{max_retries})")
                    if retry_count == max_retries - 1:  # 最后一次重试
                        increment_failed_attempts()
                        print(f"[Worker-{worker_id}] 达到最大重试次数，全局失败计数: {get_failed_attempts()}")
                        return None, f"节点类型为None (已重试{max_retries}次)"
                    continue  # 重试
                
                prefix_code, middle_code, suffix_code = return_tuple[1], return_tuple[2], return_tuple[3]
                print(f"[Worker-{worker_id}] 任务类型: {node_type}")
                
                # 根据不同的节点类型解析返回值
                skeleton = None
                sub_task_type = None
                
                if node_type in ["CLASS_TYPE", "FUNCTION_TYPE"]:
                    # CLASS_TYPE 和 FUNCTION_TYPE 返回 6 个元素: (node_type, prefix, middle, suffix, skeleton, sub_task_type)
                    if len(return_tuple) >= 6:
                        skeleton = return_tuple[4]
                        sub_task_type = return_tuple[5]
                    elif len(return_tuple) >= 5:
                        skeleton = return_tuple[4]
                elif node_type in ["BLOCK_TYPE", "LINE_TYPE"]:
                    # BLOCK_TYPE 和 LINE_TYPE 返回 5 个元素: (node_type, prefix, middle, suffix, sub_task_type)
                    if len(return_tuple) >= 5:
                        sub_task_type = return_tuple[4]
                
                middle_code = utils.remove_comments(middle_code, language) # 去掉注释
                # 验证样本质量 非常重要
                if node_type == "BLOCK_TYPE" and len(middle_code.split('\n')) < 10:
                    logger_error.error(f"[Worker-{worker_id}] 样本质量检查失败: middle_code长度不足 当前代码为 {middle_code}")
                    return None, "middle_code长度小于10，不合格的block测试集"
                elif node_type == "LINE_TYPE" and (len(middle_code.split('\n')) < 5 or len(middle_code) < 10):
                    logger_error.error(f"[Worker-{worker_id}] 样本质量检查失败: line类型不合格 当前代码为 {middle_code}")
                    return None, "middle_code行数小于2或者总字数小于5（比如会有middle_code为单括号的(情况），不合格的line测试集"
                elif node_type == "FUNCTION_TYPE" and len(middle_code.split('\n')) < 10:
                    logger_error.error(f"[Worker-{worker_id}] 样本质量检查失败: function类型不合格 当前代码为 {middle_code}")
                    return None, "middle_code长度小于10，不合格的function测试集"
                elif node_type == "CLASS_TYPE" and len(middle_code.split('\n')) < 10:
                    logger_error.error(f"[Worker-{worker_id}] 样本质量检查失败: class类型不合格 当前代码为 {middle_code}")
                    return None, "middle_code长度小于10，不合格的class测试集"
                elif not middle_code:
                    print(f"[Worker-{worker_id}] 样本质量检查失败: middle_code为空")
                    return None, "middle_code为空"
                
                # 创建样本
                created_sample = {
                    "repo_name": repo_name,
                    "file_name": masked_file.replace(repo_root_path, ""),
                    "inference_info": { # 推理所需要的内容 
                        "prefix_code": prefix_code,
                        "suffix_code": suffix_code,
                        "middle_code": middle_code,
                        "code_description": None,
                        "fill_type": node_type,
                        "language_type": language,
                        "sub_task_type": sub_task_type,
                    },
                    "context_code": context_code,
                    "task_instance_info": {
                        "created_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # 添加创建时间
                        "created_task_model": inference_model # 添加产生该任务点的模型
                    }
                }
                print(f"[Worker-{worker_id}] 创建样本 当前推理的模型为 [{inference_model}]")
                
                # 根据节点类型添加skeleton
                if node_type == "CLASS_TYPE" and skeleton:
                    created_sample["task_instance_info"].update({"class_skeleton": skeleton})
                elif node_type == "FUNCTION_TYPE" and skeleton:
                    created_sample["task_instance_info"].update({"function_skeleton": skeleton})
                
                # 生成代码描述
                print(f"[Worker-{worker_id}] 开始生成代码描述...")
                code_description = generate_description(prefix_code, middle_code, suffix_code, context_code, model=inference_model)
                
                created_sample["task_instance_info"]["code_description"] = code_description
                # 计算相关性并排序
                print(f"[Worker-{worker_id}] 开始计算文件相关性...")
                relevance = utils.get_relevance(created_sample, tokenizer, python_path)
                sorted_context_code_files = list(created_sample["context_code"].items())
                sorted_index = np.argsort(relevance)
                sorted_context_code_files = [sorted_context_code_files[index] for index in sorted_index][::-1]
                created_sample["context_code"] = sorted_context_code_files
                
                # 检查样本是否应该被包含（这里包含API调用）
                print(f"[Worker-{worker_id}] 开始API推理和相似度检测...")
                should_include, processed_sample = should_include_sample_async(created_sample, similarity_threshold, inference_model, worker_id)
                
                if should_include:
                    logger_info.info(f"""在{os.path.basename(__file__)} 中 [Worker-{worker_id}] ✅ 样本处理成功，
                        编辑距离: {processed_sample["editdistance_info"].get('edit_distance', 'N/A')}""")
                    return processed_sample, None
                else:
                    logger_error.error(f"在{os.path.basename(__file__)} 中 [Worker-{worker_id}] ❌ 样本被过滤: 相似度过高",exc_info=True)
                    if retry_count == max_retries - 1:  # 最后一次重试
                        return None, f"相似度检测失败 (已重试{max_retries}次)"
                    continue  # 重试                
            except Exception as e:
                logger_error.error(f"在{os.path.basename(__file__)} 中 [Worker-{worker_id}] ❌ 处理样本时出错: {str(e)} (重试 {retry_count + 1}/{max_retries})",exc_info=True)
                if retry_count == max_retries - 1:  # 最后一次重试
                    increment_failed_attempts()
                    return None, f"处理样本时出错: {str(e)} (已重试{max_retries}次)"
                continue  # 重试
        return None, f"达到最大重试次数 {max_retries}"

    def should_include_sample_async(sample_data, similarity_threshold, inference_model, worker_id):
        """
        异步版本的样本检查函数
        Return: 是否采样成功， 采样后的代码
        """
        try:
            print(f"[Worker-{worker_id}] 🤖 开始LLM推理...")
            
            # 执行推理（这是主要的API调用瓶颈）
            inference_code = inference.inference_middle_code(
                prefix_code=sample_data["inference_info"]["prefix_code"], 
                suffix_code=sample_data["inference_info"]["suffix_code"], 
                context_code=sample_data["context_code"], 
                skeleton=sample_data["task_instance_info"].get("function_skeleton") or sample_data["task_instance_info"].get("class_skeleton", ""),  
                code_description=sample_data["inference_info"]["code_description"], 
                task_type=sample_data["inference_info"]["fill_type"], 
                language=sample_data["inference_info"]["language_type"], 
                model=inference_model
            )

            if inference_code is None or len(inference_code) == 0:
                retry_count = getattr(thread_local_data, 'retry_count', 0)
                if retry_count < 3:
                    thread_local_data.retry_count = retry_count + 1
                    return should_include_sample_async(sample_data, similarity_threshold, inference_model, worker_id)
                else:
                    logger_error.error(f"并发过大 LLM后端负载严重 [Worker-{worker_id}] 推理代码为空 ❌",exc_info=True)
                return False, None
            
            print(f"[Worker-{worker_id}] 🤖 LLM推理完成")
            
            # 从推理中拿到预测的代码
            predict_code = calculator.extract_code_from_predict(inference_code, sample_data["inference_info"]["language_type"])
            
            # 计算相似度
            print(f"[Worker-{worker_id}] 📊 开始计算相似度...")

            editdistance_item = calculator.calculate_edit_distance(
                sample_data["inference_info"]["middle_code"], 
                predict_code, 
                language=sample_data["inference_info"]["language_type"]
            )
            # cosine_item = calculator.calculate_cosine_similarity(
            #     sample_data["inference_info"]["middle_code"], 
            #     predict_code, 
            #     language=sample_data["inference_info"]["language_type"]
            # )
            edit_similarity = editdistance_item["edit_distance"] 
            print(f"[Worker-{worker_id}] 📊 相似度计算完成")
            print(f"[Worker-{worker_id}] 📈 编辑距离为 {edit_similarity}%")
            sample_data.update({
                "inference_content": {
                    "inference_model": inference_model,
                    "inference_result": inference_code,
                    "inference_time": datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                }
            })
            if 10 < edit_similarity < similarity_threshold:
                sample_data.update({
                    "editdistance_info": editdistance_item
                })
                return True, sample_data
            else:
                return False, None
                
        except Exception as e:
            logger_error.error(f"在{os.path.basename(__file__)} 中 [Worker-{worker_id}] ❌ 样本检查过程中出现错误: {e}", exc_info=True)
            return False, None
    
    print(f"🚀 开始多线程处理，目标样本数: {n_samples}，线程数: {max_workers}")
    start_time = time.time()
    
    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交更多的任务以确保能获得足够的有效样本
        max_attempts = n_samples * 3  # 尝试3倍的样本数
        
        # 提交所有任务，为每个任务分配worker ID
        future_to_info = {}
        for i in range(max_attempts):
            worker_id = (i % max_workers) + 1  # 分配worker ID (1-based)
            future = executor.submit(process_single_sample, worker_id)
            future_to_info[future] = {'attempt_id': i, 'worker_id': worker_id}
        
        print(f"📋 已提交 {max_attempts} 个处理任务")
        
        completed_tasks = 0
        for future in concurrent.futures.as_completed(future_to_info):
            completed_tasks += 1
            info = future_to_info[future]
            if check_max_failed_attempts():
                    print(f"🛑 全局失败次数达到上限 ({get_failed_attempts()})，停止处理")
                    # 取消剩余任务
                    for remaining_future in future_to_info:
                        if not remaining_future.done():
                            remaining_future.cancel()
                    break
            if successful_samples >= n_samples:
                # 取消剩余的任务
                remaining_count = 0
                for remaining_future in future_to_info:
                    if not remaining_future.done():
                        remaining_future.cancel()
                        remaining_count += 1
                if remaining_count > 0:
                    print(f"🛑 已达到目标样本数，取消剩余 {remaining_count} 个任务")
                break
            
            try:
                result, error = future.result()
                if result is not None:
                    with lock:
                        if successful_samples < n_samples:
                            test_data.append(result)
                            middle_code_set.add(result["inference_info"]["middle_code"].strip())
                            successful_samples += 1
                            
                            print(f"✅ [Worker-{info['worker_id']}] 成功生成第 {successful_samples}/{n_samples} 个样本")
                            print(f"📊 进度: {successful_samples}/{n_samples} ({successful_samples*1.0/n_samples*100:.1f}%), 已完成任务: {completed_tasks}/{max_attempts}")
                            utils.write_jsonl_file(test_data, repo_output_path)
                            print(f"已成功写入第 {successful_samples} 个样本: {result['file_name']}")
                
                else:
                    logger_error.error(f"在{os.path.basename(__file__)} 中 ❌ [Worker-{info['worker_id']}] 样本处理失败: {error}"
                    ,exc_info=True)
                    
            except Exception as e:
                logger_error.error(f"在{os.path.basename(__file__)} 中 ❌ [Worker-{info['worker_id']}] 获取任务结果时出错: {e}"
                ,exc_info=True)
    
    total_time = time.time() - start_time    
    
    # 输出统计信息
    print(f"\n📈 === 处理完成统计 ===")
    print(f"🎯 目标样本数: {n_samples}")
    print(f"✅ 成功生成样本数: {len(test_data)}")
    print(f"🧵 使用线程数: {max_workers}")
    print(f"⏱️  总处理时间: {total_time:.2f}秒")
    print(f"⚡ 平均每样本耗时: {total_time/len(test_data):.2f}秒" if test_data else "⚡ 平均每样本耗时: N/A")
    logger_info.info(f"✅ 成功生成样本数：{len(test_data)} ⏱️  总处理时间: {total_time:.2f}秒")
    
    # 按worker统计
    worker_stats = {}
    for sample in test_data:
        worker_id = sample.get('worker_id', 'Unknown')
        if worker_id not in worker_stats:
            worker_stats[worker_id] = 0
        worker_stats[worker_id] += 1
    
    print(f"\n👥 === Worker统计 ===")
    for worker_id, count in sorted(worker_stats.items()):
        print(f"Worker-{worker_id}: {count} 个样本")
    
    return test_data

def prepare_test_repo_data(repo_root_path, task_level, language="python",  similarity_threshold=50.0, inference_model="deepseek-v3", max_workers=32):
    language = language.lower()
    def is_valid_file(file_name, language):
        if language == 'python':
            if ("tests/" in file_name or "test/" in file_name) or ("evaluate_repo.py" in file_name) or ("setup.py" in file_name) \
                or ("docs/" in file_name) or ("build/" in file_name):
                return False
            return True
        elif language == 'java':
            if ("test/" in file_name or "tests/" in file_name) or ("target/" in file_name) or ("build/" in file_name) \
                or (".gradle/" in file_name) or ("gradle/" in file_name) or ("docs/" in file_name) or ("documentation/" in file_name) \
                    or ("examples/" in file_name) or ("sample/" in file_name) or ("demo/" in file_name) \
                        or ("benchmark/" in file_name) or ("pom.xml" in file_name) or ("build.gradle" in file_name) \
                            or ("settings.gradle" in file_name) or ("gradlew" in file_name) or (".mvn/" in file_name) \
                                or ("mvnw" in file_name):
                return False
            return True
        elif language == 'cpp' or language == 'c++':
            if ("test/" in file_name or "tests/" in file_name) or ("build/" in file_name) or ("cmake-build-" in file_name) \
                or ("CMakeFiles/" in file_name) or ("CMakeCache.txt" in file_name) or ("Makefile" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or ("third_party/" in file_name) or ("external/" in file_name) or ("vendor/" in file_name) \
                                or ("CMakeLists.txt" in file_name) or (".cmake" in file_name) or ("configure" in file_name) \
                                    or ("autogen" in file_name) or (".o" in file_name) or (".so" in file_name) \
                                        or (".a" in file_name) or (".exe" in file_name) or (".dll" in file_name):
                return False
            return True
        elif language == "javascript":
            if ("test/" in file_name or "tests/" in file_name) or ("node_modules/" in file_name) or ("build/" in file_name) \
                or ("dist/" in file_name) or (".next/" in file_name) or ("coverage/" in file_name) or ("docs/" in file_name) \
                    or ("documentation/" in file_name) or ("examples/" in file_name) or ("sample/" in file_name) \
                        or ("demo/" in file_name) or ("benchmark/" in file_name) or ("public/" in file_name) \
                            or ("static/" in file_name) or ("assets/" in file_name) or ("package.json" in file_name) \
                                or ("package-lock.json" in file_name) or ("yarn.lock" in file_name) or ("webpack.config.js" in file_name) \
                                    or (".babelrc" in file_name) or ("tsconfig.json" in file_name) or (".eslintrc" in file_name) \
                                        or (".gitignore" in file_name) or ("README.md" in file_name) or (".env" in file_name):
                return False
            # 过滤掉 .xxx.js 格式的文件（如 .config.js, .test.js 等）
            import os
            base_name = os.path.basename(file_name)
            return False if base_name.startswith('.') else True
        elif language == "typescript":
            if ("test/" in file_name or "tests/" in file_name) or ("node_modules/" in file_name) or ("build/" in file_name) \
                or ("dist/" in file_name) or (".next/" in file_name) or ("coverage/" in file_name) or ("docs/" in file_name) \
                    or ("documentation/" in file_name) or ("examples/" in file_name) or ("sample/" in file_name) \
                        or ("demo/" in file_name) or ("benchmark/" in file_name) or ("public/" in file_name) \
                            or ("static/" in file_name) or ("assets/" in file_name) or ("package.json" in file_name) \
                                or ("package-lock.json" in file_name) or ("yarn.lock" in file_name) or ("webpack.config.js" in file_name) \
                                    or (".babelrc" in file_name) or ("tsconfig.json" in file_name) or (".eslintrc" in file_name) \
                                        or (".gitignore" in file_name) or ("README.md" in file_name) or (".env" in file_name) \
                                            or ("jest.config.js" in file_name) or ("rollup.config.js" in file_name) or ("vite.config.ts" in file_name) \
                                                or (".d.ts" in file_name and "index.d.ts" not in file_name):
                return False
            # 过滤掉 .xxx.ts/.js 格式的配置文件
            import os
            base_name = os.path.basename(file_name)
            return False if base_name.startswith('.') else True
        elif language == "c_sharp" or language == "c-sharp":
            if ("test/" in file_name or "tests/" in file_name) or ("bin/" in file_name) or ("obj/" in file_name) \
                or ("packages/" in file_name) or (".vs/" in file_name) or ("Debug/" in file_name) or ("Release/" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or (".csproj" in file_name) or (".sln" in file_name) or (".config" in file_name) \
                                or ("packages.config" in file_name) or ("app.config" in file_name) or ("web.config" in file_name) \
                                    or ("AssemblyInfo.cs" in file_name) or ("GlobalAssemblyInfo.cs" in file_name) \
                                        or (".nuspec" in file_name) or (".nupkg" in file_name) or ("nuget.exe" in file_name) \
                                            or (".dll" in file_name) or (".exe" in file_name) or (".pdb" in file_name):
                return False
            return True
        elif language == "php":
            if ("test/" in file_name or "tests/" in file_name) or ("vendor/" in file_name) or ("build/" in file_name) \
                or ("dist/" in file_name) or ("cache/" in file_name) or ("storage/" in file_name) or ("logs/" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or ("public/" in file_name) or ("assets/" in file_name) or ("resources/" in file_name) \
                                or ("composer.json" in file_name) or ("composer.lock" in file_name) or ("package.json" in file_name) \
                                    or (".env" in file_name) or (".htaccess" in file_name) or ("phpunit.xml" in file_name) \
                                        or ("webpack.mix.js" in file_name) or ("artisan" in file_name) or ("server.php" in file_name) \
                                            or ("bootstrap/" in file_name) or ("config/" in file_name) or ("database/" in file_name) \
                                                or (".phpunit.result.cache" in file_name) or (".gitignore" in file_name) or ("README.md" in file_name):
                return False
            return True
        elif language == "go":
            if ("test/" in file_name or "tests/" in file_name) or ("vendor/" in file_name) or ("build/" in file_name) \
                or ("bin/" in file_name) or ("pkg/" in file_name) or (".git/" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or ("testdata/" in file_name) or ("_test.go" in file_name) or ("*_test.go" in file_name) \
                                or ("go.mod" in file_name) or ("go.sum" in file_name) or ("Makefile" in file_name) \
                                    or ("Dockerfile" in file_name) or (".env" in file_name) or ("README.md" in file_name) \
                                        or (".gitignore" in file_name) or ("LICENSE" in file_name) or ("CHANGELOG" in file_name) \
                                            or ("scripts/" in file_name) or ("tools/" in file_name) or ("hack/" in file_name) \
                                                or (".github/" in file_name) or ("deployments/" in file_name) or ("configs/" in file_name):
                return False
            return True
        elif language == "c":
            if ("test/" in file_name or "tests/" in file_name) or ("build/" in file_name) or ("cmake-build-" in file_name) \
                or ("CMakeFiles/" in file_name) or ("CMakeCache.txt" in file_name) or ("Makefile" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or ("third_party/" in file_name) or ("external/" in file_name) or ("vendor/" in file_name) \
                                or ("CMakeLists.txt" in file_name) or (".cmake" in file_name) or ("configure" in file_name) \
                                    or ("autogen" in file_name) or (".o" in file_name) or (".so" in file_name) \
                                        or (".a" in file_name) or (".exe" in file_name) or (".dll" in file_name) \
                                            or ("config.h" in file_name) or ("version.h" in file_name):
                return False
            return True
        elif language == "rust":
            if ("test/" in file_name or "tests/" in file_name) or ("target/" in file_name) or ("build/" in file_name) \
                or ("deps/" in file_name) or (".cargo/" in file_name) or ("vendor/" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or ("benches/" in file_name) or ("fixtures/" in file_name) or ("testdata/" in file_name) \
                                or ("Cargo.toml" in file_name) or ("Cargo.lock" in file_name) or ("build.rs" in file_name) \
                                    or (".gitignore" in file_name) or ("README.md" in file_name) or ("LICENSE" in file_name) \
                                        or ("CHANGELOG" in file_name) or (".github/" in file_name) or ("scripts/" in file_name) \
                                            or ("tools/" in file_name) or ("ci/" in file_name) or ("docker/" in file_name):
                return False
            return True
        elif language == "r":
            if ("test/" in file_name or "tests/" in file_name) or ("build/" in file_name) or ("dist/" in file_name) \
                or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                    or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                        or ("vignettes/" in file_name) or ("inst/" in file_name) or ("man/" in file_name) \
                            or ("data/" in file_name) or ("data-raw/" in file_name) or (".Rproj" in file_name) \
                                or ("DESCRIPTION" in file_name) or ("NAMESPACE" in file_name) or ("NEWS" in file_name) \
                                    or (".Rhistory" in file_name) or (".RData" in file_name) or (".Ruserdata" in file_name) \
                                        or ("packrat/" in file_name) or ("renv/" in file_name) or (".gitignore" in file_name) \
                                            or ("README.md" in file_name) or ("LICENSE" in file_name) or ("CHANGELOG" in file_name):
                return False
            return True
        elif language == "ruby":
            if ("test/" in file_name or "tests/" in file_name) or ("spec/" in file_name) or ("build/" in file_name) \
                or ("tmp/" in file_name) or ("log/" in file_name) or ("vendor/" in file_name) or ("bundle/" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or ("coverage/" in file_name) or (".bundle/" in file_name) or ("node_modules/" in file_name) \
                                or ("Gemfile" in file_name) or ("Gemfile.lock" in file_name) or ("Rakefile" in file_name) \
                                    or (".gemspec" in file_name) or ("config.ru" in file_name) or (".rspec" in file_name) \
                                        or (".rubocop.yml" in file_name) or (".gitignore" in file_name) or ("README.md" in file_name) \
                                            or ("LICENSE" in file_name) or ("CHANGELOG" in file_name) or (".env" in file_name) \
                                                or ("db/migrate/" in file_name) or ("public/" in file_name) or ("assets/" in file_name):
                return False
            return True
        elif language == "scala":
            if ("test/" in file_name or "tests/" in file_name) or ("target/" in file_name) or ("build/" in file_name) \
                or ("project/" in file_name) or (".bloop/" in file_name) or (".metals/" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or ("build.sbt" in file_name) or ("build.sc" in file_name) or ("project/build.properties" in file_name) \
                                or (".gitignore" in file_name) or ("README.md" in file_name) or ("LICENSE" in file_name) \
                                    or ("CHANGELOG" in file_name) or (".github/" in file_name) or ("scripts/" in file_name) \
                                        or ("conf/" in file_name) or ("resources/" in file_name) or (".scalafmt.conf" in file_name) \
                                            or ("metals.sbt" in file_name) or (".scalafix.conf" in file_name):
                return False
            return True
        elif language == "kotlin":
            if ("test/" in file_name or "tests/" in file_name) or ("build/" in file_name) or ("target/" in file_name) \
                or (".gradle/" in file_name) or ("gradle/" in file_name) or ("docs/" in file_name) \
                    or ("documentation/" in file_name) or ("examples/" in file_name) or ("sample/" in file_name) \
                        or ("demo/" in file_name) or ("benchmark/" in file_name) or ("build.gradle" in file_name) \
                            or ("settings.gradle" in file_name) or ("gradlew" in file_name) or (".idea/" in file_name) \
                                or (".gitignore" in file_name) or ("README.md" in file_name) or ("LICENSE" in file_name) \
                                    or ("app/" in file_name and "build/" in file_name) or ("kapt/" in file_name):
                return False
            return True
        elif language == "perl":
            if ("test/" in file_name or "tests/" in file_name) or ("build/" in file_name) \
                or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                    or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                        or (".t" in file_name) or ("Makefile.PL" in file_name) or ("Build.PL" in file_name) \
                            or (".gitignore" in file_name) or ("README.md" in file_name) or ("LICENSE" in file_name):
                return False
            return True
        elif language == "swift":
            if ("test/" in file_name or "tests/" in file_name) or ("build/" in file_name) or (".build/" in file_name) \
                or ("DerivedData/" in file_name) or ("Pods/" in file_name) or ("Carthage/" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or ("fastlane/" in file_name) or (".swiftpm/" in file_name) or ("xcuserdata/" in file_name) \
                                or ("Package.swift" in file_name) or ("project.pbxproj" in file_name) or (".xcworkspace" in file_name) \
                                    or (".xcodeproj" in file_name) or ("Podfile" in file_name) or ("Cartfile" in file_name) \
                                        or (".gitignore" in file_name) or ("README.md" in file_name) or ("LICENSE" in file_name) \
                                            or ("CHANGELOG" in file_name) or (".github/" in file_name) or ("scripts/" in file_name) \
                                                or ("tools/" in file_name) or ("ci/" in file_name) or ("docker/" in file_name) \
                                                    or ("Tests/" in file_name) or ("TestPlans/" in file_name) or ("UITests/" in file_name):
                return False
            return True
        elif language == "zig":
            if ("test/" in file_name or "tests/" in file_name) or ("zig-cache/" in file_name) or ("zig-out/" in file_name) \
                or ("build/" in file_name) or (".zig-cache/" in file_name) or ("target/" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or ("vendor/" in file_name) or ("deps/" in file_name) or ("lib/" in file_name and "test" in file_name) \
                                or ("build.zig" in file_name) or ("build.zig.zon" in file_name) or (".gitignore" in file_name) \
                                    or ("README.md" in file_name) or ("LICENSE" in file_name) or ("CHANGELOG" in file_name) \
                                        or (".github/" in file_name) or ("scripts/" in file_name) or ("tools/" in file_name) \
                                            or ("ci/" in file_name) or ("docker/" in file_name) or ("gyro.zzz" in file_name) \
                                                or ("zigmod.yml" in file_name) or ("zigmod.lock" in file_name):
                return False
            return True
        elif language == "verilog":
            if ("test/" in file_name or "tests/" in file_name) or ("tb/" in file_name or "testbench/" in file_name) \
                or ("sim/" in file_name or "simulation/" in file_name) or ("build/" in file_name) \
                    or ("work/" in file_name) or ("modelsim/" in file_name) or ("vivado/" in file_name) \
                        or ("quartus/" in file_name) or ("synopsys/" in file_name) or ("cadence/" in file_name) \
                            or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                                or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                                    or ("scripts/" in file_name) or ("tools/" in file_name) or ("utils/" in file_name) \
                                        or (".gitignore" in file_name) or ("README.md" in file_name) or ("LICENSE" in file_name) \
                                            or ("CHANGELOG" in file_name) or (".github/" in file_name) or ("Makefile" in file_name) \
                                                or ("*.do" in file_name) or ("*.tcl" in file_name) or ("*.sdc" in file_name) \
                                                    or ("*.xdc" in file_name) or ("*.ucf" in file_name) or ("*.qsf" in file_name) \
                                                        or ("_tb." in file_name) or ("_test." in file_name) or ("testbench_" in file_name):
                return False
            return True
        elif language == "lua":
            if ("test/" in file_name or "tests/" in file_name) or ("spec/" in file_name) or ("build/" in file_name) \
                or ("dist/" in file_name) or ("out/" in file_name) or ("target/" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or ("vendor/" in file_name) or ("lib/" in file_name and "test" in file_name) \
                                or ("rocks/" in file_name) or (".luarocks/" in file_name) \
                                    or ("rockspec" in file_name) or (".rockspec" in file_name) \
                                        or ("Makefile" in file_name) or ("makefile" in file_name) \
                                            or (".gitignore" in file_name) or ("README.md" in file_name) or ("LICENSE" in file_name) \
                                                or ("CHANGELOG" in file_name) or (".github/" in file_name) or ("scripts/" in file_name) \
                                                    or ("tools/" in file_name) or ("ci/" in file_name) or ("docker/" in file_name) \
                                                        or ("config/" in file_name) or ("conf/" in file_name) or (".env" in file_name) \
                                                            or ("_test.lua" in file_name) or ("test_" in file_name) or ("spec_" in file_name):
                return False
            return True
        elif language == "html":
            if ("test/" in file_name or "tests/" in file_name) or ("spec/" in file_name) or ("build/" in file_name) \
                or ("dist/" in file_name) or ("out/" in file_name) or ("target/" in file_name) \
                    or ("docs/" in file_name) or ("documentation/" in file_name) or ("examples/" in file_name) \
                        or ("sample/" in file_name) or ("demo/" in file_name) or ("benchmark/" in file_name) \
                            or ("vendor/" in file_name) or ("node_modules/" in file_name) or ("bower_components/" in file_name) \
                                or ("assets/" in file_name) or ("static/" in file_name) or ("public/" in file_name) \
                                    or (".gitignore" in file_name) or ("README.md" in file_name) or ("LICENSE" in file_name) \
                                        or ("CHANGELOG" in file_name) or (".github/" in file_name) or ("scripts/" in file_name) \
                                            or ("tools/" in file_name) or ("ci/" in file_name) or ("docker/" in file_name) \
                                                or ("config/" in file_name) or ("conf/" in file_name) or (".env" in file_name) \
                                                    or ("package.json" in file_name) or ("webpack.config" in file_name) \
                                                        or ("gulpfile" in file_name) or ("gruntfile" in file_name) \
                                                            or ("_test.html" in file_name) or ("test_" in file_name) or ("spec_" in file_name):
                return False
            return True

    repo_names = os.listdir(repo_root_path)
    repo_names.sort()
    print(language)
    
    data = []
    for repo_name in tqdm.tqdm(repo_names):
        if repo_name == "build" or repo_name.startswith("."):
            continue
        # current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        repo_output_path = None
        if args.action == "test":
            repo_output_path = f"./bench/{language}/{repo_name}_{task_level}_bench.jsonl"
        else:
            repo_output_path = f"./train/{language}/{repo_name}_{task_level}_bench.jsonl"
        os.makedirs(os.path.dirname(repo_output_path), exist_ok=True)
        repo_file_names = glob.glob(f"{repo_root_path}/{repo_name}/**/*", recursive=True)
        all_file_names = []
        if language == 'python':
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".py") and is_valid_file(f, language)]
        elif language == 'java':
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".java") and is_valid_file(f, language)]
        elif language in ["cpp", "c++"]:
            header_files = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".h") and is_valid_file(f, language)]
            cpp_files = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".cpp") and is_valid_file(f, language)]
            all_file_names = header_files + cpp_files
        elif language == "javascript":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and (f.endswith(".js") or f.endswith(".jsx")) and is_valid_file(f, language)]
        elif language == "typescript":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and (f.endswith(".ts") or f.endswith(".tsx")) and is_valid_file(f, language)]
        elif language == "c_sharp" or language == "c-sharp":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".cs") and is_valid_file(f, language)]
        elif language == "php":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".php") and is_valid_file(f, language)]
        elif language == "go":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".go") and is_valid_file(f, language)]
        elif language == "c":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and (f.endswith(".c")) and is_valid_file(f, language)]
        elif language == "rust":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".rs") and is_valid_file(f, language)]
        elif language == "r":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and (f.endswith(".R") or f.endswith(".r")) and is_valid_file(f, language)]
        elif language == "ruby":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".rb") and is_valid_file(f, language)]
        elif language == "scala":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".scala") and is_valid_file(f, language)]
        elif language == "kotlin":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and (f.endswith(".kt") or f.endswith(".kts")) and is_valid_file(f, language)]
        elif language == "perl":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and (f.endswith(".pl") or f.endswith(".pm")) and is_valid_file(f, language)]
        elif language == "swift":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".swift") and is_valid_file(f, language)]
        elif language == "zig":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".zig") and is_valid_file(f, language)]
        elif language == "verilog":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and 
                            (f.endswith(".v") or f.endswith(".vh") or f.endswith(".sv") or f.endswith(".svh")) 
                            and is_valid_file(f, language)]
        elif language == "lua":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and f.endswith(".lua") and is_valid_file(f, language)]
        elif language == "html":
            all_file_names = [f for f in repo_file_names if os.path.isfile(f) and (f.endswith(".html") or f.endswith(".htm")) and is_valid_file(f, language)]
        print(f"Loading repo files from {repo_name}...")
        repo_files_content = []
        if language in ["cpp", "c++"]:
            # C++特殊处理：先配对再合并
            repo_files_content = utils.process_cpp_files(all_file_names, repo_root_path)
        else:
            # Python/Java等直接读取
            repo_files_content = utils.safe_read_files(all_file_names)

        print(f"Successfully Loading all {language} files from {repo_name} 包含 {len(repo_files_content)} 个文件")
        if len(repo_files_content) == 0:
            print(f"Error 没有找到任何有效的源代码文件 跳过当前仓库{repo_name}")
            continue
        print(f"正在将文件写入{repo_output_path}")
        samples = create_samples(repo_root_path, repo_files_content, repo_name, repo_output_path, language, similarity_threshold, inference_model, max_workers)
        data.extend(samples)
        print(f"==========================Complete creating f{repo_name} samples==========================")
    statistics_data = collections.defaultdict(int)
    for obj in data:
        statistics_data[obj["inference_info"]["fill_type"]] += 1

def parse_args():
    parser = argparse.ArgumentParser(description="Argument Parser Example")
    parser.add_argument("--repo_root_path", "-repo_root_path", type=str, default="./repos/", help="repo path")
    parser.add_argument("--tokenizer_path", "-tokenizer_path", type=str, default="./models/models/Qwen/Qwen2.5-Coder-1.5B", help="LLM path")
    parser.add_argument("--action", "-action", type=str, default="test", help="action")
    parser.add_argument("--task_level", "-task_level", type=str, default="class", help="Path to output file")
    parser.add_argument("--process_language", "-language", type=str, default="python", help="Path to output file")
    parser.add_argument("--task_intensity", "-intensity", type=str, default="low", help="Path to output file")
    parser.add_argument("--similarity_threshold", "-threshold", type=float, default=50.0, help="相似度阈值")
    parser.add_argument("--inference_model", "-model", type=str, default="deepseek-v3", help="推理模型")
    import os
    parser.add_argument("--max_workers", "-workers", type=int, default=10, help="最大线程数")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    if args.inference_model not in config.MODELS_LIST:
        print(f"当前脚本不支持模型 {args.inference_model} 支持的模型有 {config.MODELS_LIST}")
        import sys
        sys.exit(1)
    calculator = SimilarityCalculator()
    
    
    np.random.seed(1)
    logger_error = setup_logger(args.inference_model, log_level=logging.ERROR)
    logger_info = setup_logger(args.inference_model, log_level=logging.INFO)
    tokenizer = transformers.AutoTokenizer.from_pretrained(args.tokenizer_path, trust_remote_code = True)
    import site
    python_path = site.getsitepackages()[0] # 获取当前python的路径
    ratio_list = [0, 0, 0, 0]
    if args.task_level == "class":
        ratio_list = [1, 0, 0, 0]
    elif args.task_level == "function":
        ratio_list = [0, 1, 0, 0]
    elif args.task_level == "block":
        ratio_list = [0, 0, 1, 0]
    elif args.task_level == "line":
        ratio_list = [0, 0, 0, 1]
    samples_per_repo = 5
    if args.task_intensity == "high":
        samples_per_repo = 100
    prepare_test_repo_data(repo_root_path = args.repo_root_path, task_level = args.task_level, language = args.process_language, similarity_threshold=args.similarity_threshold, inference_model=args.inference_model, max_workers=args.max_workers)