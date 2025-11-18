"""
指定file_path 以及 languages数组
如果是DeepSeek-R1 file_path应为./bench/(language)/*.jsonl 其中*.jsonl是我要获取的文件后缀
如果不是 file_path应为./result/(language)/similarity/*.josnl
在每个jsonl文件中，都会有多个json字段，我需要你获取它们的["editdistance_info"]["edit_distance"]
然后在字段中还会有["inference_info"]["fill_type"] 分别为class、function、block以及line
我需要的是，对于每一个fill_type，我需要获取它的edit_distance的平均值，当然你需要统计all(edit_distance) / len(edit_distance)
然后绘制柱状图出来，注意图上的所有内容都应该用英文表示
x轴应该是语言类型 每个语言类型有4个柱子对应其fill_type
y轴就是edit_distance 为整数(规范化到0-100)
然后每个柱子的颜色使用LinearSegmentedColormap来控制，我想有蓝、浅红、深白以及浅紫色4种渐变
输出的图片放在./img_result/(model).png下
"""
import json
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from collections import defaultdict
from glob import glob
import argparse

def read_jsonl_data(file_path, is_deepseek_r1=True):
    """读取jsonl文件并提取edit_distance和fill_type数据"""
    data = []
    
    if is_deepseek_r1:
        # DeepSeek-R1: ./bench/(language)/*.jsonl
        pattern = os.path.join(file_path, "*.jsonl")
    else:
        # 其他模型: ./result/(language)/similarity/*.jsonl
        pattern = os.path.join(file_path, "similarity", "*.jsonl")
    
    jsonl_files = glob(pattern)
    
    for file in jsonl_files:
        with open(file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    
                    # 提取edit_distance
                    if "editdistance_info" in item:
                        edit_distance = item["editdistance_info"].get("edit_distance")
                    else:
                        continue
                    
                    # 提取fill_type
                    if "inference_info" in item:
                        fill_type = item["inference_info"].get("fill_type", "")
                        # 标准化fill_type名称
                        if "class" in fill_type.lower():
                            fill_type = "class"
                        elif "function" in fill_type.lower():
                            fill_type = "function"
                        elif "block" in fill_type.lower():
                            fill_type = "block"
                        elif "line" in fill_type.lower():
                            fill_type = "line"
                        else:
                            continue
                    else:
                        continue
                    
                    if edit_distance is not None:
                        data.append({
                            'edit_distance': float(edit_distance),
                            'fill_type': fill_type
                        })
                        
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"第{line_num}行处理出错: {e}")
                    continue
    
    return data

def calculate_averages(data):
    """计算每个fill_type的edit_distance平均值"""
    grouped = defaultdict(list)
    
    for item in data:
        grouped[item['fill_type']].append(item['edit_distance'])
    
    averages = {}
    for fill_type, distances in grouped.items():
        if distances:
            averages[fill_type] = sum(distances) / len(distances)
    
    return averages

def plot_results(language_data, model_name):
    """绘制柱状图"""
    # 定义fill_type顺序和颜色
    fill_types = ['class', 'function', 'block', 'line']
    colors = ['#4472C4', '#E15759', '#00FF00', '#A569BD']  # 蓝、浅红、浅绿、浅紫
    
    # 创建自定义颜色映射
    cmap = LinearSegmentedColormap.from_list('custom', colors, N=4)
    
    languages = list(language_data.keys())
    x = np.arange(len(languages))
    width = 0.2
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 为每个fill_type绘制柱子
    for i, fill_type in enumerate(fill_types):
        values = []
        for lang in languages:
            avg = language_data[lang].get(fill_type, 0)
            # 规范化到0-100
            normalized_avg = min(100, max(0, int(avg)))
            values.append(normalized_avg)
        
        bars = ax.bar(x + i * width, values, width, 
                     label=fill_type.capitalize(), 
                     color=cmap(i/3))
        
        # 在柱子上显示数值
        for bar, value in zip(bars, values):
            if value > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                       f'{value}', ha='center', va='bottom', fontsize=8)
    
    # 设置图表属性
    ax.set_xlabel('Programming Languages', fontsize=12)
    ax.set_ylabel('Edit Distance', fontsize=12)
    ax.set_title(f'{model_name}', fontsize=14)
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(languages, rotation=45, ha='right')
    ax.legend()
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图片
    os.makedirs('./img_result', exist_ok=True)
    plt.savefig(f'./img_result/{model_name}.png', dpi=300, bbox_inches='tight')
    plt.close()


def parse_args():
    parser = argparse.ArgumentParser(description="model arg")
    parser.add_argument("--model", "-model", type=str, default="DeepSeek-R1", help="Inference model")
    args = parser.parse_args()
    return args

def main(model_name):
    # 配置参数
    # model_name = "DeepSeek-R1"  # 可修改为其他模型名
    languages = [
        'c', 'c_sharp', 'cpp', 'go', 'html',  # 5
        'java', 'javascript', 'kotlin', 'lua', 'php', # 5 
        'python', 'r', 'rust', 'scala', 'swift',  # 5
        'typescript', 'verilog', 'zig' # 3
    ]  # 可修改语言列表
    
    # 判断是否为DeepSeek-R1
    is_deepseek_r1 = model_name == "DeepSeek-R1"
    
    language_data = {}
    
    for lang in languages:
        if is_deepseek_r1:
            file_path = f"./bench/{lang}"
        else:
            file_path = f"./result/{lang}/{model_name}"
        
        if os.path.exists(file_path):
            data = read_jsonl_data(file_path, is_deepseek_r1)
            if data:
                averages = calculate_averages(data)
                language_data[lang] = averages
                print(f"{lang}: {averages}")
    
    if language_data:
        plot_results(language_data, model_name)
        print(f"图表已保存到 ./img_result/{model_name}.png")
    else:
        print("未找到有效数据")

if __name__ == "__main__":
    args = parse_args()
    main(args.model)