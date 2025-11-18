# 骨架生成器

def generate_class_skeleton(masked_code, language = "python", masked_node = None, all_codes = None) -> str:
    """
    param1: code 遮盖的代码
    param2: masked_node 选择遮盖的类 是tree-sitter覆盖的节点
    return: 返回对应类的骨架 
    """
    if language == "python":
        skeleton = []
        lines = masked_code.split("\n")
        cnt = 0
        for line in lines:
            stripped_code = line.strip()
            if stripped_code.startswith("class"): # 以class开头
                skeleton.append(stripped_code)
            # 如果当前类没有方法 则舍去 没有必要补充这种类
            elif stripped_code.startswith("def") and ('):' in stripped_code or (')' in stripped_code and ':' in stripped_code)):
                lastidx = line.find(':') # 找到:的位置截取到这里就是完整的方法签名
                if lastidx != -1:
                    cnt += 1
                    method_signature = line[: lastidx + 2] # 多+1
                    skeleton.append(method_signature)
                    indent = len(line) - len(line.lstrip())
                    skeleton.append(' ' * (indent + 4) + 'pass')
        return '\n'.join(skeleton) if cnt else None
    elif language == "java":
        # java没有特殊的语法糖 因此使用tree-sitter来解析
        skeleton = []
        cnt = 0
        for child in masked_node.children[:-1]:
            skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
        skeleton.append("{")
        class_body = masked_node.children[-1] #  class的body一般在最后一个
        for child in class_body.children:
            temp_list = []
            if child.type == "field_declaration":
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            elif child.type == "method_declaration":
                for grandchild in child.children[:-1]:
                    temp_list.append(all_codes[grandchild.start_byte: grandchild.end_byte].decode("utf-8"))
                skeleton.append(" ".join(temp_list) + "{}")
                cnt += 1
        skeleton.append("}")
        return "\n".join(skeleton) if cnt else None
    elif language == "cpp":
        # C++类骨架生成
        skeleton = []
        cnt = 0
        
        # 获取类声明部分
        for child in masked_node.children[:-1]:
            skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
        skeleton.append("{")
        
        # 处理类体
        class_body = masked_node.children[-1]
        current_access = "private"  # C++默认访问级别
        
        for child in class_body.children:
            if child.type == "access_specifier":
                access_spec = all_codes[child.start_byte: child.end_byte].decode("utf-8")
                if not access_spec.endswith(":"):
                    access_spec += ":"
                skeleton.append(access_spec)
                current_access = access_spec.rstrip(":").strip()
            elif child.type == "field_declaration":
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            elif child.type == "function_definition":
                # 提取函数声明部分
                func_declaration = []
                for grandchild in child.children[:-1]:
                    func_declaration.append(all_codes[grandchild.start_byte: grandchild.end_byte].decode("utf-8"))
                skeleton.append(" ".join(func_declaration) + " {}")
                cnt += 1
        
        skeleton.append("};")  # C++类声明需要分号
        return "\n".join(skeleton) if cnt else None
    elif language == "javascript":
        # JavaScript类骨架生成 - 处理ES6+ class语法
        skeleton = []
        cnt = 0
        
        # 获取类声明部分 (class ClassName extends ParentClass)
        for child in masked_node.children[:-1]:
            skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
        skeleton.append("{")
        
        # 处理类体
        class_body = masked_node.children[-1]  # class的body在最后
        
        for child in class_body.children:
            if child.type == "method_definition":
                # 提取方法声明部分（包括constructor、普通方法、static方法等）
                method_declaration = []
                for grandchild in child.children[:-1]:  # 排除方法体
                    method_declaration.append(all_codes[grandchild.start_byte: grandchild.end_byte].decode("utf-8"))
                skeleton.append(" ".join(method_declaration) + " {}")
                cnt += 1
            elif child.type == "field_definition":
                # 处理类字段（ES2022+）
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            elif child.type == "property_identifier":
                # 处理属性标识符
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
        
        skeleton.append("}")
        return "\n".join(skeleton) if cnt else None
    elif language == "typescript":
        # TypeScript类骨架生成，使用tree-sitter解析
        skeleton = []
        cnt = 0
        
        # 获取类声明部分（除了类体）
        for child in masked_node.children[:-1]:
            skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
        skeleton.append("{")
        
        # 处理类体
        class_body = masked_node.children[-1]  # 类体通常在最后一个子节点
        
        for child in class_body.children:
            if child.type == "field_definition":
                # 处理属性定义
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            elif child.type == "method_definition":
                # 处理方法定义
                method_parts = []
                for grandchild in child.children[:-1]:  # 排除方法体
                    method_parts.append(all_codes[grandchild.start_byte: grandchild.end_byte].decode("utf-8"))
                skeleton.append(" ".join(method_parts) + " {}")
                cnt += 1
            elif child.type == "public_field_definition":
                # 处理public字段
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            elif child.type == "method_signature":
                # 处理接口中的方法签名
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
                cnt += 1
        
        skeleton.append("}")
        return "\n".join(skeleton) if cnt else None
    elif language == "c_sharp":
        # C#类骨架生成，使用tree-sitter解析
        skeleton = []
        cnt = 0
        
        # 获取类声明部分（除了类体）
        for child in masked_node.children[:-1]:
            skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
        skeleton.append("{")
        
        # 处理类体
        class_body = masked_node.children[-1]  # 类体通常在最后一个子节点
        
        for child in class_body.children:
            if child.type == "field_declaration":
                # 处理字段声明
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            elif child.type == "property_declaration":
                # 处理属性声明
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            elif child.type == "method_declaration":
                # 处理方法声明
                method_parts = []
                for grandchild in child.children[:-1]:  # 排除方法体
                    method_parts.append(all_codes[grandchild.start_byte: grandchild.end_byte].decode("utf-8"))
                skeleton.append(" ".join(method_parts) + " {}")
                cnt += 1
            elif child.type == "constructor_declaration":
                # 处理构造函数
                constructor_parts = []
                for grandchild in child.children[:-1]:  # 排除构造函数体
                    constructor_parts.append(all_codes[grandchild.start_byte: grandchild.end_byte].decode("utf-8"))
                skeleton.append(" ".join(constructor_parts) + " {}")
                cnt += 1
            elif child.type == "destructor_declaration":
                # 处理析构函数
                destructor_parts = []
                for grandchild in child.children[:-1]:  # 排除析构函数体
                    destructor_parts.append(all_codes[grandchild.start_byte: grandchild.end_byte].decode("utf-8"))
                skeleton.append(" ".join(destructor_parts) + " {}")
                cnt += 1
        
        skeleton.append("}")
        return "\n".join(skeleton) if cnt else None
    elif language == "php":
        # PHP类骨架生成，使用tree-sitter解析
        skeleton = []
        cnt = 0
        
        # 获取类声明部分（除了类体）
        for child in masked_node.children[:-1]:
            skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
        skeleton.append("{")
        
        # 处理类体
        class_body = masked_node.children[-1]  # 类体通常在最后一个子节点
        
        for child in class_body.children:
            if child.type == "property_declaration":
                # 处理属性声明
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            elif child.type == "const_declaration":
                # 处理常量声明
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            elif child.type == "method_declaration":
                # 处理方法声明
                method_parts = []
                for grandchild in child.children[:-1]:  # 排除方法体
                    method_parts.append(all_codes[grandchild.start_byte: grandchild.end_byte].decode("utf-8"))
                skeleton.append(" ".join(method_parts) + " {}")
                cnt += 1
            elif child.type == "function_definition":
                # 处理函数定义（在类中的方法）
                func_parts = []
                for grandchild in child.children[:-1]:  # 排除函数体
                    func_parts.append(all_codes[grandchild.start_byte: grandchild.end_byte].decode("utf-8"))
                skeleton.append(" ".join(func_parts) + " {}")
                cnt += 1
        
        skeleton.append("}")
        return "\n".join(skeleton) if cnt else None
    elif language == "go":
        # Go语言"类"骨架生成 - 处理type声明、struct和interface
        skeleton = []
        cnt = 0
        
        if masked_node.type == "type_declaration":
            # 处理 type MyStruct struct { ... } 或 type MyInterface interface { ... }
            type_name = ""
            type_spec = None
            
            # 获取类型名称和类型规范
            for child in masked_node.children:
                if child.type == "type_spec":
                    type_spec = child
                    # 获取类型名称
                    for grandchild in child.children:
                        if grandchild.type == "type_identifier":
                            type_name = all_codes[grandchild.start_byte: grandchild.end_byte].decode("utf-8")
                            break
                    break
            
            if type_spec:
                # 构建类型声明开头
                skeleton.append(f"type {type_name}")
                
                # 查找struct_type或interface_type
                for child in type_spec.children:
                    if child.type == "struct_type":
                        skeleton.append("struct {")
                        # 处理结构体字段
                        for grandchild in child.children:
                            if grandchild.type == "field_declaration_list":
                                for field in grandchild.children:
                                    if field.type == "field_declaration":
                                        skeleton.append(all_codes[field.start_byte: field.end_byte].decode("utf-8"))
                        skeleton.append("}")
                        
                        # 查找关联的方法（在同一文件中定义的方法）
                        # 注意：Go的方法是在类型外部定义的，这里只能提取结构体本身
                        
                    elif child.type == "interface_type":
                        skeleton.append("interface {")
                        # 处理接口方法
                        for grandchild in child.children:
                            if grandchild.type == "method_spec_list":
                                for method in grandchild.children:
                                    if method.type == "method_spec":
                                        skeleton.append(all_codes[method.start_byte: method.end_byte].decode("utf-8"))
                                        cnt += 1
                        skeleton.append("}")
                        
        elif masked_node.type == "struct_type":
            # 直接的struct类型
            skeleton.append("struct {")
            for child in masked_node.children:
                if child.type == "field_declaration_list":
                    for field in child.children:
                        if field.type == "field_declaration":
                            skeleton.append(all_codes[field.start_byte: field.end_byte].decode("utf-8"))
            skeleton.append("}")
            
        elif masked_node.type == "interface_type":
            # 直接的interface类型
            skeleton.append("interface {")
            for child in masked_node.children:
                if child.type == "method_spec_list":
                    for method in child.children:
                        if method.type == "method_spec":
                            skeleton.append(all_codes[method.start_byte: method.end_byte].decode("utf-8"))
                            cnt += 1
            skeleton.append("}")
            
        # 对于结构体，我们可能需要查找相关的方法
        # 但由于Go的方法是在类型外部定义的，这需要额外的逻辑来关联
        
        return "\n".join(skeleton) if skeleton else None
    elif language == "rust":
        node_types = utils.language_symbols["rust"]
        for node in ast.walk():
            if node.type in node_types["CLASS_TYPE"]:
                if node.type == "struct_item":
                    # 处理结构体：struct Name { ... }
                    struct_name = utils.get_definition_name(node, node_types)
                    if struct_name:
                        skeleton_parts.append(f"struct {struct_name};")
                elif node.type == "enum_item":
                    # 处理枚举：enum Name { ... }
                    enum_name = utils.get_definition_name(node, node_types)
                    if enum_name:
                        skeleton_parts.append(f"enum {enum_name} {{}}")
                elif node.type == "trait_item":
                    # 处理特征：trait Name { ... }
                    trait_name = utils.get_definition_name(node, node_types)
                    if trait_name:
                        skeleton_parts.append(f"trait {trait_name} {{}}")
                elif node.type == "impl_item":
                    # 处理实现块：impl Name { ... } 或 impl Trait for Type { ... }
                    impl_signature = code[node.start_byte:node.end_byte].decode('utf-8')
                    # 提取impl签名部分（到第一个{之前）
                    impl_header = impl_signature.split('{')[0].strip()
                    skeleton_parts.append(f"{impl_header} {{}}")
    elif language == "r":
        # R语言类骨架生成：处理R6类、S4类、setClass等
        skeleton_parts = []
        
        for node in nodes:
            if node.type == "call":
                # 检查是否是类定义调用
                call_text = code[node.start_byte:node.end_byte].decode('utf-8')
                
                # 处理 R6Class 定义
                if "R6Class" in call_text:
                    # 提取 R6Class 的基本结构
                    lines = call_text.split('\n')
                    class_name = ""
                    for line in lines:
                        if "<-" in line and "R6Class" in line:
                            class_name = line.split("<-")[0].strip()
                            break
                    if class_name:
                        skeleton_parts.append(f"{class_name} <- R6Class(\"ClassName\", list())")
                
                # 处理 setClass 定义 (S4类)
                elif "setClass" in call_text:
                    # 提取 setClass 的基本结构
                    lines = call_text.split('\n')
                    for line in lines:
                        if "setClass" in line:
                            # 提取类名
                            if '"' in line:
                                class_name = line.split('"')[1]
                                skeleton_parts.append(f'setClass("{class_name}", slots = list())')
                            break
                
                # 处理 setRefClass 定义
                elif "setRefClass" in call_text:
                    lines = call_text.split('\n')
                    for line in lines:
                        if "setRefClass" in line:
                            if '"' in line:
                                class_name = line.split('"')[1]
                                skeleton_parts.append(f'setRefClass("{class_name}", fields = list())')
                            break
            
            elif node.type == "assignment":
                # 处理赋值形式的类定义
                assignment_text = code[node.start_byte:node.end_byte].decode('utf-8')
                if "R6Class" in assignment_text or "setClass" in assignment_text:
                    # 提取变量名
                    if "<-" in assignment_text:
                        var_name = assignment_text.split("<-")[0].strip()
                        if "R6Class" in assignment_text:
                            skeleton_parts.append(f"{var_name} <- R6Class(\"ClassName\", list())")
                        elif "setClass" in assignment_text:
                            skeleton_parts.append(f"{var_name} <- setClass(\"ClassName\", slots = list())")
        
        return '\n'.join(skeleton_parts)
    elif language == "ruby":
        # Ruby类骨架生成：支持class定义和module定义
        skeleton_parts = []
        lines = masked_code.split("\n")
        
        for line in lines:
            stripped_line = line.strip()
            # 处理类定义
            if stripped_line.startswith("class ") and not stripped_line.endswith("end"):
                # 提取类名和继承关系
                class_def = stripped_line
                if "<" in class_def:  # 有继承
                    skeleton_parts.append(f"{class_def}")
                else:  # 无继承
                    skeleton_parts.append(f"{class_def}")
                # 添加缩进和end
                indent = len(line) - len(line.lstrip())
                skeleton_parts.append(' ' * indent + 'end')
            
            # 处理模块定义
            elif stripped_line.startswith("module ") and not stripped_line.endswith("end"):
                module_def = stripped_line
                skeleton_parts.append(f"{module_def}")
                # 添加缩进和end
                indent = len(line) - len(line.lstrip())
                skeleton_parts.append(' ' * indent + 'end')
        
        return '\n'.join(skeleton_parts)
    elif language == "scala":
        # Scala类骨架生成：支持class、object、trait、case class等
        skeleton_parts = []
        
        if masked_node.type == "class_definition":
            # 处理 class 定义
            for child in masked_node.children:
                if child.type == "template_body":
                    break
                else:
                    skeleton_parts.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton_parts.append("{}")
            
        elif masked_node.type == "object_definition":
            # 处理 object 定义
            for child in masked_node.children:
                if child.type == "template_body":
                    break
                else:
                    skeleton_parts.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton_parts.append("{}")
            
        elif masked_node.type == "trait_definition":
            # 处理 trait 定义
            for child in masked_node.children:
                if child.type == "template_body":
                    break
                else:
                    skeleton_parts.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton_parts.append("{}")
            
        elif masked_node.type == "case_class_definition":
            # 处理 case class 定义
            for child in masked_node.children:
                if child.type == "template_body":
                    break
                else:
                    skeleton_parts.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            # case class 可能没有body，如果有则添加{}
            if any(child.type == "template_body" for child in masked_node.children):
                skeleton_parts.append("{}")
        
        return " ".join(skeleton_parts)
    elif language == "kotlin":
        # Kotlin类骨架生成：支持class、interface、object、data class等，使用tree-sitter节点
        skeleton_parts = []
        
        if masked_node.type == "class_declaration":
            # 处理 class 定义，包括data class
            for child in masked_node.children:
                if child.type == "class_body":
                    break
                else:
                    skeleton_parts.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton_parts.append("{}")
            
        elif masked_node.type == "interface_declaration":
            # 处理 interface 定义
            for child in masked_node.children:
                if child.type == "class_body":
                    break
                else:
                    skeleton_parts.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton_parts.append("{}")
            
        elif masked_node.type == "object_declaration":
            # 处理 object 定义
            for child in masked_node.children:
                if child.type == "class_body":
                    break
                else:
                    skeleton_parts.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton_parts.append("{}")
        
        return " ".join(skeleton_parts)
    elif language == "perl":
        # Perl类骨架生成：支持package定义，使用tree-sitter节点
        skeleton_parts = []
        
        if masked_node.type == "package_declaration":
            # 处理 package 定义
            for child in masked_node.children:
                if child.type == "block":  # 假设块节点
                    break
                else:
                    skeleton_parts.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton_parts.append("{ }")  # 添加空块
        
        return " ".join(skeleton_parts)
    elif language == "swift":
        # Swift类骨架生成：提取访问修饰符、类名、继承关系、协议实现
        skeleton = []
        
        if masked_node.type == "class_declaration":
            # 处理类声明 class MyClass: SuperClass, Protocol {}
            for child in masked_node.children:
                if child.type == "class_body":  # 类体，跳过
                    break
                else:
                    # 提取访问修饰符、class关键字、类名、继承等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        elif masked_node.type == "struct_declaration":
            # 处理结构体声明 struct MyStruct: Protocol {}
            for child in masked_node.children:
                if child.type == "struct_body":  # 结构体体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        elif masked_node.type == "protocol_declaration":
            # 处理协议声明 protocol MyProtocol {}
            for child in masked_node.children:
                if child.type == "protocol_body":  # 协议体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        elif masked_node.type == "extension_declaration":
            # 处理扩展声明 extension MyClass {}
            for child in masked_node.children:
                if child.type == "extension_body":  # 扩展体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        else:
            # 其他类型的类声明，通用处理
            for child in masked_node.children:
                if child.type in ["class_body", "struct_body", "protocol_body", "extension_body"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
        
        return " ".join(skeleton)
    elif language == "zig":
        # Zig结构体/联合体骨架生成：提取类型名、字段等
        skeleton = []
        
        if masked_node.type in ["ContainerDecl", "struct", "enum", "union"]:
            # 处理容器声明 const MyStruct = struct {}
            for child in masked_node.children:
                if child.type == "Block":  # 容器体，跳过
                    break
                else:
                    # 提取const、结构体名、struct关键字等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        else:
            # 其他类型的声明，通用处理
            for child in masked_node.children:
                if child.type == "Block":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
        
        return " ".join(skeleton)
    elif language == "verilog":
        # Verilog模块/接口骨架生成：提取模块名、端口列表等
        skeleton = []
        
        if masked_node.type == "module_declaration":
            # 处理模块声明 module module_name(port_list);
            for child in masked_node.children:
                if child.type in ["module_or_generate_item", "endmodule"]:
                    # 跳过模块体内容和endmodule
                    break
                else:
                    # 提取module关键字、模块名、端口列表等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("endmodule")
            
        elif masked_node.type == "interface_declaration":
            # 处理接口声明 interface interface_name;
            for child in masked_node.children:
                if child.type in ["interface_or_generate_item", "endinterface"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("endinterface")
            
        elif masked_node.type == "package_declaration":
            # 处理包声明 package package_name;
            for child in masked_node.children:
                if child.type in ["package_or_generate_item_declaration", "endpackage"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("endpackage")
            
        elif masked_node.type == "class_declaration":
            # 处理类声明 class class_name;
            for child in masked_node.children:
                if child.type in ["class_item", "endclass"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("endclass")
            
        else:
            # 其他类型的声明，通用处理
            for child in masked_node.children:
                if child.type in ["module_or_generate_item", "interface_or_generate_item", 
                                "package_or_generate_item_declaration", "class_item"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("end")
        
        return " ".join(skeleton)
    elif language == "lua":
        # Lua类骨架生成：主要处理table构造器和模块定义
        skeleton = []
        
        if masked_node.type == "table_constructor":
            # 处理 local MyClass = {} 形式的类定义
            skeleton.append(all_codes[masked_node.start_byte: masked_node.end_byte].decode("utf-8").split('{')[0] + "{}")
            
        elif masked_node.type == "function_definition":
            # 处理 function MyClass:new() 形式的构造函数
            for child in masked_node.children:
                if child.type == "block":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("end")
            
        elif masked_node.type == "assignment_statement":
            # 处理 MyClass = {} 形式的类定义
            assignment_text = all_codes[masked_node.start_byte: masked_node.end_byte].decode("utf-8")
            if "{" in assignment_text:
                skeleton.append(assignment_text.split('{')[0] + "{}")
            else:
                skeleton.append(assignment_text)
        
        return " ".join(skeleton)


def generate_function_skeleton(masked_code, masked_node = None, language = "python", all_codes = None) -> str:
    """
    param masked_code 被遮盖部分的代码
    return 当前函数的骨架 函数名+签名等
    """
    if language == "python":
        skeleton = []
        lines = masked_code.split("\n")
        for line in lines:
            stripped_code = line.strip()
            if stripped_code.startswith("def") and ('):' in stripped_code or (')' in stripped_code and ':' in stripped_code)):
                lastidx = line.find(':') # 找到:的位置截取到这里就是完整的方法签名
                if lastidx != -1:
                    method_signature = line[: lastidx + 2] # 多+1
                    skeleton.append(method_signature)
                    indent = len(line) - len(line.lstrip())
                    skeleton.append(' ' * (indent + 4) + 'pass')
        return '\n'.join(skeleton)
    elif language == "java":
        skeleton = []
        for child in masked_node.children[:-1]:
            skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
        skeleton.append("{}")
        return " ".join(skeleton)
    elif language == "cpp":
        # C++函数骨架生成：提取返回类型、函数名、参数列表
        skeleton = []
        # 遍历函数定义的所有子节点，排除最后一个（函数体）
        for child in masked_node.children:
            if child.type == "compound_statement":  # 这是函数体，跳过
                break
            else:
                # 提取返回类型、函数名、参数列表等
                skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
        
        # 添加空的函数体
        skeleton.append("{}")
        return " ".join(skeleton)
    elif language == "javascript":
        # JavaScript函数骨架生成 - 处理多种函数定义方式
        skeleton = []
        
        if masked_node.type == "function_declaration":
            # 处理 function test(config) {} 形式
            for child in masked_node.children:
                if child.type == "statement_block":  # 函数体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
            
        elif masked_node.type == "arrow_function":
            # 处理箭头函数 (config) => {} 形式
            for child in masked_node.children:
                if child.type == "statement_block":  # 函数体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
            
        elif masked_node.type == "function_expression":
            # 处理函数表达式 const test = function(config) {} 形式
            # 需要找到父节点来获取完整的赋值语句
            parent = masked_node.parent
            if parent and parent.type == "variable_declarator":
                # 获取变量名
                var_name = all_codes[parent.children[0].start_byte: parent.children[0].end_byte].decode("utf-8")
                skeleton.append(f"const {var_name} = function")
                
                # 获取参数列表
                for child in masked_node.children:
                    if child.type == "formal_parameters":
                        skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
                        break
                skeleton.append("{}")
            else:
                # 匿名函数表达式
                for child in masked_node.children:
                    if child.type == "statement_block":
                        break
                    else:
                        skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
                skeleton.append("{}")
                
        elif masked_node.type == "method_definition":
            # 处理对象方法 test(config) {} 形式
            for child in masked_node.children:
                if child.type == "statement_block":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
            
        else:
            # 其他类型的函数，通用处理
            for child in masked_node.children:
                if child.type in ["statement_block", "expression_statement"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
        
        return " ".join(skeleton)
    elif language == "typescript":
        # TypeScript函数骨架生成 - 处理多种函数定义方式和类型注解
        skeleton = []
        
        if masked_node.type == "function_declaration":
            # 处理 function test(config: Config): ReturnType {} 形式
            for child in masked_node.children:
                if child.type == "statement_block":  # 函数体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
            
        elif masked_node.type == "arrow_function":
            # 处理箭头函数 (config: Config): ReturnType => {} 形式
            for child in masked_node.children:
                if child.type == "statement_block":  # 函数体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
            
        elif masked_node.type == "function_expression":
            # 处理函数表达式 const test = function(config: Config): ReturnType {} 形式
            parent = masked_node.parent
            if parent and parent.type == "variable_declarator":
                # 获取变量名
                var_name = all_codes[parent.children[0].start_byte: parent.children[0].end_byte].decode("utf-8")
                skeleton.append(f"const {var_name} = function")
                
                # 获取参数列表和返回类型
                for child in masked_node.children:
                    if child.type in ["formal_parameters", "type_annotation"]:
                        skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
                    elif child.type == "statement_block":
                        break
                skeleton.append("{}")
            else:
                # 匿名函数表达式
                for child in masked_node.children:
                    if child.type == "statement_block":
                        break
                    else:
                        skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
                skeleton.append("{}")
                
        elif masked_node.type == "method_definition":
            # 处理对象方法 test(config: Config): ReturnType {} 形式
            for child in masked_node.children:
                if child.type == "statement_block":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
            
        elif masked_node.type == "method_signature":
            # 处理接口中的方法签名
            skeleton.append(all_codes[masked_node.start_byte: masked_node.end_byte].decode("utf-8"))
            
        else:
            # 其他类型的函数，通用处理
            for child in masked_node.children:
                if child.type in ["statement_block", "expression_statement"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
        
        return " ".join(skeleton)
    elif language == "c_sharp":
        # C#函数骨架生成：提取访问修饰符、返回类型、函数名、参数列表
        skeleton = []
        
        if masked_node.type == "method_declaration":
            # 处理方法声明
            for child in masked_node.children:
                if child.type == "block":  # 这是方法体，跳过
                    break
                else:
                    # 提取访问修饰符、返回类型、方法名、参数列表等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            # 添加空的方法体
            skeleton.append("{}")
            
        elif masked_node.type == "constructor_declaration":
            # 处理构造函数
            for child in masked_node.children:
                if child.type == "block":  # 这是构造函数体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            skeleton.append("{}")
            
        elif masked_node.type == "destructor_declaration":
            # 处理析构函数
            for child in masked_node.children:
                if child.type == "block":  # 这是析构函数体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            skeleton.append("{}")
            
        elif masked_node.type == "property_declaration":
            # 处理属性声明（C#特有）
            for child in masked_node.children:
                if child.type == "accessor_list":  # 这是属性的get/set体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            skeleton.append("{ get; set; }")
            
        else:
            # 其他类型的函数，通用处理
            for child in masked_node.children:
                if child.type in ["block", "expression_statement"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
        
        return " ".join(skeleton)
    elif language == "php":
        # PHP函数骨架生成：提取访问修饰符、返回类型、函数名、参数列表
        skeleton = []
        
        if masked_node.type == "function_definition":
            # 处理函数定义 function test($param) {}
            for child in masked_node.children:
                if child.type == "compound_statement":  # 这是函数体，跳过
                    break
                else:
                    # 提取函数关键字、函数名、参数列表等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            # 添加空的函数体
            skeleton.append("{}")
            
        elif masked_node.type == "method_declaration":
            # 处理类方法声明 public function test($param) {}
            for child in masked_node.children:
                if child.type == "compound_statement":  # 这是方法体，跳过
                    break
                else:
                    # 提取访问修饰符、函数关键字、方法名、参数列表等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            skeleton.append("{}")
            
        elif masked_node.type == "anonymous_function_creation_expression":
            # 处理匿名函数 function($param) {}
            for child in masked_node.children:
                if child.type == "compound_statement":  # 这是函数体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            skeleton.append("{}")
            
        elif masked_node.type == "arrow_function":
            # 处理箭头函数 fn($param) => expression
            for child in masked_node.children:
                if child.type in ["compound_statement", "expression_statement"]:  # 这是函数体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            skeleton.append("{}")
            
        else:
            # 其他类型的函数，通用处理
            for child in masked_node.children:
                if child.type in ["compound_statement", "expression_statement"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
        
        return " ".join(skeleton)
    elif language == "go":
        # Go函数骨架生成：提取函数签名，排除函数体
        skeleton = []
        
        if masked_node.type == "function_declaration":
            # 处理普通函数声明 func functionName(params) returnType {}
            for child in masked_node.children:
                if child.type == "block":  # 这是函数体，跳过
                    break
                else:
                    # 提取func关键字、函数名、参数列表、返回类型等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            # 添加空的函数体
            skeleton.append("{}")
            
        elif masked_node.type == "method_declaration":
            # 处理方法声明 func (receiver) methodName(params) returnType {}
            for child in masked_node.children:
                if child.type == "block":  # 这是方法体，跳过
                    break
                else:
                    # 提取func关键字、接收者、方法名、参数列表、返回类型等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            skeleton.append("{}")
            
        else:
            # 其他类型的函数，通用处理
            for child in masked_node.children:
                if child.type == "block":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
        
        return " ".join(skeleton)
    elif language == "c":
        # C函数骨架生成：提取函数签名，排除函数体
        skeleton = []
        
        if masked_node.type == "function_definition":
            # 处理函数定义 returnType functionName(params) { ... }
            for child in masked_node.children:
                if child.type == "compound_statement":  # 这是函数体，跳过
                    break
                else:
                    # 提取返回类型、函数名、参数列表等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            # 添加空的函数体
            skeleton.append("{}") 
            
        else:
            # 其他类型的函数，通用处理
            for child in masked_node.children:
                if child.type == "compound_statement":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
        
        return " ".join(skeleton)
    elif language == "rust":
        # Rust函数骨架生成：提取函数签名，排除函数体
        skeleton = []
        
        if masked_node.type == "function_item":
            # 处理函数定义 fn function_name(params) -> return_type { ... }
            for child in masked_node.children:
                if child.type == "block":  # 这是函数体，跳过
                    break
                else:
                    # 提取fn关键字、函数名、参数列表、返回类型等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            
            # 添加空的函数体
            skeleton.append("{}")
            
        else:
            # 其他类型的函数，通用处理
            for child in masked_node.children:
                if child.type == "block":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
        
        return " ".join(skeleton)
    elif language == "r":
        # R语言函数骨架生成：提取函数签名并添加空函数体
        skeleton = []
        
        if masked_node.type == "assignment":
            # 处理 func_name <- function(args) { ... } 形式
            assignment_text = all_codes[masked_node.start_byte: masked_node.end_byte].decode("utf-8")
            
            if "function" in assignment_text and "<-" in assignment_text:
                # 提取函数名
                func_name = assignment_text.split("<-")[0].strip()
                
                # 查找 function 关键字和参数列表
                func_start = assignment_text.find("function")
                if func_start != -1:
                    # 查找参数列表的结束位置
                    paren_count = 0
                    args_start = assignment_text.find("(", func_start)
                    args_end = -1
                    
                    if args_start != -1:
                        for i in range(args_start, len(assignment_text)):
                            if assignment_text[i] == "(":
                                paren_count += 1
                            elif assignment_text[i] == ")":
                                paren_count -= 1
                                if paren_count == 0:
                                    args_end = i
                                    break
                    
                    if args_end != -1:
                        args_part = assignment_text[args_start:args_end+1]
                        skeleton.append(f"{func_name} <- function{args_part} {{}}")
                    else:
                        skeleton.append(f"{func_name} <- function() {{}}")
                else:
                    skeleton.append(f"{func_name} <- function() {{}}")
            else:
                # 其他赋值，保持原样但添加空体
                skeleton.append(assignment_text.split("{")[0].strip() + " {}")
                
        elif masked_node.type == "function_definition":
            # 处理直接的函数定义
            func_text = all_codes[masked_node.start_byte: masked_node.end_byte].decode("utf-8")
            
            # 查找函数体的开始位置（第一个 {）
            brace_pos = func_text.find("{")
            if brace_pos != -1:
                func_signature = func_text[:brace_pos].strip()
                skeleton.append(f"{func_signature} {{}}")
            else:
                skeleton.append(func_text + " {}")
                
        elif masked_node.type == "call":
            # 处理函数调用形式的定义（如某些特殊的R函数定义）
            call_text = all_codes[masked_node.start_byte: masked_node.end_byte].decode("utf-8")
            
            if "function" in call_text:
                # 提取到第一个 { 之前的部分
                brace_pos = call_text.find("{")
                if brace_pos != -1:
                    func_signature = call_text[:brace_pos].strip()
                    skeleton.append(f"{func_signature} {{}}")
                else:
                    skeleton.append(call_text + " {}")
            else:
                skeleton.append(call_text)
                
        else:
            # 通用处理：提取到函数体之前的所有内容
            func_text = all_codes[masked_node.start_byte: masked_node.end_byte].decode("utf-8")
            
            # 查找函数体（通常是 { ... }）
            brace_pos = func_text.find("{")
            if brace_pos != -1:
                func_signature = func_text[:brace_pos].strip()
                skeleton.append(f"{func_signature} {{}}")
            else:
                # 如果没有找到 {，可能是单行函数，保持原样但确保有函数体
                if "function" in func_text:
                    skeleton.append(func_text.strip() + " {}")
                else:
                    skeleton.append(func_text)
        
        return " ".join(skeleton)
    elif language == "ruby":
        # Ruby函数骨架生成：支持def方法定义
        skeleton = []
        lines = masked_code.split("\n")
        
        for line in lines:
            stripped_line = line.strip()
            # 处理方法定义
            if stripped_line.startswith("def ") and not stripped_line.endswith("end"):
                # 提取方法签名
                method_signature = stripped_line
                skeleton.append(method_signature)
                
                # 添加缩进和end
                indent = len(line) - len(line.lstrip())
                skeleton.append(' ' * indent + 'end')
            
            # 处理单行方法定义（如果有的话）
            elif "def " in stripped_line and ";" in stripped_line:
                # 单行方法定义，转换为多行格式
                parts = stripped_line.split(";")
                method_part = parts[0].strip()
                skeleton.append(method_part)
                indent = len(line) - len(line.lstrip())
                skeleton.append(' ' * indent + 'end')
        
        return '\n'.join(skeleton)
    elif language == "scala":
        # Scala函数骨架生成：支持def方法定义
        skeleton = []
        
        if masked_node.type == "function_definition":
            # 处理 def 方法定义
            for child in masked_node.children:
                if child.type == "block":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
            
        elif masked_node.type == "function_declaration":
            # 处理抽象方法声明（在trait中）
            skeleton.append(all_codes[masked_node.start_byte: masked_node.end_byte].decode("utf-8"))
            
        elif masked_node.type == "val_definition" or masked_node.type == "var_definition":
            # 处理函数值定义 val/var func = (x: Int) => x + 1
            for child in masked_node.children:
                if child.type == "lambda_expression":
                    # 提取lambda表达式的签名部分
                    for lambda_child in child.children:
                        if lambda_child.type == "block":
                            break
                        else:
                            skeleton.append(all_codes[lambda_child.start_byte: lambda_child.end_byte].decode("utf-8"))
                    skeleton.append("{}")
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
        
        return " ".join(skeleton)
    elif language == "kotlin":
        # Kotlin函数骨架生成：支持fun函数定义，使用tree-sitter节点
        skeleton = []
        
        if masked_node.type == "function_declaration":
            # 处理 fun 函数定义
            for child in masked_node.children:
                if child.type == "function_body":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
            
        elif masked_node.type == "lambda_literal":
            # 处理 lambda 表达式 { ... }
            skeleton.append(all_codes[masked_node.start_byte: masked_node.children[0].end_byte].decode("utf-8"))  # 提取参数部分如果有
            skeleton.append("{}")
            
        elif masked_node.type == "function_value":
            # 处理函数值 val func: (Int) -> Int = { it + 1 }
            for child in masked_node.children:
                if child.type == "lambda_literal":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{}")
        
        return " ".join(skeleton)
    elif language == "perl":
        # Perl函数骨架生成：支持sub函数定义，使用tree-sitter节点
        skeleton = []
        
        if masked_node.type == "function_definition":
            # 处理 sub 函数定义
            for child in masked_node.children:
                if child.type == "block":  # 函数体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")  # 添加空函数体
        
        return " ".join(skeleton)
    elif language == "swift":
        # Swift函数骨架生成：提取访问修饰符、函数名、参数列表、返回类型
        skeleton = []
        
        if masked_node.type == "function_declaration":
            # 处理函数声明 func myFunction(param: Type) -> ReturnType {}
            for child in masked_node.children:
                if child.type == "function_body":  # 函数体，跳过
                    break
                else:
                    # 提取访问修饰符、func关键字、函数名、参数列表、返回类型等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        elif masked_node.type == "init_declaration":
            # 处理初始化器 init(param: Type) {}
            for child in masked_node.children:
                if child.type == "function_body":  # 初始化器体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        elif masked_node.type == "deinit_declaration":
            # 处理析构器 deinit {}
            for child in masked_node.children:
                if child.type == "function_body":  # 析构器体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        elif masked_node.type == "subscript_declaration":
            # 处理下标声明 subscript(index: Int) -> Type {}
            for child in masked_node.children:
                if child.type == "accessor_block":  # 访问器块，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        else:
            # 其他类型的函数声明，通用处理
            for child in masked_node.children:
                if child.type in ["function_body", "accessor_block"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
        
        return " ".join(skeleton)
    elif language == "zig":
        # Zig函数骨架生成：提取函数名、参数列表、返回类型
        skeleton = []
        
        if masked_node.type in ["FnProto", "Decl"]:
            # 处理函数声明 fn myFunction(param: type) returnType {}
            for child in masked_node.children:
                if child.type == "Block":  # 函数体，跳过
                    break
                else:
                    # 提取fn关键字、函数名、参数列表、返回类型等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        elif masked_node.type == "TestDecl":
            # 处理测试声明 test "test name" {}
            for child in masked_node.children:
                if child.type == "Block":  # 测试体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        elif masked_node.type == "VarDecl":
            # 处理变量声明中的函数 const myFunc = fn() void {}
            for child in masked_node.children:
                if child.type == "Block":  # 函数体，跳过
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
            
        else:
            # 其他类型的函数声明，通用处理
            for child in masked_node.children:
                if child.type == "Block":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("{ }")
        
        return " ".join(skeleton)
    elif language == "verilog":
        # Verilog函数/任务骨架生成：提取函数名、参数列表、返回类型
        skeleton = []
        
        if masked_node.type == "function_declaration":
            # 处理函数声明 function [return_type] function_name;
            for child in masked_node.children:
                if child.type in ["function_statement_or_null", "endfunction"]:
                    # 跳过函数体和endfunction
                    break
                else:
                    # 提取function关键字、返回类型、函数名、参数等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("endfunction")
            
        elif masked_node.type == "task_declaration":
            # 处理任务声明 task [automatic] task_name;
            for child in masked_node.children:
                if child.type in ["statement_or_null", "endtask"]:
                    # 跳过任务体和endtask
                    break
                else:
                    # 提取task关键字、automatic、任务名、参数等
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("endtask")
            
        elif masked_node.type == "class_method":
            # 处理类方法
            for child in masked_node.children:
                if child.type in ["statement_or_null", "function_statement_or_null"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("endfunction")
            
        elif masked_node.type == "dpi_import_export":
            # 处理DPI导入/导出函数
            skeleton.append(all_codes[masked_node.start_byte: masked_node.end_byte].decode("utf-8"))
            
        else:
            # 其他类型的函数声明，通用处理
            for child in masked_node.children:
                if child.type in ["statement_or_null", "function_statement_or_null", 
                                "endfunction", "endtask"]:
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("end")
        
        return " ".join(skeleton)
    elif language == "lua":
        # Lua函数骨架生成：处理多种函数定义方式
        skeleton = []
        
        if masked_node.type == "function_definition":
            # 处理 function name() 或 local function name() 形式
            for child in masked_node.children:
                if child.type == "block":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("end")
            
        elif masked_node.type == "local_function":
            # 处理 local function name() 形式
            for child in masked_node.children:
                if child.type == "block":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("end")
            
        elif masked_node.type == "method_definition":
            # 处理 function obj:method() 形式的方法定义
            for child in masked_node.children:
                if child.type == "block":
                    break
                else:
                    skeleton.append(all_codes[child.start_byte: child.end_byte].decode("utf-8"))
            skeleton.append("end")
            
        elif masked_node.type == "assignment_statement":
            # 处理 name = function() 形式的函数赋值
            assignment_text = all_codes[masked_node.start_byte: masked_node.end_byte].decode("utf-8")
            if "function" in assignment_text:
                # 提取到 function(...) 部分
                func_part = assignment_text.split("function")[0] + "function"
                # 查找参数列表
                for child in masked_node.children:
                    if child.type == "function_definition":
                        for func_child in child.children:
                            if func_child.type == "parameters":
                                func_part += all_codes[func_child.start_byte: func_child.end_byte].decode("utf-8")
                                break
                        break
                skeleton.append(func_part + " end")
            else:
                skeleton.append(assignment_text)
        
        return " ".join(skeleton)