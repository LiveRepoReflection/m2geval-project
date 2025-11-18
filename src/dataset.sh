default_model="DeepSeek-V3"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            model="$2"
            shift 2
            ;; # break 
        -h|--help)
            echo "Usage: $0 [--model MODEL_NAME]"
            echo "  --model MODEL_NAME           指定要使用的模型 (默认: $default_model)"
            echo "  -h, --help                   显示此帮助信息"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 $0 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

if [ -z "$model" ]; then
    model="$default_model"
fi

echo "使用模型 $model"

rm -rf ../log/$model
echo "已删除$model 对应的日志文件夹"

# 定义 languages 数组

languages=("c" "c_sharp" "cpp" "go" "java" "php" "python" "javascript" "kotlin" "lua" "r" "rust" "scala" "typescript" "swift" "zig" "verilog" "html")

# 定义 actions 数组
create_actions=("class" "function" "block" "line")

# 记录开始时间
start_time=$(date +%s)

echo "Task started at $(date)"

遍历 languages 和 create_actions 进行创造测试数据集
rm -rf ./bench/*
echo "已删除旧的bench目录"
for language in "${languages[@]}"; do
    for action in "${create_actions[@]}"; do
        if [[ "$language" == "html" && ("$action" == "class" || "$action" == "function") ]]; then
            continue
        fi
        if [[ "$language" == "c" && "$action" == "class" ]]; then
            continue
        fi
        if [[ "$language" == "go" && "$action" == "class" ]]; then
            continue
        fi
        echo "Processing $language - $action"
        python3 create_test.py --repo_root_path ./repo/$language/ --task_level $action --process_language $language --inference_model $model
    done

# 记录结束时间
end_time=$(date +%s)

# 计算执行时间
duration=$((end_time - start_time))

echo "Task completed at $(date)"
echo "Total duration: $duration seconds"
