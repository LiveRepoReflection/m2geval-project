# 树解析器工厂
import tree_sitter_language_pack as tree_sitter_languages
from utils import utils


def traverse_tree(node):
    """遍历语法树节点 非常关键的递归函数"""
    cursor = node.walk()
    depth = 0

    visited_children = False
    while True:
        if not visited_children:
            yield cursor.node
            if not cursor.goto_first_child():
                depth += 1
                visited_children = True
        elif cursor.goto_next_sibling():
            visited_children = False
        elif not cursor.goto_parent() or depth == 0:
            break
        else:
            depth -= 1


def get_definition_name(node, node_types):
    """获取定义名称"""
    for child in node.children:
        if child.type == node_types["IDENTIFIER_TYPE"]:
            return child.text.decode("utf8")


def has_return_statement(node, node_types):
    """检查节点是否包含返回语句"""
    traverse_nodes = traverse_tree(node)
    for node in traverse_nodes:
        if node.type == node_types["RETURN_TYPE"]:
            return True
    return False


def get_parser(language):
    """获取指定语言的解析器"""
    language = language.lower()
    if language == "c++":
        language = "cpp"
    elif language == "c#":
        language = "c_sharp"
    
    if language == "c_sharp":
        try:
            import tree_sitter_c_sharp as tscsharp
            from tree_sitter import Language, Parser
            CSHARP_LANGUAGE = Language(tscsharp.language())
            parser = Parser(CSHARP_LANGUAGE)
            return parser
        except ImportError:
            raise ImportError("C# parser not available")
    else:
        return tree_sitter_languages.get_parser(language)


def get_node_types(language):
    """获取语言的节点类型映射"""
    language = language.lower()
    if language == "c++":
        language = "cpp"
    elif language == "c#":
        language = "c_sharp"
    
    return utils.language_symbols.get(language, {})