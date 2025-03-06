from typing import Dict
from src.config import PromptConfig
from tools.code_file_manager import CodeFileManager


class PromptBuilder:
    def __init__(self, prompt_config: PromptConfig, code_file_manager: CodeFileManager):
        self._prompt_config = prompt_config
        self._code_file_manager = code_file_manager
