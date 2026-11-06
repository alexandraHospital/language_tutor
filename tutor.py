
#!/usr/bin/env python3

import argparse
import datetime
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from ollama import chat
from dotenv import load_dotenv
from mistralai.client import Mistral
from openai import OpenAI

from piper import PiperVoice
import wave


DEFAULT_WHISPER_MODEL = "ggml-tiny.bin"
DEFAULT_PIPER_PATH = "/home/alex/Documents/python_projects/piper"
DEFAULT_LOGS_DIR = "./logs"
DEFAULT_ENV_PATH = "./.env"
DEFAULT_TUTOR_PROMPT_PATH = "./tutor_system_prompt.txt"
DEFAULT_FEEDBACK_PROMPT_PATH = "./feedback_system_prompt.txt"

LANGUAGE_MAP = {
    "fr": "French",
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
}


    
# --- Styles ---
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"
REVERSE = "\033[7m"
HIDDEN = "\033[8m"
STRIKETHROUGH = "\033[9m"

# --- Text colors (standard) ---
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# --- Text colors (light) ---
LIGHT_BLACK = "\033[90m"
LIGHT_RED = "\033[91m"
LIGHT_GREEN = "\033[92m"
LIGHT_YELLOW = "\033[93m"
LIGHT_BLUE = "\033[94m"
LIGHT_MAGENTA = "\033[95m"
LIGHT_CYAN = "\033[96m"
LIGHT_WHITE = "\033[97m"

API_LIST = ["mistral", "openai", "ollama", "opencode"] #TODO add hugging face

def load_prompt(path, name):
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"{name} file not found: {path}\n"
            f"Provide it or use --tutor_prompt / --feedback_prompt."
        )

def parse_args():
    DEFAULT_WHISPER_PATH = os.getenv("DEFAULT_WHISPER_PATH", "./models/whisper.cpp")

    parser = argparse.ArgumentParser(
        description="Practice speaking a language with a local Whisper model and AI."
    )

    parser.add_argument(
        "--api",
        default="ollama",
        choices=API_LIST,
        help="LLM API",
    ) # TODO
    
    parser.add_argument(
        "--model",
        default="llama3.2:3b",
        help="Name of the LLM model to use (e.g., 'qwen3.5:2b', 'open-mistral-7b', llama3.2:3b). Check if model is available on the API (ollama or external) you use on \"api\" option.",
    )

    parser.add_argument(
        "--device",
        default="plughw:0,7",
        help="ALSA audio device for capture (e.g., 'plughw:0,7'). Use 'arecord -l' to list devices.",
    )

    parser.add_argument(
        "--whisper_path",
        default=DEFAULT_WHISPER_PATH,
        help="Path to the whisper.cpp directory, for example /path/to/whisper.cpp",
    )

    parser.add_argument(
        "--whisper_model",
        default=DEFAULT_WHISPER_MODEL,
        help="Whisper model file, by default /path/to/whisper.cpp/models/.",
    )

    parser.add_argument(
        "--language",
        default="en",
        choices=list(LANGUAGE_MAP.keys()),
        help="Language for transcription (e.g., 'en' for English, 'fr' for French).",
    )

    parser.add_argument(
        "--tutor_prompt",
        default=DEFAULT_TUTOR_PROMPT_PATH,
        help=f"Path to the tutor system prompt file (default: '{DEFAULT_TUTOR_PROMPT_PATH}').",
    )

    parser.add_argument(
        "--feedback_prompt",
        default=DEFAULT_FEEDBACK_PROMPT_PATH,
        help=f"Path to the feedback system prompt file (default: '{DEFAULT_FEEDBACK_PROMPT_PATH}').",
    )

    # parser.add_argument(
    #     "--voice",
    #     action="store_true",
    #     help="Anwsers are read out loud.",
    # ) # TODO

    parser.add_argument(
        "--threads",
        type=int,
        default=8,
        help="Number of CPU threads to use for Whisper.",
    )

    parser.add_argument(
        "--logs_dir",
        default=DEFAULT_LOGS_DIR,
        help="Directory to save conversation logs (default: './logs').",
    )

    parser.add_argument(
        "--high_quality",
        action="store_true",
        help="Enable high-quality mode (slower but more accurate transcription).",
    )
    
    # parser.add_argument(
    #     "--manual-check",
    #     action="store_true",
    #     help="Check transcription manually before sending.",
    # ) # TODO

    return parser.parse_args()


class ConversationLogger:
    def __init__(self, logs_dir, language_name):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.conversation_path = self.logs_dir / f"session_{timestamp}_conversation.md"
        self.feedback_path = self.logs_dir / f"session_{timestamp}_feedback.md"
        self.language_name = language_name
        self._write_header(
            self.conversation_path,
            f"{self.language_name} Tutor Session - Conversation",
        )
        self._write_header(
            self.feedback_path,
            f"{self.language_name} Tutor Session - Feedback",
        )

    def _write_header(self, path, title):
        with path.open("w", encoding="utf-8") as file:
            file.write(f"{title}\n")
            file.write("=" * 60 + "\n")
            file.write(
                datetime.datetime.now().strftime("Started: %Y-%m-%d %H:%M:%S\n")
            )
            file.write("\n")

    def _append(self, path, text):
        with path.open("a", encoding="utf-8") as file:
            file.write(text)

    def write_user(self, text):
        self._append(self.conversation_path, f"<u>You:</u> {text}\n\n")

    def write_tutor(self, text):
        self._append(self.conversation_path, f"<u>Tutor:</u> {text}\n\n")

    def write_feedback(self, feedback):
        self._append(self.feedback_path, feedback + "\n")


class AudioRecorder:
    def __init__(self, device):
        self.device = device

    def record(self, output_path):
        print("Recording... Press ENTER to stop.")

        command = [
            "arecord",
            "-q",
            "-D",
            self.device,
            "-f",
            "S16_LE",
            "-r",
            "16000",
            "-c",
            "1",
            output_path,
        ]

        process = subprocess.Popen(command)

        try:
            input()
        except KeyboardInterrupt:
            pass
        finally:
            process.terminate()

            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        return Path(output_path)


class WhisperTranscriber:
    def __init__(
        self,
        whisper_path,
        whisper_model,
        language,
        threads,
        high_quality=False,
    ):
        self.whisper_path = Path(os.path.expanduser(whisper_path))
        self.whisper_model = self.whisper_model_path(whisper_model)
        self.language = language
        self.threads = threads
        self.high_quality = high_quality

        self.binary = self.whisper_path / "build" / "bin" / "whisper-cli"

        if not self.binary.exists():
            raise FileNotFoundError(
                f"Whisper binary not found: {self.binary}"
            )

        if not self.whisper_model.exists():
            raise FileNotFoundError(
                f"Whisper model not found: {self.whisper_model}"
            )

    def whisper_model_path(self, model):
        model_path = Path(model)

        if model_path.is_absolute():
            return model_path

        return self.whisper_path / "models" / model

    def transcribe(self, audio_path):
        command = [
            str(self.binary),
            "--model",
            str(self.whisper_model),
            "--file",
            str(audio_path),
            "--language",
            self.language,
            "--threads",
            str(self.threads),
            "--no-timestamps",
        ]

        if self.high_quality:
            command.extend([
                "--best-of",
                "5",
                "--beam-size",
                "5",
            ])

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Whisper transcription failed:\n"
                + result.stderr
            )

        return self._extract_transcription(result.stdout)

    @staticmethod
    def _extract_transcription(output):
        lines = []

        for line in output.splitlines():
            line = line.strip()

            if not line:
                continue

            # Ignore Whisper diagnostic lines.
            if line.startswith("["):
                continue

            lines.append(line)

        return " ".join(lines).strip()


class EnglishTutor:
    def __init__(self, api, model, tutor_prompt, feedback_prompt):
        self.api = api
        self.model = model
        self.tutor_prompt = tutor_prompt
        self.feedback_prompt = feedback_prompt
        load_dotenv()
        
        # LLM API
        api_key = os.getenv("API_KEY")
        base_url = os.getenv("BASE_URL")

        missing = []
        if self.api != "ollama" and not api_key:
            missing.append("API_KEY")
        if not base_url:
            missing.append("BASE_URL")
        if missing:
            raise RuntimeError(
                            f"Missing required environment variables: {', '.join(missing)}\n"
                            f"Expected them in: {DEFAULT_ENV_PATH}"
            )


        if self.api in ("ollama", "openai", "opencode"):
            if self.api == "opencode":
                default_headers = {"x-opencode-session": str(uuid.uuid4())}
            else:
                default_headers = None

            self.client = OpenAI(
                api_key="ollama" if self.api == "ollama" else api_key,
                base_url=base_url,
                default_headers=default_headers,
            )

            self.messages = [
                {
                    "role": "system",
                    "content": tutor_prompt,
                }
            ]
        elif self.api == "mistral":
            self.client = Mistral(api_key=api_key)

            self.messages = [
                {
                    "role": "system",
                    "content": tutor_prompt,
                }
            ]
        
        # TODO: add other API

    def test_connection(self):
        """Send a minimal request to check the model is reachable."""
        messages = [
            {"role": "user", "content": "Reply with exactly: OK"},
        ]

        if self.api in ("ollama", "openai", "opencode"):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
        elif self.api == "mistral":
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
            )

        if not response.choices[0].message.content:
            raise RuntimeError("Model returned an empty response.")

    def chat(self, user_text):
        self.messages.append(
            {
                "role": "user",
                "content": user_text,
            }
        )
        
        if self.api in ("ollama", "openai", "opencode"):
            if self.api == "opencode":
                default_headers = {"x-opencode-session": str(uuid.uuid4())}
            else:
                default_headers = None
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
        )
        elif self.api == "mistral":
            response = self.client.chat.complete(
                model=self.model,
                messages=self.messages,
        )

        assistant_text = response.choices[0].message.content.strip()

        self.messages.append(
            {
                "role": "assistant",
                "content": assistant_text,
            }
        )

        return assistant_text

    def feedback(self, conversation):
        messages = [
            {
                "role": "system",
                "content": self.feedback_prompt,
            },
            {
                "role": "user",
                "content": (
                    "Here is the complete transcript of the session.\n\n"
                    + conversation
                ),
            },
        ]

        if self.api in ("ollama", "openai", "opencode"):
            if self.api == "opencode":
                default_headers = {"x-opencode-session": str(uuid.uuid4())}
            else:
                default_headers = None
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
        elif self.api == "mistral":
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
        )

        return response.choices[0].message.content.strip()



def build_conversation_text(log_path):
    return log_path.read_text(encoding="utf-8")

def print_banner():
    banner = r"""
     _                                        
    | |                                       
    | |     __ _ _ __   __ _  __ _  __ _  ___ 
    | |    / _` | '_ \ / _` |/ _` |/ _` |/ _ \
    | |___| (_| | | | | (_| | (_| | (_| |  __/
    \_____/\__,_|_| |_|\__, |\__,_|\__, |\___|
                        __/ |       __/ |     
                       |___/       |___/      
       _____     _                              
      |_   _|   | |                             
        | |_   _| |_ ___  _ __                  
        | | | | | __/ _ \| '__|                 
        | | |_| | || (_) | |                    
        \_/\__,_|\__\___/|_|               v1.0              
                                          
    """
    print(f"{BOLD}{LIGHT_MAGENTA}{banner}{RESET}")

def main():
    load_dotenv(DEFAULT_ENV_PATH)
    args = parse_args()
    
    language_name = LANGUAGE_MAP[args.language]

    print_banner()

    print(f"{BOLD}{LIGHT_MAGENTA}{language_name}{RESET}")
    print(f"{DIM}─" + "─" * 58 + f"{RESET}")
    print(f"  {DIM}LLM API:{RESET}      {args.api}")
    print(f"  {DIM}BASE URL:{RESET}     {os.getenv('BASE_URL')}")
    print(f"  {DIM}LLM model:{RESET}    {args.model}")
    print(f"  {DIM}Whisper:{RESET}      {args.whisper_model}")
    print(f"{DIM}─" + "─" * 58 + f"{RESET}")
    print()

    try:
        # Get prompts
        tutor_prompt = load_prompt(args.tutor_prompt, "Tutor system prompt")
        feedback_prompt = load_prompt(args.feedback_prompt, "Feedback system prompt")
        final_prompt = tutor_prompt.replace("{%language%}", language_name)
        final_feedback_prompt = feedback_prompt.replace("{%language%}", language_name)

        tutor = EnglishTutor(args.api, args.model, final_prompt, final_feedback_prompt)

        # Test if model is available
        print("Testing LLM connection...")
        tutor.test_connection()

        # Initialize logger
        logger = ConversationLogger(args.logs_dir, language_name)

        # Initialize recorder
        recorder = AudioRecorder(args.device)

        # Initialize Whisper
        transcriber = WhisperTranscriber(
            whisper_path=args.whisper_path,
            whisper_model=args.whisper_model,
            language=args.language,
            threads=args.threads,
            high_quality=args.high_quality,
        )


    except Exception as error:
        print(f"Initialization error: {error}")
        sys.exit(1)

    print()
    print(f"{REVERSE}{BOLD} Ready! ", end=f"{RESET}")
    print()
    print()
    print(f"{BOLD}Speak {LIGHT_MAGENTA}{language_name}{RESET}{BOLD} into your microphone.{RESET}")
    print(f"  {CYAN}/feedback{RESET}  get feedback on your {language_name}")
    # print(f"  {CYAN}/voice to enable or disable reading out loud.") # TODO
    print(f"  {CYAN}/quit{RESET}      end the session")
    print()

    while True:
        try:
            command = input("Press ENTER to speak, or type a command: ").strip()

            if command == "/quit":
                print("Goodbye!")
                break

            if command == "/feedback":
                print()
                print("Generating feedback...")

                conversation = build_conversation_text(logger.conversation_path)
                feedback = tutor.feedback(conversation)

                print()
                print(feedback)

                logger.write_feedback(feedback)

                print()
                continue

            if command:
                print("Unknown command. Use /feedback or /quit.")
                continue

            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
            ) as temp_file:
                audio_path = temp_file.name

            try:
                recorder.record(audio_path)

                print("Transcribing...")

                user_text = transcriber.transcribe(audio_path)

                if not user_text:
                    print("No speech detected.")
                    continue

                print(f"{BOLD}{GREEN}You:{RESET}")
                print(f"{GREEN}{user_text}")

                logger.write_user(user_text)

                print(f"{BOLD}{LIGHT_MAGENTA}Tutor:{RESET}")
                start_time = time.time()
                response = tutor.chat(user_text)
                response_time = time.time() - start_time

                print(f"{LIGHT_MAGENTA}{response}")
                print(f"{DIM}Response time: {response_time:.2f} seconds{RESET}")
                logger.write_tutor(response)

                print()
                
#                 if args.voice:
#                     # voice = PiperVoice.load(f"{DEFAULT_PIPER_PATH}/en_GB-northern_english_male-medium.onnx")

#                     piper = PiperVoice(model_path=f"{DEFAULT_PIPER_PATH}/en_GB-northern_english_male-medium.onnx")
#                     piper.synthesize_to_file(
#                         text="Hello, I'm a synthetizer.",
#                         output_file="temp.wav"
# )

            finally:
                try:
                    os.remove(audio_path)
                except OSError:
                    pass

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

        except Exception as error:
            print(f"Error: {error}")
            print()


if __name__ == "__main__":
    main()
