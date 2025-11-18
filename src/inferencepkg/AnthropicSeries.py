import anthropic

def AnthropicRequest(model, api_key, messages):
    """
    按照Anthropic的格式请求，使用messages进行请求
    """
    client = anthropic.Anthropic(api_key=api_key)
    inference_answer = ""

    print(f"{model} 开始输出")
    try:
        with client.messages.stream(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=32 * 1024
        )as stream:
            print("模型开始输出答案")
            for text in stream.text_stream:
                inference_answer += text
            print(f"\n\n已完成 完成原因{stream.get_final_message().stop_reason}")
    except Exception as e:
        print(f"{model} 请求失败，错误信息：{e}")
    return inference_answer.split("</think>")[-1].strip()