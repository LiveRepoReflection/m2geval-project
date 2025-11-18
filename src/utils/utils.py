import jsonlines
import glob
import pandas as pd
import os
import math
import multiprocessing as mp
import traceback
import tqdm
import itertools
import re
import collections
import argparse
from pathlib import Path
import json
import numpy as np
import itertools
import gc
import glob
import subprocess
import hashlib
import random
import string
import tree_sitter_language_pack as tree_sitter_languages
import io
import importlib
from fuzzywuzzy import fuzz
language_symbols = {
    "python": {
        "CLASS_TYPE": ["class_definition"],
        "FUNCTION_TYPE": ["function_definition"],
        "IMPORT_TYPE": ["import_statement", "import_from_statement"],
        "IDENTIFIER_TYPE": ["identifier"],
        "ATTRIBUTE_TYPE": ["attribute"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["assignment"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_statement"]
    },
    "java": {
        "CLASS_TYPE": ["class_declaration"],
        "FUNCTION_TYPE": ["method_declaration"],
        "IMPORT_TYPE": ["import_declaration"],
        "IDENTIFIER_TYPE": ["identifier"],
        "ATTRIBUTE_TYPE": ["field_access"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["local_variable_declaration", "field_declaration"],
        "COMMENT_TYPE": ["comment", "line_comment", "block_comment"],
        "IF_STATEMENT_TYPE": ["if_statement", "try_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement", "enhanced_for_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_statement"]
    },
    "cpp": {
        "CLASS_TYPE": ["class_specifier"],
        "FUNCTION_TYPE": ["function_definition"],
        "TEMPLATE_DECLARATION_TYPE": ["template_declaration"],
        "IMPORT_TYPE": ["using_declaration", "namespace_definition", "preproc_include"],
        "IDENTIFIER_TYPE": ["identifier"],
        "ATTRIBUTE_TYPE": ["field_expression", "method_invocation"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement", "declaration"],
        "ASSIGNMENT_STATEMENT_TYPE": ["declaration"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement", "range_based_for_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_statement"],
        "STRUCT_DECLARATION_TYPE": ["struct_specifier"],
        "ENUM_DECLARATION_TYPE": ["enum_specifier"],
    },
    "c_sharp": {
        "CLASS_TYPE": ["class_declaration"],
        "FUNCTION_TYPE": ["method_declaration", "constructor_declaration"],
        "IMPORT_TYPE": ["using_directive"],
        "IDENTIFIER_TYPE": ["identifier"],
        "ATTRIBUTE_TYPE": ["simple_name", "qualified_name"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["local_declaration_statement", "assignment_expression"],
        "COMMENT_TYPE": ["single_line_comment", "multi_line_comment", "documentation_comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement", "foreach_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement", "try_statement", "catch_clause", "finally_clause", "block", "namespace_declaration", "declaration_list"],
        "RETURN_STATEMENT_TYPE": ["return_statement", "throw_statement"]
    },  
    "typescript": {
        "CLASS_TYPE": ["class_declaration"],
        "FUNCTION_TYPE": ["function_declaration", "method_definition"],
        "IMPORT_TYPE": ["import_statement", "import_clause", "import_require_statement"],
        "IDENTIFIER_TYPE": ["identifier"],
        "ATTRIBUTE_TYPE": ["property_access_expression"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["variable_declaration", "variable_statement"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement", "for_of_statement", "for_in_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_statement"],
        "INTERFACE_DECLARATION_TYPE": ["interface_declaration"],
        "ENUM_DECLARATION_TYPE": ["enum_declaration"],
        "TYPE_ALIAS_DECLARATION_TYPE": ["type_alias_declaration"],
        "DECORATOR_TYPE": ["decorator"]
    },
    "javascript": {
        "CLASS_TYPE": ["class_declaration"],
        "FUNCTION_TYPE": ["function_declaration", "arrow_function", "async_function_declaration", "async_arrow_function"],
        "IMPORT_TYPE": ["import_statement", "export_statement"],
        "IDENTIFIER_TYPE": ["identifier"],
        "ATTRIBUTE_TYPE": ["member_expression"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["variable_declaration"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement", "for_in_statement", "for_of_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_statement"],
        "OBJECT_DECLARATION_TYPE": ["object"],
        "ARRAY_DECLARATION_TYPE": ["array"],
        "TEMPLATE_STRING_TYPE": ["template_string"],
    },
    "php": {
        "CLASS_TYPE": ["class_declaration"],
        "FUNCTION_TYPE": ["function_definition", "method_declaration"],
        "IMPORT_TYPE": ["use_declaration", "use_statement"],
        "IDENTIFIER_TYPE": ["name"],
        "ATTRIBUTE_TYPE": ["property_declaration"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["assignment_expression"],
        "COMMENT_TYPE": ["comment", "_comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_statement"]
    },
    "go": {
        "CLASS_TYPE": ["type_declaration", "struct_type", "interface_type"],
        "FUNCTION_TYPE": ["function_declaration", "method_declaration"],
        "IMPORT_TYPE": ["import_declaration"],
        "IDENTIFIER_TYPE": ["identifier"],
        "ATTRIBUTE_TYPE": ["selector_expression"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["assignment_statement", "short_var_declaration"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement"],
        "WHILE_STATEMENT_TYPE": ["for_statement"],  # Go 用 for 实现 while
        "RETURN_STATEMENT_TYPE": ["return_statement"],
        "GOROUTINE_TYPE": ["go_statement"],  # Go 特有
        "CHANNEL_TYPE": ["channel_type"]  # Go 特有
    },
    "c": {
        "CLASS_TYPE": ["struct_specifier", "union_specifier", "enum_specifier"],
        "FUNCTION_TYPE": ["function_definition"],
        "IMPORT_TYPE": ["preproc_include"],
        "IDENTIFIER_TYPE": ["identifier"],
        "ATTRIBUTE_TYPE": ["field_expression"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["declaration"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_statement"],
        "POINTER_TYPE": ["pointer_declarator"],  # C 特有
        "TYPEDEF_TYPE": ["type_definition"]  # C 特有
    },
    "rust": {
        "CLASS_TYPE": ["struct_item", "enum_item", "trait_item", "impl_item"],
        "FUNCTION_TYPE": ["function_item"],
        "IMPORT_TYPE": ["use_declaration"],
        "IDENTIFIER_TYPE": ["identifier"],
        "ATTRIBUTE_TYPE": ["field_expression"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["let_declaration"],
        "COMMENT_TYPE": ["line_comment", "block_comment"],
        "IF_STATEMENT_TYPE": ["if_expression"],
        "FOR_STATEMENT_TYPE": ["for_expression"],
        "WHILE_STATEMENT_TYPE": ["while_expression"],
        "RETURN_STATEMENT_TYPE": ["return_expression"],
        "MATCH_STATEMENT_TYPE": ["match_expression"],  # Rust 特有
        "MACRO_TYPE": ["macro_invocation"]  # Rust 特有
    },
    "r": {
        "CLASS_TYPE": ["setClass", "setRefClass", "R6Class"],  # R语言的类定义方式
        "FUNCTION_TYPE": ["function_definition", "assignment"],  # function() 和 <- 赋值函数
        "IMPORT_TYPE": ["library_call", "require_call", "source_call"],  # library(), require(), source()
        "IDENTIFIER_TYPE": ["identifier", "symbol"],
        "ATTRIBUTE_TYPE": ["subset", "subset2"],  # $ 和 [[ ]] 访问
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["left_assignment", "right_assignment", "equals_assignment"],  # <-, ->, =
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_statement"],
        "VECTOR_TYPE": ["call"],  # R特有：向量操作
        "DATAFRAME_TYPE": ["data_frame"]  # R特有：数据框
    },
    "ruby": {
        "CLASS_TYPE": ["class", "module"],  # class 和 module 定义
        "FUNCTION_TYPE": ["method", "singleton_method"],  # def 方法定义
        "IMPORT_TYPE": ["require", "require_relative", "load"],  # require, require_relative, load
        "IDENTIFIER_TYPE": ["identifier", "constant"],
        "ATTRIBUTE_TYPE": ["call"],  # 方法调用和属性访问
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["assignment", "operator_assignment"],  # = 和 +=, -=等
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if", "unless"],  # if 和 unless
        "FOR_STATEMENT_TYPE": ["for"],
        "WHILE_STATEMENT_TYPE": ["while", "until"],  # while 和 until
        "RETURN_STATEMENT_TYPE": ["return"],
        "BLOCK_TYPE": ["block", "do_block"],  # Ruby特有：代码块
        "SYMBOL_TYPE": ["symbol"],  # Ruby特有：符号
        "STRING_INTERPOLATION_TYPE": ["string"]  # Ruby特有：字符串插值
    },
    "scala": {
        "CLASS_TYPE": ["class_definition", "object_definition", "trait_definition"],
        "FUNCTION_TYPE": ["function_definition", "method_definition"],
        "IMPORT_TYPE": ["import_declaration"],
        "IDENTIFIER_TYPE": ["identifier"],
        "ATTRIBUTE_TYPE": ["field_expression", "select_expression"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["val_definition", "var_definition"],
        "COMMENT_TYPE": ["comment", "block_comment"],
        "IF_STATEMENT_TYPE": ["if_expression"],
        "FOR_STATEMENT_TYPE": ["for_expression"],
        "WHILE_STATEMENT_TYPE": ["while_expression"],
        "RETURN_STATEMENT_TYPE": ["return_expression"],
        "CASE_CLASS_TYPE": ["case_class_definition"],  # Scala特有
        "PATTERN_MATCH_TYPE": ["match_expression"],  # Scala特有
        "LAMBDA_TYPE": ["lambda_expression"]  # Scala特有
    },
    "kotlin": {
        "CLASS_TYPE": ["class_declaration", "object_declaration", "interface_declaration"],
        "FUNCTION_TYPE": ["function_declaration"],
        "IMPORT_TYPE": ["import_header"],
        "IDENTIFIER_TYPE": ["simple_identifier"],
        "ATTRIBUTE_TYPE": ["navigation_expression"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["property_declaration", "variable_declaration"],
        "COMMENT_TYPE": ["line_comment", "multiline_comment"],
        "IF_STATEMENT_TYPE": ["if_expression"],
        "FOR_STATEMENT_TYPE": ["for_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_expression"],
        "DATA_CLASS_TYPE": ["class_declaration"],  # Kotlin特有：data class
        "EXTENSION_FUNCTION_TYPE": ["function_declaration"],  # Kotlin特有：扩展函数
        "WHEN_EXPRESSION_TYPE": ["when_expression"],  # Kotlin特有：when表达式
        "NULLABLE_TYPE": ["nullable_type"]  # Kotlin特有：可空类型
    },
    "perl": {
        "CLASS_TYPE": ["package_declaration", "class_statement"],  # 修正为package_declaration，Perl的包声明类似类
        "FUNCTION_TYPE": ["method_declaration_statement", "function_definition", "subroutine_declaration_statement"],  # 修正为sub_declaration，对应sub函数声明
        "IMPORT_TYPE": ["use_statement", "require_statement"],
        "IDENTIFIER_TYPE": ["identifier"],
        "ATTRIBUTE_TYPE": ["hash_access", "array_access"],
        "EXPRESSION_STATEMENT_TYPE": ["call_experssion", "binary_expression", "hash_access_variable", "unary_expression"],
        "ASSIGNMENT_STATEMENT_TYPE": ["variable_declaration"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement", "foreach_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_expression"],
        "REGEX_TYPE": ["regex"],  # Perl特有：正则表达式
        "HASH_TYPE": ["hash"],  # Perl特有：哈希
        "ARRAY_TYPE": ["array"],  # Perl特有：数组
        "REFERENCE_TYPE": ["reference"]  # Perl特有：引用
    },
    "lua": {
        "CLASS_TYPE": ["table_constructor"],  # Lua使用table作为类的基础
        "FUNCTION_TYPE": ["coroutine_create", "function_definition", "function_declaration", "local_function", "method_definition"],
        "IMPORT_TYPE": ["require_statement", "dofile_statement", "loadfile_statement"],
        "IDENTIFIER_TYPE": ["identifier", "field"],
        "ATTRIBUTE_TYPE": ["field_access", "index_access", "dot_index"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["assignment_statement", "local_assignment", "metatable_assignment"],
        "COMMENT_TYPE": ["comment", "block_comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement", "for_in_statement", "while_statement", "repeat_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_statement"],
    },
    "css": {
        "CLASS_TYPE": ["class_selector", "id_selector", "attribute_selector"],
        "FUNCTION_TYPE": ["function_value", "calc_expression", "var_function", "selectors"],
        "IMPORT_TYPE": ["import_statement", "at_rule"],
        "IDENTIFIER_TYPE": ["identifier", "property_name", "tag_name"],
        "ATTRIBUTE_TYPE": ["property_name", "attribute_name"],
        "EXPRESSION_STATEMENT_TYPE": ["declaration", "rule_set"],
        "ASSIGNMENT_STATEMENT_TYPE": ["declaration"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["media_query", "supports_query"],
        "FOR_STATEMENT_TYPE": ["keyframes_statement"],
        "WHILE_STATEMENT_TYPE": ["rule_set", "declaration"],
        "RETURN_STATEMENT_TYPE": [],
        "BLOCK_TYPE": ["rule_set", "declaration", "media_query", "keyframes_statement"],  # CSS块级单位：规则集、声明、媒体查询、关键帧
        # "SELECTOR_TYPE": ["selectors"],  # CSS特有：选择器
        # "MEDIA_QUERY_TYPE": ["media_query"],  # CSS特有：媒体查询
        # "KEYFRAMES_TYPE": ["keyframes_statement"]  # CSS特有：关键帧动画
    },
    "elisp": {
        "CLASS_TYPE": ["defclass", "defstruct"],
        "FUNCTION_TYPE": ["defun", "defmacro", "lambda", "defmethod"],
        "IMPORT_TYPE": ["require", "load", "autoload"],
        "IDENTIFIER_TYPE": ["symbol", "variable"],
        "ATTRIBUTE_TYPE": ["slot", "property"],
        "EXPRESSION_STATEMENT_TYPE": ["expression"],
        "ASSIGNMENT_STATEMENT_TYPE": ["setq", "setf", "defvar", "defconst"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if", "when", "unless", "cond"],
        "FOR_STATEMENT_TYPE": ["dolist", "dotimes", "loop", "while"],
        "WHILE_STATEMENT_TYPE": ["while"],
        "RETURN_STATEMENT_TYPE": ["return", "return-from"],
        # "DEFVAR_TYPE": ["defvar", "defconst"],  # Elisp特有：变量定义
        # "DEFMACRO_TYPE": ["defmacro"],  # Elisp特有：宏定义
        # "QUOTE_TYPE": ["quote"]  # Elisp特有：引用
    },
    "erlang": {
        "CLASS_TYPE": ["module", "record"],
        "FUNCTION_TYPE": ["function_declaration", "function_clause", "spawn", "receive"],
        "IMPORT_TYPE": ["import", "include", "include_lib"],
        "IDENTIFIER_TYPE": ["atom", "variable"],
        "ATTRIBUTE_TYPE": ["attribute", "record_field"],
        "EXPRESSION_STATEMENT_TYPE": ["expression"],
        "ASSIGNMENT_STATEMENT_TYPE": ["match", "assignment"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if_expression", "case_expression"],
        "FOR_STATEMENT_TYPE": ["list_comprehension", "binary_comprehension"],
        "WHILE_STATEMENT_TYPE": [],
        "RETURN_STATEMENT_TYPE": [],
        # "MODULE_TYPE": ["module"],  # Erlang特有：模块声明
        # "RECORD_TYPE": ["record"],  # Erlang特有：记录定义
        # "PROCESS_TYPE": ["spawn", "receive"]  # Erlang特有：进程相关
    },
    "html":{
        "CLASS_TYPE": ["element", "start_tag", "end_tag"],
        "FUNCTION_TYPE": ["script_element"],
        "IMPORT_TYPE": ["link_element", "script_element"],
        "IDENTIFIER_TYPE": ["tag_name", "attribute_name"],
        "ATTRIBUTE_TYPE": ["attribute", "attribute_name", "attribute_value"],
        "EXPRESSION_STATEMENT_TYPE": ["element"],
        "ASSIGNMENT_STATEMENT_TYPE": ["attribute"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": [],
        "FOR_STATEMENT_TYPE": ["element", "script_element", "style_element", "cdata_section"], # BLOCK_TYPE
        "WHILE_STATEMENT_TYPE": [],
        "RETURN_STATEMENT_TYPE": [],
        "BLOCK_TYPE": [],  # HTML块级单位：元素、脚本块、样式块、CDATA节
        # "DOCTYPE_TYPE": ["doctype"],  # HTML特有：文档类型声明
        # "TEXT_TYPE": ["text"],  # HTML特有：文本内容
        # "CDATA_TYPE": ["cdata_section"]  # HTML特有：CDATA节
    },
    "ocaml": {
        "CLASS_TYPE": ["type_definition", "class_definition", "module_definition", "signature"],
        "FUNCTION_TYPE": ["function_definition", "value_definition", "method_definition", "let_binding"],
        "IMPORT_TYPE": ["open_statement", "include_statement", "module_binding"],
        "IDENTIFIER_TYPE": ["identifier", "type_identifier", "module_identifier"],
        "ATTRIBUTE_TYPE": ["attribute", "field_declaration"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement", "let_expression"],
        "ASSIGNMENT_STATEMENT_TYPE": ["let_binding", "assignment_expression"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if_expression", "match_expression"],
        "FOR_STATEMENT_TYPE": ["for_expression"],
        "WHILE_STATEMENT_TYPE": ["while_expression"],
        "RETURN_STATEMENT_TYPE": ["expression_statement"],
        # "PATTERN_TYPE": ["pattern"],  # OCaml特有：模式匹配
        # "VARIANT_TYPE": ["variant_declaration"],  # OCaml特有：变体类型
        # "RECORD_TYPE": ["record_declaration"]  # OCaml特有：记录类型
    },
    "julia": {
        "CLASS_TYPE": ["struct_definition", "abstract_definition", "primitive_definition", "module_definition"],
        "FUNCTION_TYPE": ["function_definition", "short_function_definition", "macro_definition"],
        "IMPORT_TYPE": ["import_statement", "using_statement", "include_statement"],
        "IDENTIFIER_TYPE": ["identifier", "field_expression"],
        "ATTRIBUTE_TYPE": ["field_expression", "parameter_list"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement", "assignment_expression"],
        "ASSIGNMENT_STATEMENT_TYPE": ["assignment_expression", "compound_assignment_expression"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["if_statement", "ternary_expression"],
        "FOR_STATEMENT_TYPE": ["for_statement", "while_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return_statement"],
        # "MACRO_TYPE": ["macro_definition", "macro_call"],  # Julia特有：宏
        # "TYPE_ANNOTATION_TYPE": ["type_annotation"],  # Julia特有：类型注解
        # "COMPREHENSION_TYPE": ["comprehension_expression"]  # Julia特有：推导式
    },
    "hcl": {
        "CLASS_TYPE": ["block", "object_elem", "object"],
        "FUNCTION_TYPE": ["function_call", "expression"],
        "IMPORT_TYPE": ["block"],  # HCL中通过block实现模块导入
        "IDENTIFIER_TYPE": ["identifier", "attribute_name"],
        "ATTRIBUTE_TYPE": ["attribute", "object_elem"],
        "EXPRESSION_STATEMENT_TYPE": ["attribute", "block"],
        "ASSIGNMENT_STATEMENT_TYPE": ["attribute"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": ["conditional_expression"],
        "FOR_STATEMENT_TYPE": ["for_expression"],
        "WHILE_STATEMENT_TYPE": [],
        "RETURN_STATEMENT_TYPE": [],
        "BLOCK_TYPE": ["block", "object", "tuple"],  # HCL特有：配置块
        # "RESOURCE_TYPE": ["block"],  # HCL特有：资源块
        # "VARIABLE_TYPE": ["block"],  # HCL特有：变量块
        # "OUTPUT_TYPE": ["block"]  # HCL特有：输出块
    },
    "swift": {
        "CLASS_TYPE": ["class_declaration", "struct_declaration", "enum_declaration", "protocol_declaration"],
        "FUNCTION_TYPE": ["function_declaration", "init_declaration"],
        "IMPORT_TYPE": ["import_declaration"],
        "IDENTIFIER_TYPE": ["simple_identifier"],
        "ATTRIBUTE_TYPE": ["navigation_expression", "member_access_expression"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["property_declaration", "variable_declaration", "extension_declaration"],
        "COMMENT_TYPE": ["comment", "multiline_comment"],
        "IF_STATEMENT_TYPE": ["if_statement"],
        "FOR_STATEMENT_TYPE": ["for_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement", "lambda_literal"],
        "RETURN_STATEMENT_TYPE": ["return_statement"],
        # "EXTENSION_TYPE": ["extension_declaration"],  # Swift特有：扩展
        # "CLOSURE_TYPE": ["lambda_literal"],  # Swift特有：闭包
        # "OPTIONAL_TYPE": ["optional_type"],  # Swift特有：可选类型
        # "GUARD_STATEMENT_TYPE": ["guard_statement"]  # Swift特有：guard语句
    },
    "zig": {
        "CLASS_TYPE": ["ContainerDecl", "struct", "enum", "union"],
        "FUNCTION_TYPE": ["FnProto", "Decl"],  # 函数声明和定义
        "IMPORT_TYPE": ["BUILTINIDENTIFIER"],  # @import等内置标识符
        "IDENTIFIER_TYPE": ["IDENTIFIER"],
        "ATTRIBUTE_TYPE": ["FieldOrFnCall", "SuffixOp"],  # 字段访问和后缀操作
        "EXPRESSION_STATEMENT_TYPE": ["Statement", "AssignExpr"],
        "ASSIGNMENT_STATEMENT_TYPE": ["VarDecl", "AssignExpr"],  # 变量声明和赋值表达式
        "COMMENT_TYPE": ["line_comment", "comment"],
        "IF_STATEMENT_TYPE": ["IfStatement"],
        "FOR_STATEMENT_TYPE": ["for_statement"],
        "WHILE_STATEMENT_TYPE": ["while_statement"],
        "RETURN_STATEMENT_TYPE": ["return"],
        "COMPTIME_TYPE": ["comptime"],  # zig特有的编译时计算
        "ERROR_TYPE": ["ErrorSetDecl", "ErrorUnionExpr"],  # zig特有的错误处理
        "TEST_TYPE": ["test"],  # zig特有的测试声明
        "BLOCK_TYPE": ["Block"],
        "CONTAINER_FIELD_TYPE": ["ContainerField"],  # zig特有的容器字段
        "PARAM_DECL_TYPE": ["ParamDecl"],  # 参数声明
        "BUILTIN_TYPE": ["BuildinTypeExpr"],  # 内置类型表达式
        "INIT_LIST_TYPE": ["InitList"],  # 初始化列表
        "FIELD_INIT_TYPE": ["FieldInit"]  # 字段初始化
    },
    "verilog": {
        "CLASS_TYPE": ["module_declaration", "interface_declaration", "class_declaration"],
        "FUNCTION_TYPE": ["function_declaration", "task_declaration"],
        "IMPORT_TYPE": ["include_statement", "import_statement"],
        "IDENTIFIER_TYPE": ["simple_identifier"],
        "ATTRIBUTE_TYPE": ["hierarchical_identifier", "member_access"],
        "EXPRESSION_STATEMENT_TYPE": ["expression_statement"],
        "ASSIGNMENT_STATEMENT_TYPE": ["net_declaration", "variable_declaration", "continuous_assign"],
        "COMMENT_TYPE": ["comment", "block_comment"],
        "IF_STATEMENT_TYPE": ["conditional_statement"],
        "FOR_STATEMENT_TYPE": ["loop_statement", "always_construct", "initial_construct", "generate_region"],
        "WHILE_STATEMENT_TYPE": ["port_declaration"],
        "RETURN_STATEMENT_TYPE": ["return_statement"],
        # "ALWAYS_BLOCK_TYPE": ["always_construct"],  # Verilog特有：always块
        # "INITIAL_BLOCK_TYPE": ["initial_construct"],  # Verilog特有：initial块
        # "GENERATE_BLOCK_TYPE": ["generate_region"],  # Verilog特有：generate块
        # "PORT_DECLARATION_TYPE": ["port_declaration"]  # Verilog特有：端口声明
    },
    "html": {
        "CLASS_TYPE": ["element"],  # HTML元素作为类级别
        "FUNCTION_TYPE": ["script_element", "style_element"],  # script和style标签作为函数级别
        "IMPORT_TYPE": ["doctype", "start_tag"],  # DOCTYPE和开始标签
        "IDENTIFIER_TYPE": ["tag_name", "attribute_name"],
        "ATTRIBUTE_TYPE": ["attribute", "quoted_attribute_value"],
        "EXPRESSION_STATEMENT_TYPE": ["element", "self_closing_tag"],
        "ASSIGNMENT_STATEMENT_TYPE": ["attribute"],
        "COMMENT_TYPE": ["comment"],
        "IF_STATEMENT_TYPE": [],  # HTML没有条件语句
        "FOR_STATEMENT_TYPE": [],  # HTML没有循环语句
        "WHILE_STATEMENT_TYPE": [],
        "RETURN_STATEMENT_TYPE": [],
        # HTML特有的BLOCK级别标签（容器类、布局类）
        "BLOCK_TYPE": ["div", "section", "article", "header", "footer", "nav", "main", "aside", "form", "table", "ul", "ol", "dl"],
        # HTML特有的LINE级别标签（内联元素、文本元素）
        "LINE_TYPE": ["span", "a", "strong", "em", "b", "i", "u", "small", "mark", "del", "ins", "sub", "sup", "code", "kbd", "samp", "var", "time", "data"]
    },
}

class BM25:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.doc_lengths = self._compute_doc_lengths()
        self.avgdl = sum(self.doc_lengths) / len(self.doc_lengths)
        self.idf_scores = self._compute_idf()

    def _compute_doc_lengths(self):
        return [len(doc) for doc in self.corpus]

    def _compute_idf(self):
        num_docs = len(self.corpus)
        idf_scores = {}

        for doc in self.corpus:
            for term in set(doc):
                idf_scores[term] = idf_scores.get(term, 0) + 1

        for term, freq in idf_scores.items():
            idf_scores[term] = math.log((num_docs - freq + 0.5) / (freq + 0.5) + 1)

        return idf_scores

    def _bm25_score(self, query, doc_index):
        doc = self.corpus[doc_index]
        score = 0
        doc_terms = collections.Counter(doc)
        for term in query:
            if term in doc_terms:
                tf = doc_terms[term]
                idf = self.idf_scores[term] if term in self.idf_scores else 0
                denom = tf + self.k1 * (1 - self.b + self.b * self.doc_lengths[doc_index] / self.avgdl)
                score += idf * tf * (self.k1 + 1) / denom 
        return score


    def get_scores(self, query):
        scores = {}
        for index in range(len(self.corpus)):
            scores[index] = self._bm25_score(query, index)
        return scores

    def get_similarity(self, doc_index):
        target_doc = self.corpus[doc_index]
        similarities = []
        for index in range(len(self.corpus)):
            if index != doc_index:
                similarity = self._bm25_score(target_doc, index)
                similarities.append(similarity)
        return similarities

def is_installed_package(module_name, project_root):
    try:
        module = importlib.import_module(module_name)
        module_path = getattr(module, '__file__', None)
        if module_path is None:
            return True
        module_path = Path(module_path).resolve()
        project_root = Path(project_root).resolve()
        return project_root in module_path.parents
    except:
        #print(f"Cannot import module {module_name}. It may not be installed or the name may be incorrect.")
        return False

#from rank_bm25 import BM25Okapi
class MPLogExceptions(object):
    def __init__(self, callable):
        self.__callable = callable

    def error(msg, *args):
        return mp.get_logger().error(msg, *args) 

    def __call__(self, *args, **kwargs):
        try:
            result = self.__callable(*args, **kwargs)

        except Exception as e:
            # Here we add some debugging help. If multiprocessing's
            # debugging is on, it will arrange to log the traceback
            self.error(traceback.format_exc())
            # Re-raise the original exception so the Pool worker can``
            # clean up
            raise

        # It was fine, give a normal answer
        return result

def read_file_from_position(args):
    filename, start_position, end_position, worker_id = args
    objs = []
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        current_position = find_next_line(f, start_position)
        f.seek(current_position)
        if current_position >= end_position:
            print(f"worker_id {worker_id} completed")
            return objs
        for cnt in tqdm.tqdm(itertools.count(), position=worker_id, desc=f"worker_id: {worker_id}"):
            line = f.readline()  
            if not line:
                break
            obj = json.loads(line)
            objs.append(obj)
            if f.tell() >= end_position:
                break
    print(f"worker_id {worker_id} completed")
    return objs

def find_next_line(f, position):
    if position == 0:
        return position
    f.seek(position)
    f.readline()
    position = f.tell()
    return position

def multi_read(file_name = 'example.txt', workers = 32, chunk_size = None):    
    file_size = os.path.getsize(file_name)
    print(f"The size of {file_name} is: {file_size} bytes")
    if chunk_size:
        assert chunk_size > 0
        job_num = math.ceil(float(file_size) / chunk_size)
        positions = [chunk_size * i for i in range(job_num)]
        start_positions = [(file_name, positions[i], positions[i] + chunk_size, i) for i in range(job_num)]
        print(f"job num: {job_num}")
    else:
        chunk_size = math.ceil(float(file_size) / workers)
        positions = [chunk_size * i for i in range(workers)]
        start_positions = [(file_name, positions[i], positions[i] + chunk_size, i) for i in range(workers)]
    p = mp.Pool(workers)
    results = []
    for pos in start_positions:
        results.append(p.apply_async(MPLogExceptions(read_file_from_position), args=(pos,)))
    p.close()
    p.join()
    output_objs = []
    for result in results:
        output_objs.extend(result.get())
    print(f"Successfully Loading from {file_name}: {len(output_objs)} samples")
    return output_objs

def filter_code(text):
    def calculate_metrics(text):
        NON_ALPHA = re.compile("[^A-Za-z_0-9]")
        lines = text.strip().split('\n')
        line_lengths = [len(line) for line in lines]
        if len(lines) > 0:
            avg_line_length = sum(line_lengths) / len(lines)
            max_line_length = max(line_lengths)
        else:
            avg_line_length = 0
            max_line_length = 0
        alphanum_count = sum(c.isalnum() for c in text)
        alpha_count = sum(c.isalpha() for c in text)
        if len(text) > 0:
            alphanum_fraction = alphanum_count / len(text)
            alpha_fraction = alpha_count / len(text)
        else:
            alphanum_fraction = 0
            alpha_fraction = 0
        alpha_len = len(NON_ALPHA.split(text))
        char_len = len(text)
        tokens_num = len(text.split())
        return char_len, alpha_len, avg_line_length, max_line_length, alphanum_fraction, alpha_fraction, tokens_num
    char_len, alpha_len, avg_line_length, max_line_length, alphanum_fraction, alpha_fraction, tokens_num = calculate_metrics(text)
    if (1 < avg_line_length < 50) and (1 < max_line_length < 100) and (0.1 < alphanum_fraction < 1.0) and (0.1 < alpha_fraction < 1.0) and (10 < tokens_num < 1024):
        return False
    else:
        return True
    

def read_file_from_position_with_filter(args):
    filename, start_position, end_position, worker_id = args
    objs = []
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        current_position = find_next_line(f, start_position)
        f.seek(current_position)
        if current_position >= end_position:
            print(f"worker_id {worker_id} completed")
            return objs
        for cnt in tqdm.tqdm(itertools.count(), position=worker_id, desc=f"worker_id: {worker_id}"):
            line = f.readline()  
            if not line:
                break
            obj = json.loads(line)
            #if not filter_code(obj["text"]):
            objs.append(obj)
            if f.tell() >= end_position:
                break
    print(f"worker_id {worker_id} completed")
    return objs

def multi_read_with_filter(file_name = 'example.txt', workers = 32, chunk_size = None):    
    file_size = os.path.getsize(file_name)
    print(f"The size of {file_name} is: {file_size} bytes")
    if chunk_size:
        assert chunk_size > 0
        job_num = math.ceil(float(file_size) / chunk_size)
        positions = [chunk_size * i for i in range(job_num)]
        start_positions = [(file_name, positions[i], positions[i] + chunk_size, i) for i in range(job_num)]
        print(f"job num: {job_num}")
    else:
        chunk_size = math.ceil(float(file_size) / workers)
        positions = [chunk_size * i for i in range(workers)]
        start_positions = [(file_name, positions[i], positions[i] + chunk_size, i) for i in range(workers)]
    p = mp.Pool(workers)
    results = []
    for pos in start_positions:
        results.append(p.apply_async(MPLogExceptions(read_file_from_position_with_filter), args=(pos,)))
    p.close()
    p.join()
    output_objs = []
    for result in results:
        output_objs.extend(result.get())
    print(f"Successfully Loading from {file_name}: {len(output_objs)} samples")
    return output_objs

def read_jsonl_file(file_name, max_sentence=None):
    data = []
    with jsonlines.open(file_name, "r") as r:
        for i, obj in tqdm.tqdm(enumerate(r)):
            if max_sentence is not None and i >= max_sentence:
                return data
            data.append(obj)
    return data

def safe_read_jsonl_file(file_name, max_sentence=None):
    data = []
    with open(file_name, "r", encoding="utf-8", errors="ignore") as r:
        for i, line in tqdm.tqdm(enumerate(r)):
            try:
                obj = json.loads(line)
                if max_sentence is not None and i >= max_sentence:
                    return data
                data.append(obj)
            except:
                continue
    return data

def read_json_file(path):
    with open(path, "r") as r:
        objs = json.load(r)
    print(f"Successfully loading from {path}")
    return objs
    
def write_jsonl_file(objs, path, chunk_size = 1):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path), exist_ok = True)
    with jsonlines.open(path, "w", flush=True) as w:
        for i in tqdm.tqdm(range(0, len(objs), chunk_size)):
            try:
                w.write_all(objs[i: i + chunk_size])
            except Exception as e:
                print(type(objs), type(objs[i]))
                print(f"出错 {i} {i + chunk_size} {len(objs)}")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                exit()
    print(f"Successfully saving to {path}: {len(objs)}")

def get_avg_score(samples, key):
    return float(np.average([obj[key] for obj in samples]))

def copy_src_to_dest(src_dir, tgt_dir, cur):
    os.makedirs(tgt_dir, exist_ok=True)
    source_dir = f"{src_dir}/{cur}"
    target_dir = f"{tgt_dir}/{cur}"
    subprocess.run(["cp", "-r", source_dir, target_dir])


def read_jsonl_file(file_name, max_sentence=None):
    data = []
    with jsonlines.open(file_name, "r") as r:
        for i, obj in tqdm.tqdm(enumerate(r)):
            if max_sentence is not None and i >= max_sentence:
                return data
            data.append(obj)
    return data


def sentence_jaccard_similarity(sentence1, sentence2):
    def tokenize(sentence):
        """
        Tokenize the input sentence into a set of words.
        """
        # Convert to lowercase and split the sentence into words
        words = re.findall(r'\b\w+\b', sentence.lower())
        # Return the set of words
        return set(words)
    """
    Calculate the Jaccard Similarity between two sentences.
    """
    # Tokenize the sentences into sets of words
    set1 = tokenize(sentence1)
    set2 = tokenize(sentence2)
    
    # Calculate intersection and union
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    
    # Compute Jaccard Similarity
    similarity = len(intersection) / len(union)
    return similarity

def read_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def save_json(data, file_name):
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    print(f"Successfully saving to {file_name}")

def multi_write_jsonl_file(objs, path, workers = 16):
    chunk_size = math.ceil(len(objs) / workers)
    positions = [chunk_size * i for i in range(workers)]
    start_positions = [(objs[positions[i]: positions[i] + chunk_size], f"{path}-worker{i}.jsonl") for i in range(workers)]
    p = mp.Pool(workers)
    results = []
    for pos in start_positions:
        results.append(p.apply_async(MPLogExceptions(write_jsonl_file), args=(pos[0], pos[1])))
    p.close()
    p.join()
    p1 = subprocess.Popen(f"ls {path}-worker*.jsonl | sort -V | xargs cat > {path}", shell=True)
    p1.wait()
    print(f"Start merging to {path}")
    p2 = subprocess.Popen(f"rm {path}-worker*.jsonl", shell=True)
    print(f"Successfully Saving to {path}")

def extract_code(text):
    if re.search(r"```(.*?)\n(.*?)```", text, flags=re.DOTALL) is not None:
        return re.search(r"```(.*?)\n(.*?)```", text, flags=re.DOTALL).group(2)
    else:
        return text

def extract_class_name(code):
    if re.search(r"public class\s+(\w*?)\s+{", code, flags=re.DOTALL) is not None:
        return re.search(r"class\s+(\w*?)\s+{", code, flags=re.DOTALL).group(1)
    else:
        return "Main"

def minihash_deduplicate(data):
    hash_set = set()
    deduped_data = []
    for item in tqdm.tqdm(data):
        hash_value = hashlib.md5(item["text"].encode()).hexdigest()
        if hash_value not in hash_set:
            deduped_data.append(item)
            hash_set.add(hash_value)
    return deduped_data

def contain_chinese(string):
    for ch in string:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
    return False


def remove_blank_line(code):
    code_lines = code.split("\n")
    code_lines = [c for c in code_lines if c.strip() != ""]
    code = "\n".join(code_lines)
    return code

def cal_edit_sim(references, hypotheses):
    total = len(references)
    edit_sim = 0.0
    for pred, gt in zip(hypotheses, references):
        pred = pred.strip()
        gt = gt.strip()
        edit_sim += fuzz.ratio(pred, gt)
    return edit_sim / total


def remove_comments(code, language, remove_blank_line=True):
    """
    移除代码中的注释，结合正则表达式预处理和tree-sitter补充处理
    
    Args:
        code (str): 源代码
        language (str): 编程语言
        remove_blank_line (bool): 是否移除空白行
    
    Returns:
        str: 移除注释后的代码
    """
    if not code or not code.strip():
        return code
    
    try:
        # 第一步：使用正则表达式移除常见注释模式
        code_after_regex = _remove_comments_regex_comprehensive(code, language)
        
        # 第二步：使用tree-sitter进行补充处理
        try:
            
            # 语言名称标准化（参考create_test_repo.py的处理方式）
            language = language.lower()
            if language == "c++":
                language = "cpp"
            elif language == "c#":
                language = "c_sharp"
            
            # 获取语言对应的注释类型
            if language in language_symbols:
                comment_types = language_symbols[language].get('COMMENT_TYPE', [])
                if isinstance(comment_types, str):
                    comment_types = [comment_types]
                
                if comment_types:
                    code_bytes = bytes(code_after_regex, "utf8")
                    tree = None
                    
                    # 根据create_test_repo.py的方式处理解析器
                    if language == "c_sharp":
                        import tree_sitter_c_sharp as tscsharp
                        from tree_sitter import Language, Parser
                        CSHARP_LANGUAGE = Language(tscsharp.language())
                        parser = Parser(CSHARP_LANGUAGE)
                        tree = parser.parse(code_bytes)
                    else:
                        parser = tree_sitter_languages.get_parser(language)
                        tree = parser.parse(code_bytes)
                    
                    if tree:
                        root_node = tree.root_node
                        
                        # 收集所有注释节点的位置
                        comment_ranges = []
                        for node in traverse_tree(root_node):
                            if node.type in comment_types:
                                comment_ranges.append((node.start_byte, node.end_byte))
                        
                        # 按位置倒序排列，从后往前删除，避免位置偏移
                        comment_ranges.sort(key=lambda x: x[0], reverse=True)
                        
                        # 移除注释
                        code_bytes = code_after_regex.encode('utf8')
                        for start_byte, end_byte in comment_ranges:
                            code_bytes = code_bytes[:start_byte] + code_bytes[end_byte:]
                        
                        code_after_regex = code_bytes.decode('utf8')
        
        except Exception as e:
            # tree-sitter处理失败，继续使用正则表达式的结果
            print(f"Tree-sitter processing failed for {language}: {e}")
            pass
        
        # 第三步：移除空白行（如果需要）
        if remove_blank_line:
            lines = code_after_regex.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            code_after_regex = '\n'.join(non_empty_lines)
        
        return code_after_regex
        
    except Exception as e:
        print(f"Error in remove_comments: {e}")
        # 如果所有方法都失败，返回原始代码
        return code

def _remove_comments_regex_comprehensive(code, language):
    """
    使用正则表达式移除常见的注释模式
    """
    import re
    
    # 定义各种注释模式
    patterns = [
        # 0. # 单行注释 (Python, R, Ruby, Perl, Shell等) - 但排除shebang行
        r'(?<!^)#.*?(?=\n|$)',
        
        # 1. """xxx""" 多行字符串/文档字符串 (Python)
        r'\"\"\"[\s\S]*?\"\"\"',
        
        # 2. // 单行注释 (C, C++, Java, JavaScript, C#, Go, Rust, Swift等)
        r'//.*?(?=\n|$)',
        
        # 3. /// 文档注释 (C#, Rust等)
        r'///.*?(?=\n|$)',
        
        # 4. /*xxxx*/ 块注释 (C, C++, Java, JavaScript, C#, Go, Rust, Swift等)
        r'/\*[\s\S]*?\*/',
        
        # 5. -- 单行注释 (SQL, Lua, Haskell等)
        r'--(?!\[\[).*?(?=\n|$)',
        
        # 6. =begin xxx =end 块注释 (Ruby)
        r'=begin[\s\S]*?=end',
        
        # 7. //! 文档注释 (Rust)
        r'//!.*?(?=\n|$)',
        
        # 8. <!--xxxxx--> HTML注释
        r'<!--[\s\S]*?-->',
        
        # 9. --[[xxxxx--]] Lua块注释
        r'--\[\[[\s\S]*?\]\]',
        
        # 10. =pod xxx =cut Perl文档注释
        r'=pod[\s\S]*?=cut',
        
        # 11. # 行首注释（用于非shebang的行首#注释）
        r'^\s*#(?![!/]).*?(?=\n|$)',
        
        # 12. '''xxx''' Python三引号字符串
        r"'''[\s\S]*?'''",
    ]
    
    # 根据语言选择合适的模式
    language_patterns = {
        'python': [0, 1, 12, 11],  # #(非行首), \"\"\"\"\"\", ''''''', #(行首非shebang)
        'java': [2, 4],    # //, /**/
        'javascript': [2, 4],  # //, /**/
        'typescript': [2, 4],  # //, /**/
        'c': [2, 4],       # //, /**/
        'cpp': [2, 4],     # //, /**/
        'c_sharp': [2, 3, 4],  # //, ///, /**/
        'go': [2, 4],      # //, /**/
        'rust': [2, 3, 4, 7],  # //, ///, /**/, //!
        'swift': [2, 4],   # //, /**/
        'kotlin': [2, 4],  # //, /**/
        'scala': [2, 4],   # //, /**/
        'php': [0, 2, 4, 11],  # #(非行首), //, /**/, #(行首非shebang)
        'ruby': [0, 6, 11],    # #(非行首), =begin =end, #(行首非shebang)
        'perl': [0, 10, 11],   # #(非行首), =pod =cut, #(行首非shebang)
        'r': [0, 11],          # #(非行首), #(行首非shebang)
        'lua': [9, 5],    # --(非多行), --[[--]]
        'html': [8],       # <!---->
        'sql': [5],        # --
        'verilog': [2, 4], # //, /**/
        'zig': [2, 4],     # //, /**/
    }
    
    # 获取当前语言的模式索引
    pattern_indices = language_patterns.get(language.lower(), [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])  # 默认使用大部分模式
    
    # 应用选定的模式
    for idx in pattern_indices:
        if idx < len(patterns):
            code = re.sub(patterns[idx], '', code, flags=re.MULTILINE | re.DOTALL)
    return code

def remove_blank_line_func(code):
    """
    移除空白行的辅助函数
    """
    code_lines = code.split("\n")
    code_lines = [c for c in code_lines if c.strip() != ""]
    return "\n".join(code_lines)

def multi_tasks_from_objs(objs, workers = 64, task=None, chunk_size=None, args=None):
    p = mp.Pool(workers)
    if chunk_size:
        results = []
        job_num = math.ceil(len(objs) / chunk_size)
        print(f"job num: {job_num}")
        for worker_id in range(job_num):
            results.append(p.apply_async(MPLogExceptions(task), args=(objs[worker_id * chunk_size: (worker_id + 1) * chunk_size], worker_id, workers, args)))
    else:
        chunk_size = math.ceil(len(objs) / float(workers))
        results = []
        for worker_id in range(workers):
            results.append(p.apply_async(MPLogExceptions(task), args=(objs[worker_id * chunk_size: (worker_id + 1) * chunk_size], worker_id, workers, args)))
    p.close()
    p.join()
    output_objs = []
    for result in results:
        output_objs.extend(result.get())
    return output_objs

def read_jsonl_file(file_path):
    """
    读取JSONL文件，返回包含所有数据的列表
    """
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if line:  # 跳过空行
                    try:
                        json_obj = json.loads(line)
                        data.append(json_obj)
                    except json.JSONDecodeError as e:
                        print(f"警告：第{line_num}行JSON解析失败: {e}")
                        continue
        print(f"成功读取 {len(data)} 条记录从 {file_path}")
        return data
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 不存在")
        return []
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
        return []

def save_results_to_jsonl(results, output_path):
    """
    将结果保存到JSONL文件
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            for result in results:
                json_line = json.dumps(result, ensure_ascii=False)
                file.write(json_line + '\n')
        print(f"结果已保存到 {output_path}")
    except Exception as e:
        print(f"保存结果时发生错误: {e}")

def safe_read_files(files):
    """
    读取files中的所有对应文件的内容
    """
    data = {}
    for f in files:
        try:
            data[f] = open(f, "r").read()
        except:
            continue
    return data

def truncate_prompt(prompt, max_num_tokens, tokenizer, side="right"):
    tokens = tokenizer.tokenize(prompt)
    num_tokens = len(tokens)
    if num_tokens > max_num_tokens:
        if side == 'left':
            prompt_tokens = tokens[num_tokens - max_num_tokens:]
        elif side == 'right':
            prompt_tokens = tokens[:max_num_tokens]
        prompt = tokenizer.convert_tokens_to_string(prompt_tokens)
        new_len = len(tokenizer.tokenize(prompt))
        if new_len > max_num_tokens:
            print(f'Number of tokens after truncation is greater than max tokens allowed {max_num_tokens}: {new_len} {num_tokens}')
    return prompt

def get_definition_name(node, node_types):
    for child in node.children:
        if child.type == node_types["IDENTIFIER_TYPE"]:
            return child.text.decode("utf8")

def has_return_statement(node, node_types):
    traverse_nodes = traverse_tree(node)
    for node in traverse_nodes:
        if node.type == node_types["RETURN_TYPE"]:
            return True
    return False



def extract_imports(code, language="python"):
    code_bytes = bytes(code, "utf8")
    parser = tree_sitter_languages.get_parser(language)
    tree = parser.parse(code_bytes)
    root_node = tree.root_node
    parser = tree_sitter_languages.get_parser(language)
    imports = []
    all_nodes = list(traverse_tree(root_node))
    for child in all_nodes:
        if child.type == 'import_statement':
            for imported_name in child.named_children:
                if imported_name.type == 'dotted_name':
                    module_name = imported_name.text.decode("utf-8")
                    imports.append(module_name)
        elif child.type == 'import_from_statement':
            module_name = []
            for sub_child in child.children:
                if sub_child.type == 'dotted_name':
                    module_name.append(sub_child.text.decode("utf-8"))
                elif sub_child.type == 'relative_import':
                    module_name.append(sub_child.text.decode("utf-8").replace(".", ""))
            if module_name:
                imports.extend(module_name)
    return imports

def get_relevance(obj, tokenizer, python_path="./miniconda3/envs/"):
    code = obj["inference_info"]["prefix_code"] + obj["inference_info"]["middle_code"] + obj["inference_info"]["suffix_code"]
    all_imported_modules = extract_imports(code)
    imported_modules = []
    for m in all_imported_modules:
        if not is_installed_package(m, python_path):
            imported_modules.append(m)
    print(f"imported_modules为：{imported_modules}")
    context_code_files = obj["context_code"]
    dependencies = np.array([0.0 for i in range(len(context_code_files))])
    for m in imported_modules:
        for index, file_name in enumerate(context_code_files):
            if f"{m}.py" in file_name:
                dependencies[index] += 1.0
    corpus = [tokenizer.tokenize(code)]
    for file_name in context_code_files:
        doc = tokenizer.tokenize(context_code_files[file_name])
        corpus.append(doc)
    bm25 = BM25(corpus)
    target_doc_index = 0
    similarities = bm25.get_similarity(target_doc_index)
    similarities = np.array(similarities) / np.sum(similarities)
    relevance = dependencies + similarities
    return relevance



def traverse_tree(node):
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

def extract_function_signature(node, code_bytes):
    """从函数声明节点中提取函数签名"""
    if node.type == "function_declarator":
        # 获取函数名
        function_name = code_bytes[node.children[0].start_byte: node.children[0].end_byte].decode("utf-8")
        # 获取参数列表
        params = code_bytes[node.children[1].start_byte: node.children[1].end_byte].decode("utf-8")
        return function_name, params
    return None, None

def extract_cpp_function_info(node, code_bytes):
    """从C++实现文件中提取函数信息"""
    if node.type == "function_definition":
        # 获取函数声明部分（不包括函数体）
        declarator = None
        for child in node.children:
            if child.type == "function_declarator":
                declarator = child
                break
        
        if declarator:
            # 提取完整的函数名（包括类名）
            full_function_name = code_bytes[declarator.start_byte: declarator.end_byte].decode("utf-8")
            # 提取函数体
            function_body = code_bytes[node.children[-1].start_byte: node.children[-1].end_byte].decode("utf-8")
            
            # 从完整函数名中提取简单函数名
            if "::" in full_function_name:
                simple_name = full_function_name.split("::")[1].split("(")[0]
            else:
                simple_name = full_function_name.split("(")[0]
            
            return simple_name, full_function_name, function_body
    return None, None, None

def merge_header_and_cpp(header_code, cpp_code, class_name=None):
    """合并头文件和实现文件，生成完整的类"""
    parser = tree_sitter_languages.get_parser("cpp")
    
    # 解析头文件
    header_bytes = bytes(header_code, "utf-8")
    header_tree = parser.parse(header_bytes)
    
    # 解析实现文件
    cpp_bytes = bytes(cpp_code, "utf-8")
    cpp_tree = parser.parse(cpp_bytes)
    
    # 提取头文件中的函数声明
    class_template = []
    for node in traverse_tree(header_tree.root_node):
        if node.type == "class_specifier":
            class_body = node.children[-1]
            for child in class_body.children:
                if child.type == "access_specifier":
                    access_spec = header_bytes[child.start_byte: child.end_byte].decode("utf-8")
                    # 确保访问修饰符后面有冒号
                    if not access_spec.endswith(":"):
                        access_spec += ":"
                    class_template.append({
                        "type": "access_specifier",
                        "content": access_spec
                    })
                elif "declaration" in child.type:
                    declaration = header_bytes[child.start_byte: child.end_byte].decode("utf-8")
                    
                    # 检查是否是函数声明
                    is_function = False
                    function_name = None
                    for grandchild in child.children:
                        if grandchild.type == "function_declarator":
                            is_function = True
                            function_name = header_bytes[grandchild.children[0].start_byte: grandchild.children[0].end_byte].decode("utf-8")
                            break
                    
                    if is_function:
                        class_template.append({
                            "type": "function_declaration",
                            "function_name": function_name,
                            "declaration": declaration.rstrip(";"),
                            "function_body": None  # 待填充
                        })
                    else:
                        class_template.append({
                            "type": "other_declaration",
                            "content": declaration
                        })
    
    # 提取实现文件中的函数实现
    cpp_functions = {}
    for node in traverse_tree(cpp_tree.root_node):
        if node.type == "function_definition":
            simple_name, full_name, body = extract_cpp_function_info(node, cpp_bytes)
            if simple_name:
                cpp_functions[simple_name] = {
                    "full_name": full_name,
                    "body": body
                }
    
    # 匹配并合并
    for item in class_template:
        if item["type"] == "function_declaration":
            func_name = item["function_name"]
            if func_name in cpp_functions:
                item["function_body"] = cpp_functions[func_name]["body"]
    
    # 生成完整的类代码
    merged_class = []
    merged_class.append(f"class {class_name} {{")
    
    for item in class_template:
        if item["type"] == "access_specifier":
            # 访问修饰符，确保格式正确
            merged_class.append(f"  {item['content']}")
        elif item["type"] == "function_declaration":
            if item["function_body"]:
                # 有实现的函数
                merged_class.append(f"    {item['declaration']} {item['function_body']}")
            else:
                # 内联函数或纯声明
                merged_class.append(f"    {item['declaration']};")
        elif item["type"] == "other_declaration":
            merged_class.append(f"    {item['content']}")
    
    merged_class.append("};")    
    return "\n".join(merged_class)

def find_cpp_pairs(header_files, cpp_files):
    """找到.h和.cpp文件的配对关系"""
    pairs = []
    standalone_files = []
    
    for header_file in header_files:
        header_name = os.path.splitext(os.path.basename(header_file))[0]
        # 寻找对应的.cpp文件
        corresponding_cpp = None
        for cpp_file in cpp_files:
            cpp_name = os.path.splitext(os.path.basename(cpp_file))[0]
            if header_name == cpp_name:
                corresponding_cpp = cpp_file
                break
        
        if corresponding_cpp:
            pairs.append((header_file, corresponding_cpp))
            cpp_files.remove(corresponding_cpp)  # 避免重复配对
        else:
            standalone_files.append(header_file)
    
    # 剩余的.cpp文件作为独立文件
    standalone_files.extend(cpp_files)
    
    return pairs, standalone_files

def process_cpp_files(all_file_names, repo_root_path):
    """处理C++文件：配对并虚拟合并"""
    header_files = [f for f in all_file_names if f.endswith(".h")]
    cpp_files = [f for f in all_file_names if f.endswith(".cpp")]
    
    # 找到配对关系
    pairs, standalone_files = find_cpp_pairs(header_files, cpp_files)
    
    repo_files_content = {}
    
    # 处理配对的文件
    for header_file, cpp_file in pairs:
        try:
            with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                header_content = f.read()
            with open(cpp_file, 'r', encoding='utf-8', errors='ignore') as f:
                cpp_content = f.read()
            
            # 提取类名（简化版本）
            class_name = extract_class_name_from_header(header_content)
            if not class_name:
                class_name = os.path.splitext(os.path.basename(header_file))[0]
            
            # 虚拟合并
            merged_content = merge_header_and_cpp(header_content, cpp_content, class_name)
            
            # 使用.h文件路径作为key，内容为合并后的代码
            repo_files_content[header_file] = merged_content
            
        except Exception as e:
            print(f"处理文件对 {header_file}, {cpp_file} 时出错: {e}")
            # 出错时分别处理
            repo_files_content.update(safe_read_files([header_file, cpp_file]))
    
    # 处理独立文件
    repo_files_content.update(safe_read_files(standalone_files))
    
    return repo_files_content

def extract_class_name_from_header(header_content):
    """从头文件中提取类名"""
    import re
    # 简单的正则表达式匹配类声明
    match = re.search(r'class\s+(\w+)', header_content)
    if match:
        return match.group(1)
    return None


def scan_jsonl_files(input_path):
    """
    从input_path中扫描所有.jsonl为后缀的文件
    输入: input_path - 目录路径
    输出: 文件列表
    """
    if not os.path.exists(input_path):
        print(f"路径 {input_path} 不存在")
        return []
    
    if os.path.isfile(input_path) and input_path.endswith('.jsonl'):
        return [input_path]
    
    if os.path.isdir(input_path):
        jsonl_files = glob.glob(os.path.join(input_path, "*.jsonl"))
        return sorted(jsonl_files)
    
    return []