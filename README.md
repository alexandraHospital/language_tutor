# Language Tutor
Language Tutor is an AI-powered open-source application for practicing speaking foreign languages. Designed with privacy in mind, it keeps user data local and does not send it to external services. It uses lightweight models that can run either CPU-only or on a GPU, depending on the user's setup.

Language Tutor can provide a feedback stored in a markdown file.

## Setting environment
Clone the projet and create environment:
```bash
cd language_tutor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt 
```

## Installing Whisper
This project uses whisper.cpp for local speech-to-text transcription.
### 1. Clone whisper.cpp

```bash
cd /your/favorite/path/to/models
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
```

### 2. Download a whisper model
This project uses the tiny model by default:
```bash
sh ./models/download-ggml-model.sh tiny
```
The model will be downloaded as:
```bash
./models/ggml-tiny.bin
```

### 3. Build whisper.cpp
```bash
cmake -B build
cmake --build build -j --config Release
```

The Whisper CLI will then be available at:
```bash
build/bin/whisper-cli
```

## Installing Ollama
This project uses [Ollama](https://ollama.com/) to run the language model locally.

Ollama allows you to run LLMs directly on your computer without sending your conversations to an external API when using local models. Its local API is available at `http://localhost:11434`.

### 1. Install Ollama
Install Ollama with:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Then verify the installation:

```bash
ollama -v
```
### 2. Start Ollama

If Ollama is not already running as a system service, start it with:

```bash
ollama serve
```

Keep this terminal open while using the application.

If Ollama is installed as a systemd service, you can instead check its status with:

```bash
systemctl status ollama
```

and start it with:

```bash
sudo systemctl start ollama
```

Ollama exposes its local API on:

```text
http://localhost:11434
```

### 3. Choose your favorite LLM
Depending on your machine's hardware capabilities, you can choose either a lightweigted model for a lower resource usage and a larger model for better performance.

Models can be downloaded with:

```bash
ollama pull <model>
```

You can then check the models installed on your computer with:

```bash
ollama list
```

## Using an external API

The application can also be configured to use an external LLM API instead of a local model.

For example, you can connect it to providers such as Mistral AI or OpenAI, depending on the API implementation you choose.

When using an external provider, **your data is no longer processed exclusively on your local machine**. Any data sent to the provider is subject to the provider's own terms of service, privacy policy, data retention policies, and usage restrictions.

:warning: **Make sure you review the provider's terms and privacy policy before using an external API, especially if you are sending sensitive or personal information.** :warning:

Using an external API provider is configured through a `.env` file and a command-line option. See the **`Environement variables`** and **Usage** sections for more details.


## Piper
<i> coming soon...</i>
<!-- TODO -->

## Environement variables


The application uses a `.env` file to configure the LLM provider and the Whisper model.

| Variable                     | Description                                                                                                                                                 |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `BASE_URL`                   | Base URL of the LLM provider API. For a local Ollama instance, use `http://127.0.0.1:11434/v1`. For an external provider, use the provider's API base URL.  |
| `API_KEY`                    | API key used to authenticate with the selected external provider. This variable is not required when using Ollama locally, depending on your configuration. |
| `DEFAULT_WHISPER_PATH` | Path to the Whisper directory used for speech transcription, for example `/path/to/whisper.cpp`.                                                  |


## Usage
```bash
python3 tutor.py --help
usage: tutor.py [-h] [--api {mistral,openai,ollama}] [--model MODEL] [--device DEVICE] [--whisper_model WHISPER_MODEL] [--whisper_path WHISPER_PATH] [--language {fr,en,es,de,it,pt}]
                [--threads THREADS] [--logs_dir LOGS_DIR] [--high_quality]

Practice speaking a language with a local Whisper model and AI.

options:
  -h, --help            show this help message and exit
  --api {mistral,openai,ollama}
                        LLM API
  --model MODEL         Name of the LLM model to use (e.g., 'qwen3.5:2b', 'open-mistral-7b', llama3.2:3b). Check if model is available on the API (ollama or external) you use on
                        "api" option.
  --device DEVICE       ALSA audio device for capture (e.g., 'plughw:0,7'). Use 'arecord -l' to list devices.
  --whisper_model WHISPER_MODEL
                        Whisper model file.
  --whisper_path WHISPER_PATH
                        Path to the whisper.cpp directory, for example /path/to/whisper.cpp
  --language {fr,en,es,de,it,pt}
                        Language for transcription (e.g., 'en' for English, 'fr' for French).
  --threads THREADS     Number of CPU threads to use for Whisper.
  --logs_dir LOGS_DIR   Directory to save conversation logs (default: './logs').
  --high_quality        Enable high-quality mode (slower but more accurate transcription).
  ```
