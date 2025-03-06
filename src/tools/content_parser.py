import subprocess  # nosec B404
import json
import shutil
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any
from src.config import LOGGER


class AbstractContentParser(ABC):
    def __init__(self, text: str, section_range: Tuple[int, int]):
        self._text = text
        self._section_range = section_range

    @abstractmethod
    def parse_surrounding_content(self):
        raise NotImplementedError


class LinearTextParser(AbstractContentParser):
    def __init__(
        self, text: str, section_range: Tuple[int, int], margin: int = 0
    ):
        super().__init__(text, section_range)
        self._margin = margin

    def parse_surrounding_content(self):
        start_idx, end_idx = self._section_range
        start_idx -= (
            self._margin + 1
        )  # decrement by 1 to include the line itself
        end_idx += self._margin

        start_idx, end_idx = self._normalize_limits(
            start_idx, end_idx
        )

        text_lines = self._text.splitlines()
        selected_lines = text_lines[start_idx:end_idx]

        return "\n".join(selected_lines)

    def _normalize_limits(
        self, start_idx: int, end_idx: int
    ) -> Tuple[int, int]:
        if start_idx < 0:
            start_idx = 0

        text_size = len(self._text.splitlines())
        if end_idx > text_size:
            end_idx = text_size

        return start_idx, end_idx