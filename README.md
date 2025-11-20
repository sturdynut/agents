# Local Ollama Agent System

A Python-based agent that uses Ollama to run locally downloaded LLM models. The agent reads a system prompt and task list from a configuration file, then plans and executes tasks sequentially.

## Features

- **Local Model Support**: Uses Ollama to run models entirely on your local machine
- **Task Planning**: Analyzes task lists and creates execution plans
- **Task Execution**: Executes tasks sequentially with context awareness
- **Flexible Configuration**: Supports both YAML and JSON configuration files
- **Conversation Context**: Maintains context across all tasks

## Prerequisites

1. **Ollama**: Install Ollama from [https://ollama.ai](https://ollama.ai)
2. **Python 3.7+**: Ensure Python is installed on your system
3. **Local Model**: Download a model using Ollama (e.g., `ollama pull llama3.2`)

## Installation

1. Clone or download this repository
2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a configuration file (YAML or JSON) with the following structure:

### YAML Example (`config.yaml`)

```yaml
# Ollama model name (must be downloaded locally)
model: "llama3.2"

# System prompt for the agent
system_prompt: |
  You are a helpful AI assistant that can plan and execute tasks.
  Analyze tasks carefully, break them down into steps, and execute them systematically.
  Provide clear progress updates and handle errors gracefully.

# List of tasks to plan and execute
tasks:
  - "Analyze the current project structure"
  - "Identify any missing dependencies"
  - "Create a summary of findings"

# Optional Ollama API settings
settings:
  temperature: 0.7
  max_tokens: 2048
  api_endpoint: "http://localhost:11434"
```

### JSON Example (`config.json`)

```json
{
  "model": "llama3.2",
  "system_prompt": "You are a helpful AI assistant...",
  "tasks": [
    "Analyze the current project structure",
    "Identify any missing dependencies",
    "Create a summary of findings"
  ],
  "settings": {
    "temperature": 0.7,
    "max_tokens": 2048,
    "api_endpoint": "http://localhost:11434"
  }
}
```

### Configuration Fields

- **model** (required): Name of the Ollama model to use (must be downloaded locally)
- **system_prompt** (optional): System prompt that defines the agent's behavior
- **tasks** (required): List of tasks (strings) to plan and execute
- **settings** (optional): Additional settings
  - **temperature** (default: 0.7): Sampling temperature (0.0-1.0)
  - **max_tokens** (default: 2048): Maximum tokens in response
  - **api_endpoint** (default: http://localhost:11434): Ollama API endpoint

## Usage

### Basic Usage

Run the agent with the default configuration file (`config.yaml`):

```bash
python agent.py
```

### Custom Configuration File

Specify a custom configuration file:

```bash
python agent.py my_config.yaml
```

or

```bash
python agent.py my_config.json
```

## How It Works

1. **Configuration Loading**: The agent loads the system prompt and task list from the config file
2. **Model Check**: Verifies that the specified Ollama model is available
3. **Planning Phase**: The agent analyzes all tasks and creates an execution plan
4. **Execution Phase**: The agent executes each task sequentially, maintaining context from previous tasks

## Example Output

```
Loading configuration from: config.yaml
Checking model availability: llama3.2

============================================================
PLANNING PHASE
============================================================

Analyzing 3 task(s)...
Tasks: Analyze the current project structure, Identify any missing dependencies, Create a summary of findings

Plan generated:
------------------------------------------------------------
[Generated plan from the model]
------------------------------------------------------------

============================================================
EXECUTION PHASE
============================================================

============================================================
TASK 1/3: Analyze the current project structure
============================================================

Execution Result:
------------------------------------------------------------
[Task execution result from the model]
------------------------------------------------------------

[... continues for each task ...]

============================================================
ALL TASKS COMPLETED
============================================================
```

## Available Models

You can use any model available in Ollama. Some popular options:

- `llama3.2` - Meta's Llama 3.2
- `mistral` - Mistral AI model
- `codellama` - Code-focused Llama variant
- `phi3` - Microsoft's Phi-3

Download models with:
```bash
ollama pull <model-name>
```

List available models:
```bash
ollama list
```

## Troubleshooting

### Model Not Found

If you see a warning about the model not being available:

1. Make sure Ollama is running: `ollama serve` (usually runs automatically)
2. Download the model: `ollama pull <model-name>`
3. Verify the model name in your config matches the downloaded model

### Connection Errors

If you get connection errors:

1. Ensure Ollama is running on the default port (11434)
2. Check the `api_endpoint` in your config if using a custom setup
3. Verify Ollama is accessible: `curl http://localhost:11434/api/tags`

### Import Errors

If you see import errors:

```bash
pip install -r requirements.txt
```

## License

This project is provided as-is for local use.

