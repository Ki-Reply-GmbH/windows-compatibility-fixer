import ast
import json
import openai
from src.config import Config, LOGGER
from src.tools.data_store import DataStore, NullDataStore


class LLModel:
    def __init__(self, config: Config, cache: DataStore = NullDataStore(path="")):
        openai.api_key = config.openai_api_key
        self._cache = cache
        self._model_name = config.llm_model_name
        self._temperature = config.llm_temperature

    def _get_llm_completion(
        self, prompt="", resp_fmt_type="text", messages=None
    ):
        """
        Sends a prompt to the OpenAI API and returns the AI's response.
        """
        if messages is None and prompt == "":
            raise ValueError("Prompt cannot be empty if messages is None.")

        if messages is None:
            messages = [
                {
                    "role": "system",
                    "content": "You are a system designed to reduce technical debts in software projects.",
                },
                {"role": "user", "content": prompt},
            ]
        response = openai.OpenAI().chat.completions.create(
            model=self._model_name,
            messages=messages,
            temperature=self._temperature,
            response_format={"type": resp_fmt_type},
        )
        return response.choices[0].message.content

    def get_completion(self, prompt, resp_fmt_type: str = "json_object"):
        LOGGER.debug("Getting completion for prompt: %s", prompt)

        if resp_fmt_type == "json_object":
            return self._get_completion_json(prompt)

        return self._get_completion_text(prompt)

    def _get_completion_json(self, prompt: str):
        if self._cache.lookup(prompt):
            response = self._cache.get_answer(prompt)
            # Prevent json.loads from throwing an error
            response = ast.literal_eval(response)
        else:
            response = json.loads(
                self._get_llm_completion(prompt, "json_object")
            )
            self._cache.update(prompt, response)

        return response

    def _get_completion_text(self, prompt: str):
        if self._cache.lookup(prompt):
            response = self._cache.get_answer(prompt)
        else:
            response = self._get_llm_completion(prompt, "text")
            self._cache.update(prompt, response)

        return response

    def get_completion_with_length_check(
        self, prompt: str, max_length: int, max_retries: int = 10
    ):
        def is_valid_length(message):
            return len(message) <= max_length

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        for _ in range(max_retries):
            response = self._get_llm_completion(messages=messages)

            LOGGER.debug("Messages: %s", messages)
            LOGGER.debug("Response: %s", response)

            if is_valid_length(response):
                return prompt, response
            else:
                messages.append(
                    {
                        "role": "assistant",
                        "content": response,
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": f"The previous message was too long ({len(response)} characters). Please generate a message with less than {max_length} characters.",
                    }
                )

        return prompt, response
