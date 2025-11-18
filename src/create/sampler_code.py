# 代码采样逻辑
import numpy as np
import tree_sitter_language_pack as tree_sitter_languages
from utils import utils
from .parser_factory import get_parser, traverse_tree
from .concurrency import increment_zero_sampling_count
from .skeletons import generate_class_skeleton, generate_function_skeleton


class CodeSampler:
    """代码采样策略"""
    
    def __init__(self):
        pass
    
    def sample(self, code, language="python", ratio_list=[0, 0, 1, 1]):
        """
        根据语义信息，生成四种级别的任务：类、函数、块以及单语句
        
        Args:
            code: 代码字符串
            language: 编程语言
            ratio_list: 采样比例列表 [类, 函数, 块, 单行]
            
        Returns:
            tuple: (node_type, prefix, middle, suffix, skeleton, sub_task_type) 或 None
        """
        language = language.lower()
        code_bytes = bytes(code, "utf8")
        
        if language == "c++":
            language = "cpp"
        elif language == "c#" or "sharp" in language:
            language = "c_sharp"
        elif language == "html":
            # HTML 由专门的 HtmlSampler 处理
            from .sampler_html import HtmlSampler
            html_sampler = HtmlSampler()
            return html_sampler.sample(code, ratio_list)
        
        tree = None
        if language == "c_sharp":
            import tree_sitter_c_sharp as tscsharp
            from tree_sitter import Language, Parser
            CSHARP_LANGUAGE = Language(tscsharp.language())
            parser = Parser(CSHARP_LANGUAGE)
            tree = parser.parse(code_bytes)
        else:
            parser = tree_sitter_languages.get_parser(language)
            tree = parser.parse(code_bytes)
        
        root_node = tree.root_node
        all_nodes = list(traverse_tree(root_node))
        
        # 节点分类
        import_nodes = []
        comment_nodes = []
        return_statement_nodes = []
        if_statement_nodes = []
        for_statement_nodes = []
        while_statement_nodes = []
        class_nodes = []
        function_nodes = []
        assignment_nodes = []
        expression_nodes = []
        
        node_types = utils.language_symbols[language]
        for child in all_nodes:
            if child.type in node_types["IMPORT_TYPE"]:
                import_nodes.append(child)
            elif child.type in node_types["COMMENT_TYPE"]:
                comment_nodes.append(child)
            elif child.type in node_types["IF_STATEMENT_TYPE"]:
                if_statement_nodes.append(child)
            elif child.type in node_types["FOR_STATEMENT_TYPE"]:
                for_statement_nodes.append(child)
            elif child.type in node_types["WHILE_STATEMENT_TYPE"]:
                while_statement_nodes.append(child)
            elif child.type in node_types["RETURN_STATEMENT_TYPE"]:
                return_statement_nodes.append(child)
            elif child.type in node_types["EXPRESSION_STATEMENT_TYPE"]:
                expression_nodes.append(child)
            elif child.type in node_types["ASSIGNMENT_STATEMENT_TYPE"]:
                assignment_nodes.append(child)
            elif child.type in node_types["CLASS_TYPE"]:
                class_nodes.append(child)
            elif child.type in node_types["FUNCTION_TYPE"]:
                function_nodes.append(child)
        
        # 创建带有子类型标记的节点列表
        block_nodes_with_type = []
        for node in for_statement_nodes:
            block_nodes_with_type.append((node, "for_statement"))
        for node in if_statement_nodes:
            block_nodes_with_type.append((node, "if_statement"))
        for node in while_statement_nodes:
            block_nodes_with_type.append((node, "while_statement"))
        for node in import_nodes:
            block_nodes_with_type.append((node, "import"))
        
        line_nodes_with_type = []
        for node in assignment_nodes:
            line_nodes_with_type.append((node, "assignment"))
        for node in expression_nodes:
            line_nodes_with_type.append((node, "expression"))
        for node in return_statement_nodes:
            line_nodes_with_type.append((node, "return_statement"))
        
        multi_level_nodes = [
            class_nodes,  # 类
            function_nodes,  # 函数
            [x[0] for x in block_nodes_with_type],  # 块 - 只保留节点用于兼容性
            [x[0] for x in line_nodes_with_type]   # 单行 - 只保留节点用于兼容性
        ]
        
        # 保存子类型映射
        block_subtype_map = {id(x[0]): x[1] for x in block_nodes_with_type}
        line_subtype_map = {id(x[0]): x[1] for x in line_nodes_with_type}
        
        _sampling_ratio = {
            "CLASS_TYPE": ratio_list[0] if len(multi_level_nodes[0]) > 0 else 0,
            "FUNCTION_TYPE": ratio_list[1] if len(multi_level_nodes[1]) > 0 else 0,
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
        # assert len(sampling_ratio) == len(multi_level_nodes)
        chosen_type_idx = np.random.choice(list(range(0, len(multi_level_nodes))), p=list(sampling_ratio), size=1, replace=False)[0]
        chosen_type_nodes = multi_level_nodes[chosen_type_idx]
        chosen_node_types = list(_sampling_ratio.keys())[chosen_type_idx]  # 选出的节点类别
        
        masked_node = np.random.choice(chosen_type_nodes, size=1, replace=True)[0]
        
        # 获取子任务类型
        sub_task_type = None
        if chosen_node_types == "BLOCK_TYPE":
            sub_task_type = block_subtype_map.get(id(masked_node))
        elif chosen_node_types == "LINE_TYPE":
            sub_task_type = line_subtype_map.get(id(masked_node))
        
        all_parts_code = code_bytes[masked_node.start_byte : masked_node.end_byte].decode("utf-8")
        all_parts_code = utils.remove_comments(all_parts_code, language)
        all_parts = list(traverse_tree(masked_node))
        
        # 对于不同的TYPE进行处理
        if chosen_node_types == "CLASS_TYPE":
            # 要处理类骨架 对于类而言 还得返回一下骨架
            masked_part = masked_node
            masked_code = code_bytes[masked_part.start_byte: masked_part.end_byte].decode("utf-8")
            skeleton = generate_class_skeleton(masked_code, language, masked_node=masked_node, all_codes=code_bytes)  # 生成类骨架 待生成
            if skeleton == None:  # 空类
                return None
            # print(f"被遮盖住的部分是 {masked_code} 当前遮盖部分类的骨架是 {skeleton}")
            prefix = code_bytes[: masked_part.start_byte].decode("utf-8")
            middle = code_bytes[masked_part.start_byte : masked_part.end_byte].decode("utf-8")
            suffix = code_bytes[masked_part.end_byte :].decode("utf-8")
            node_type = chosen_node_types
            return (chosen_node_types, prefix, middle, suffix, skeleton, sub_task_type)
        elif chosen_node_types == "FUNCTION_TYPE":
            # 处理函数骨架
            masked_part = masked_node
            masked_code = code_bytes[masked_part.start_byte: masked_part.end_byte].decode("utf-8")
            skeleton = generate_function_skeleton(masked_code, masked_node=masked_node, language=language, all_codes=code_bytes)  # 生成函数骨架 待生成
            if skeleton is None:
                return None
            # print(f"被遮盖住的部分是 {masked_code} \n 当前遮盖部分函数的骨架是 {skeleton}")
            prefix = code_bytes[: masked_part.start_byte].decode("utf-8")
            middle = code_bytes[masked_part.start_byte : masked_part.end_byte].decode("utf-8")
            suffix = code_bytes[masked_part.end_byte :].decode("utf-8")
            node_type = chosen_node_types
            return (chosen_node_types, prefix, middle, suffix, skeleton, sub_task_type)
        elif chosen_node_types == "BLOCK_TYPE":
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