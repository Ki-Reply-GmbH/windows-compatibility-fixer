from typing import Dict, Tuple
from src.models import LLModel
from src.tools.prompt_builder import PromptBuilder
from src.tools.observer import Observable
from src.config import LOGGER


class SonarAgent(Observable):

    def __init__(self, prompt_builder: PromptBuilder, model: LLModel):
        super().__init__()
        self._model = model
        self._prompt_builder = prompt_builder
        self.result: Dict = {}

    def complete_task(self, task: Dict) -> Tuple[str, Tuple[int, int], int]:
        response = self._process_task(task)

        file_path = task["file_path"]
        code_range = task["code_range"]
        inserted_lines = len(response["payload"].split("\n"))

        LOGGER.debug("Completed task: " + str(task))
        LOGGER.debug("Response: " + str(response))
        LOGGER.debug("Inserted lines: " + str(inserted_lines))

        return file_path, code_range, inserted_lines

    def _process_task(self, task: Dict) -> Dict:
        task_prompt = self._prompt_builder.build_task_prompt(task)
        response = self._model.get_completion(task_prompt)

        # Notify observer
        event_type, data = self._format_data(
            class_name="SonarAgent",
            method_name="_process_task",
            response=response,
            prompt=task_prompt,
            model_name=self._model._model_name,
        )
        self.notify(event_type, data)

        commit_msg = self._create_commit_message(task, response)
        self.result = {
            "file_path": task["file_path"],
            "improved_code_range": task["code_range"],
            "commit_message": commit_msg,
            "response": response,
        }
        return response

    def _create_commit_message(self, task: Dict, response: Dict) -> str:
        commit_prompt = self._prompt_builder.build_commit_prompt(
            task=task, response=response
        )
        response = self._model.get_completion(commit_prompt)

        # Notify observer
        event_type, data = self._format_data(
            class_name="SonarAgent",
            method_name="_create_commit_message",
            response=response,
            prompt=commit_prompt,
            model_name=self._model._model_name,
        )
        self.notify(event_type, data)

        return response["payload"]

    """
    def _find_rule_for(self, index: int, file_path: str) -> str:
        if self.result[index]["file_path"] == file_path:
            return self.result[index]["rule"]

        return "Rule not found"

    def _create_html_link(self, rule: str) -> str:
        return f'<a href="{os.getenv("SONAR_URL")}/coding_rules?q={rule}&open={rule}">{rule}</a>'
    """
