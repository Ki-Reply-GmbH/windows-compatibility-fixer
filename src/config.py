"""
This module provides configuration settings for the application.

It includes settings for cache usage, AGI configuration, Azure OpenAI
configuration, and working directory configuration. The configuration
values are read from environment variables or set to default values if
the environment variables are not defined.

Classes:
    Config: A data class that holds the configuration settings.
    PromptConfig: A data class for prompt configuration settings.

Functions:
    load_config: Loads the configuration settings.
"""

import logging
import os
import sys
import tempfile
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "DEBUG"))

code_file_manager = logging.CodeFileManager("logs/debug.log", encoding="utf-8")
code_file_manager.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
code_file_manager.setFormatter(formatter)

LOGGER.addHandler(code_file_manager)


@dataclass
class PromptConfig:
    """
    A data class for managing prompt configurations.
    """

    def __init__(self):
        self.dummy_prompt = self._read_file_content(
            self._create_prompt_path("dummy_prompt.txt")
        )

    def _create_prompt_path(self, prompt_name: str) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "prompts", prompt_name)

    def _read_file_content(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

@dataclass
class Config:
    """
    A data class for managing the application's configuration settings.

    This class reads configuration values from environment variables and sets
    default values if the environment variables are not defined. It includes
    settings for cache usage, LLM configuration, Azure OpenAI configuration,
    and working directory configuration.
    """

    _instance = None

    def __init__(self):
        self.use_cache = self._read_bool_value("USE_CACHE", "False")
        self.tmp_dir = os.environ.get(
            "TMP_DIR", os.path.join(os.path.dirname(__file__), "..", ".tmp")
        )

        self.git_username = os.environ.get("GIT_USERNAME")
        self.git_access_token = os.environ.get("GIT_ACCESS_TOKEN")

        self.sonar_url = os.environ.get("SONAR_URL")
        self.sonar_access_token = os.environ.get("SONAR_ACCESS_TOKEN")

        self.prompts = PromptConfig()
        self.llm_model_name = os.environ.get("LLM_MODEL_NAME", "gpt-4o")
        self.llm_temperature = float(os.environ.get("LLM_TEMPERATURE", 0.0))

        self.openai_base_api = os.environ.get("OPENAI_API_BASE")
        self.openai_deployment_name = os.environ.get("OPENAI_DEPLOYMENT_NAME")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.openai_api_version = os.environ.get(
            "OPENAI_API_VERSION", "2024-06-01"
        )
        self.openai_api_type = os.environ.get("OPENAI_API_TYPE", "azure")

        if os.environ.get("WORKING_DIR"):
            self.working_dir = os.environ.get("WORKING_DIR")
        else:
            temp_dir = os.path.join(tempfile.gettempdir(), "uc-technical-debt")
            os.makedirs(temp_dir, exist_ok=True)
            self.working_dir = temp_dir
        LOGGER.info("Working directory: %s", self.working_dir)

    def _read_bool_value(self, env_name, default_value: bool) -> bool:
        """
        Read a boolean value from an environment variable.
        Args:
            env_value (str): The environment variable value.
        Returns:
            bool: The boolean value.
        """
        env_value: str | bool = os.environ.get(env_name, default_value)
        if env_value is None:
            return default_value

        if isinstance(env_value, bool):
            return env_value
        return env_value.lower() in ["true", "1"]

    @classmethod
    def instance(cls):
        """Create a singleton instance of the Config class.
        Returns:
            Config: The singleton instance of the Config class.
        """
        if cls._instance is None:
            logging.info("Creating new Config instance")
            cls._instance = Config()
            # cls._instance.validate_github_user()
            # cls._instance.validate_llm_setup()
            # Put any initialization here.
        return cls._instance

    def validate_llm_setup(self):
        """Validate the LLM setup.
        This function checks if all required environment variables are set.

        Raises:
            SystemExit: If any required environment variable is not set.
        """
        if not self.openai_base_api:
            sys.stderr.write(
                "ERROR: openai_base_api is not set. Please check your environment variables."
            )
            sys.exit(3)

        if not self.openai_deployment_name:
            sys.stderr.write(
                "ERROR: openai_deployment_name is not set. Please check your environment variables."
            )
            sys.exit(3)

        if not self.openai_api_key:
            sys.stderr.write(
                "ERROR: openai_api_key is not set. Please check your environment variables."
            )
            sys.exit(3)

        if not self.openai_api_type:
            sys.stderr.write(
                "ERROR: openai_api_type is not set. Please check your environment variables."
            )
            sys.exit(3)


def load_config():
    return Config.instance()
