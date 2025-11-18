# 特殊的html采样逻辑
import numpy as np
from .parser_factory import get_parser, traverse_tree
from .concurrency import get_zero_sampling_count, increment_zero_sampling_count


class HtmlSampler:
    """HTML 采样策略"""
    
    def __init__(self):
        # HTML特有的标签分类
        self.block_tags = {"div", "section", "article", "header", "footer", "nav", "main", "aside", "form", "table", "ul", "ol", "dl"}
        self.line_tags = {"span", "a", "strong", "em", "b", "i", "u", "small", "mark", "del", "ins", "sub", "sup", "code", "kbd", "samp", "var", "time", "data"}
    
    def sample(self, code, ratio_list=[0, 0, 1, 1]):
        """
        根据语义信息，为html生成2种级别的任务
        
        Args:
            code: HTML代码字符串
            ratio_list: 采样比例列表 [类, 函数, 块, 单行]
            
        Returns:
            tuple: (node_type, prefix, middle, suffix, sub_task_type) 或 None
        """
        code_bytes = bytes(code, "utf8")
        parser = get_parser("html")
        tree = parser.parse(code_bytes)
        root_node = tree.root_node
        all_nodes = list(traverse_tree(root_node))
        
        # 创建带有子类型标记的节点列表
        block_nodes_with_type = []
        line_nodes_with_type = []
        
        for node in all_nodes:
            if node.type == "element":
                # 获取标签名
                tag_name = None
                for child in node.children:
                    if child.type == "start_tag":
                        for grandchild in child.children:
                            if grandchild.type == "tag_name":
                                tag_name = grandchild.text.decode("utf8")
                                break
                        break
                
                if tag_name:
                    if tag_name in self.block_tags:
                        block_nodes_with_type.append((node, tag_name))
                    elif tag_name in self.line_tags:
                        line_nodes_with_type.append((node, tag_name))
        
        multi_level_nodes = [
            [], # 类 - 空列表，HTML不需要
            [], # 函数 - 空列表，HTML不需要
            [x[0] for x in block_nodes_with_type], # 块
            [x[0] for x in line_nodes_with_type]  # 单行
        ]
        
        # 保存子类型映射
        block_subtype_map = {id(x[0]): x[1] for x in block_nodes_with_type}
        line_subtype_map = {id(x[0]): x[1] for x in line_nodes_with_type}
        
        _sampling_ratio = {
            "CLASS_TYPE": 0,  # HTML不需要类级别
            "FUNCTION_TYPE": 0,  # HTML不需要函数级别
            "BLOCK_TYPE": ratio_list[2] if len(multi_level_nodes[2]) > 0 else 0,
            "LINE_TYPE": ratio_list[3] if len(multi_level_nodes[3]) > 0 else 0
        }
        
        sampling_ratio = np.array(list(_sampling_ratio.values()))
        if sampling_ratio.sum() == 0:
            zero_count = increment_zero_sampling_count()
            print(f"采集样本总和为0 {sampling_ratio} (第{zero_count}次)")
            if zero_count > 100:
                print(f"采集样本总和为0的情况已超过100次，直接返回")
                return None
            return None
        
        sampling_ratio = sampling_ratio / np.sum(sampling_ratio)
        assert len(sampling_ratio) == len(multi_level_nodes)
        chosen_type_idx = np.random.choice(list(range(0, len(multi_level_nodes))), p=list(sampling_ratio), size=1, replace=False)[0]
        chosen_type_nodes = multi_level_nodes[chosen_type_idx]
        chosen_node_types = list(_sampling_ratio.keys())[chosen_type_idx]
        
        masked_node = np.random.choice(chosen_type_nodes, size=1, replace=True)[0]
        
        # 获取子任务类型
        sub_task_type = None
        if chosen_node_types == "BLOCK_TYPE":
            sub_task_type = block_subtype_map.get(id(masked_node))
        elif chosen_node_types == "LINE_TYPE":
            sub_task_type = line_subtype_map.get(id(masked_node))
        
        all_parts = list(traverse_tree(masked_node))
        
        # 选遮盖的区域
        if chosen_node_types == "BLOCK_TYPE":
            if np.random.rand() < 0.8:
                masked_part = masked_node
            else:
                masked_part = np.random.choice(all_parts, size=1, replace=True)[0]
            prefix = code_bytes[: masked_part.start_byte].decode("utf-8")
            middle = code_bytes[masked_part.start_byte : masked_part.end_byte].decode("utf-8")
            suffix = code_bytes[masked_part.end_byte :].decode("utf-8")
            # print(f"被遮盖的部分是 {masked_part} \n 当前的middle code 为{middle}")
            node_type = chosen_node_types
            return (node_type, prefix, middle, suffix, sub_task_type)
        elif chosen_node_types == "LINE_TYPE":
            if np.random.rand() < 0.8:
                masked_part = masked_node
            else:
                masked_part = np.random.choice(all_parts, size=1, replace=True)[0]
            prefix = code_bytes[: masked_part.start_byte].decode("utf-8")
            middle = code_bytes[masked_part.start_byte : masked_part.end_byte].decode("utf-8")
            suffix = code_bytes[masked_part.end_byte :].decode("utf-8")
            # print(f"被遮盖的部分是 {masked_part} \n 当前的middle code 为{middle}")
            node_type = chosen_node_types
            return (node_type, prefix, middle, suffix, sub_task_type)