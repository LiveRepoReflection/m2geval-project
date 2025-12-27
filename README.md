# M²G-Eval: Enhancing and Evaluating Multi-granularity Multilingual Code Generation

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

<p align="left">
    <a href="https://github.com/LiveRepoReflection/m2geval-project">☁️ Evaluation FrameWork / Construction Pipeline (<-- You are here) </a> 
</p>
<p align="left">
    <a href="https://livereporeflection.github.io/m2geval.github.io/index.html">🏆 Leaderboard </a>
</p>
<p align="left">
    <a href="https://livereporeflection.github.io/m2geval.github.io/home.html">🏠 Project Page </a>
</p>
<p align="left">
    <a href="#">📄 Paper(Coming soon) </a>
</p>
<p align="left">
    <a href="https://huggingface.co/datasets/Tswatery/m2geval">📊 Evaluation Data </a>
</p>
<p align="left">
    <a href="https://huggingface.co/datasets/Tswatery/m2geval-instruction">📚 Instruct Data </a>
</p>
<p align="left">
    <a href="https://huggingface.co/Tswatery/m2geval-coder">🤗 RepoReflectionCoder </a>
</p>

Welcome to the official repository for **M²G-Eval**. This project, described in detail in our paper "*M²G-Eval: Enhancing and Evaluating Multi-granularity Multilingual Code Generation*", aims to address the problem of incomplete evaluation in Large Language Model (LLM) assessments that focus on a single granularity.

**M²G-Eval** focuses on multi-granular testing during the LLM code generation process.

<center>
    <img style="border-radius: 0.3125em;
    box-shadow: 0 2px 4px 0 rgba(34,36,38,.12),0 2px 10px 0 rgba(34,36,38,.08);
                width: 500px;
                height: auto;
                " 
    src="./assets/intro.png">
    <br>
    <div style="color:orange; border-bottom: 1px solid #d9d9d9;
    display: inline-block;
    color: #999;
    padding: 2px;"></div>
</center>

## Core Components

This repository provides a suite of tools and datasets for advancing research in code intelligence:

1.  **`M²G-Eval` Evaluation Dataset**: A multi-granularity, multilingual datset with **rigorously and human-annotated test cases** across 18 programming languages (C, C#, Cpp, Go, Html, Java, JavaScript, Kotlin, Lua, Php, Python, R, Rust, Scala, Swift, TypeScript, Verilog and Zig). It uses Tree-Sitter generation with strong filtering methods, which reduces the pollution of pre-training data to a certain extent.

2.  **`M²G-Eval-Instruct` Dataset**: A large-scale (from The-Stack-V2, about 150K repositories), quality-filtered instruction-tuning dataset. This dataset was obtained through AST parsing and rigorous sample difficulty filtering, with the aim of training a model that can effectively handle multi-granularity code generation tasks.

3.  **`M²G-Eval-Coder` Models**: Starting with Qwen3-8B, we fine-tuned `M²G-Eval-Coder-SFT` using supervised training on the training set, and then trained `M²G-Eval-Coder-RL` using reinforcement learning with edit distance as the reward function. Our evaluation results show that the performance is close to that of models with larger parameters on some tasks.

4.  **Quality-Based and Automated Data Pipeline**: The entire collection pipeline is automated and equipped with a rigorous sample filtering module.

## Quality-Based and Automated Data Pipeline

Our Dataset is based on a quality-based and automated data pipeline. The pipeline described in the paper ensures that our dataset has moderate difficulty and reduces interference from pre-training data.

<center>
    <img style="border-radius: 0.3125em;
    box-shadow: 0 2px 4px 0 rgba(34,36,38,.12),0 2px 10px 0 rgba(34,36,38,.08);" 
    src="./assets/pipeline.png">
    <br>
    <div style="color:orange; border-bottom: 1px solid #d9d9d9;
    display: inline-block;
    color: #999;
    padding: 2px;"></div>
</center>

**Here are the key stages:**

1.  **Code Collection**: Collect code from open source and retrieve code from its repositories. 
2.  **Generation Dataset Using LLM**: After performing AST parsing on the code, a unique description is generated for each code segment.
3.  **Inference Candidate and Filter:** For each task, we generate a selection and filter using edit distance, keeping those with moderate difficulty because we believe that tasks that are too easy have no training significance, while tasks that are too difficult do not have strong repeatability. 

## Getting Started

### 1. Environment Setup

We recommend using Conda to manage the environment.

```bash
# Create and activate the conda environment
conda create -n m2geval python=3.12 -y
conda activate m2geval
```

### 2. Installation

For benchmark and pipeline, you need to  install the necessary dependencies.

```
pip install -r requirements.txt
```


### 3. Configuration

Our framework requires an LLM API key and a deployment address, so you'll need to configure some files. If you're using a public server, we strongly recommend using environment variables to protect your API key.

You need to register the model you want to evaluate in both config/config.py and config/model_config.json .

`model_config.json[MUST]`:

```json
{
    "DeepSeek-R1": {
        "url": "http://localhost:30000/v1", 
        "api_key": "dummy",
        "model_name": "deepseek-r1",
        "if_inference": true,
        "temperature": 0.7
    }
}
```

`config.py[MUST]`

```python
MODELS_LIST = [ "DeepSeek-R1" ]
```

#### Evaluation Metrics

**Length-Normalized Edit Similarity** 

$S \;=\; 1 \;-\; \frac{\mathrm{ED}(\hat{y},\,y^*)}{\max\!\big(|\hat{y}|,\,|y^*|\big)}$ 

Higher is better.

#### Task Example

<center>
    <img style="border-radius: 0.3125em;
    box-shadow: 0 2px 4px 0 rgba(34,36,38,.12),0 2px 10px 0 rgba(34,36,38,.08);
                width: 1000px;
                height: auto;
                " 
    src="./assets/taskexample.png">
    <br>
    <div style="color:orange; border-bottom: 1px solid #d9d9d9;
    display: inline-block;
    color: #999;
    padding: 2px;"></div>
</center>

#### Evaluation Model

After you have configured `model_config.json` and `config.py`, you can run it directly using `bash src/run.sh -- [your model-name]` .  The results of both the inference and similarity calculations will appear in the corresponding folders. If you want to verify specific languages, you can modify the `languages` array in `run.sh`.

### 4. Running the Data Construction Pipeline

Our data construction script corresponds to the language and array tuples. After you complete the configuration, you can run `bash src/dataset.sh`. If you want to specify the language and granularity, you can modify the `language` and `create_actions` arrays in the file.


## How to Cite

If you use `M²G-Eval` in your research, please cite our paper:

```bibtex

```

## License

This project is licensed under the **Apache 2.0 License**. See the [LICENSE](LICENSE) file for details.
