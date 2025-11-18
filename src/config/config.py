
N_SAMPLES = 5
CLASS_RATIO = 0
FUNCTION_RATIO = 1
BLOCK_RATIO = 0
LINE_RATIO = 0
MODELS_LIST = [
    "DeepSeek-V3", "DeepSeek-R1",
    "DeepSeek-R1-Distill-Qwen-14B", "DeepSeek-R1-Distill-Llama-8B",
    "DeepSeek-R1-Distill-Qwen-32B", "DeepSeek-R1-Distill-Llama-70B",
    "DeepSeek-R1-0528-Qwen3-8B", "DeepSeek-R1-Distill-Qwen-7B",
    # above are deepseek 8 models
    "Qwen3-Coder-480B-A35B-Instruct", "Qwen3-Coder-30B-A3B-Instruct",
    # Qwen3 latest Coder 480B 30B
    "Qwen2.5-Coder-32B-Instruct",
    # Qwen2.5-Coder-32B
    "Qwen3-235B-A22B-Thinking-2507", "Qwen3-235B-A22B-Instruct-2507",
    # Qwen3 235B
    "Qwen3-30B-A3B-Thinking-2507", "Qwen3-30B-A3B-Instruct-2507",
    # Qwen3 30B
    "Qwen3-32B-Chat",  "Qwen3-32B-Think",
    "Qwen3-8B-Chat", "Qwen3-8B-Think",
    "Qwen3-14B-Think", "Qwen3-14B-Chat",  
    "Qwen3-4B-Chat", "Qwen3-4B-Think", 
    "Qwen3-1.7B-Think", "Qwen3-1.7B-Chat", 
    "Qwen3-0.6B-Chat",  "Qwen3-0.6B-Think",
    "Qwen3-8B-My-Instruct", "Qwen3-8B-RL-GSPO", "Qwen3-8B-RL-GRPO",
    # Qwen3 all kinds
    "QwQ-32B",
    # QwQ-32B
    "Seed-Coder-8B-Instruct", 
    "Kimi-K2-Instruct",
    "GLM-4.5",
    "Kimi-Dev-72B",
    # above are open models
    "claude-sonnet-4-20250514-thinking", 
    "claude-3-7-sonnet-20250219-thinking",
    "claude-3-7-sonnet-thinking",
    "claude-3-5-sonnet-20241022", 
    "claude-3-5-haiku-20241022",
    "claude-3-5-haiku-20241022", 
    "gpt-4o-2024-11-20", 
    "o1-mini-2024-09-12", 
    "o3-mini", 
    "o4-mini", 
    "gemini-2.5-pro", 
    "gemini-2.5-flash"
]


EXTERNAL_MODEL_CONFIGS = {} # jsonl配置模型


DEFAULT_MODEL_CONFIGS = {
    "DeepSeek-V3": {
        "url": "http://localhost:30000/v1",
        "api_key": "EMPTY",
        "model_name": "deepseek-v3",
        "temperature": 0.7
    },
    "DeepSeek-R1": {
        "url": "http://localhost:30000/v1",
        "api_key": "EMPTY",
        "model_name": "deepseek-r1",
        "temperature": 0.7
    }
}

def get_model_config(model_name):
    if model_name in EXTERNAL_MODEL_CONFIGS:
        return EXTERNAL_MODEL_CONFIGS[model_name]
    
    if model_name in DEFAULT_MODEL_CONFIGS:
        return DEFAULT_MODEL_CONFIGS[model_name]
    
    raise ValueError(f"No configuration found for model: {model_name}. Please register it first.")


def list_configured_models():
    configured = list(DEFAULT_MODEL_CONFIGS.keys()) + list(EXTERNAL_MODEL_CONFIGS.keys())
    return list(set(configured))