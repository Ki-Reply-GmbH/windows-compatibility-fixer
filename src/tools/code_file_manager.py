import os
import stat
import shutil
from typing import Union, Tuple, List
from src.config import LOGGER


class CodeFileManager:

    def __init__(self, repository_location: str = ""):
        self.repository_location = repository_location

    def remove_directory(self, target_dir: str):
        """
        Cleans up the directory.
        """
        LOGGER.debug(f"Clearing directory: {target_dir}")
        for folder_root, directory_list, file_list in os.walk(target_dir):
            for folder in directory_list:
                os.chmod(os.path.join(folder_root, folder), stat.S_IRWXU)
            for filename in file_list:
                os.chmod(os.path.join(folder_root, filename), stat.S_IRWXU)
        try:
            shutil.rmtree(target_dir)
        except FileNotFoundError:
            LOGGER.exception("FileNotFoundError: clearing directory")
        except PermissionError:
            LOGGER.exception(
                "PermissionError: [WinError 32] clearing directory"
            )

    def locate_sonar_key(self, target_dir: str) -> str:
        """
        Finds the sonar project key in the repository.
        """
        sonar_properties_file = os.path.join(
            target_dir,
            "sonar-project.properties",
        )
        try:
            with open(sonar_properties_file, "r") as file:
                for line in file:
                    if "sonar.projectKey" in line:
                        return line.split("=")[1].strip()
        except FileNotFoundError:
            LOGGER.exception("finding sonar project key")
        return ""

    def get_code_segment(
        self,
        path_to_file: str,
        line_range: Union[int, Tuple[int, int]],
        relative_path=True,
    ) -> str:
        """
        Extracts relevant lines of code from a source code file.

        Args:
            path_to_file (str): Path to the source code file.
            line_range (int or tuple): An integer or a tuple of integers representing the lines to extract.
            relative_path (bool): Whether the file path is relative to the local repository path.

        Returns:
            str: A string containing the relevant line(s) of code.
        """
        if relative_path:
            path_to_file = os.path.join(self.repository_location, path_to_file)

        extracted_content = ""

        try:
            with open(path_to_file, "r", encoding="utf-8") as file:
                file_lines = file.readlines()
                line_count = len(file_lines)

                start_line, end_line = self._normalize_line_range(
                    line_range, line_count
                )
                extracted_content = "".join(file_lines[start_line - 1 : end_line])

        except FileNotFoundError:
            LOGGER.exception("extracting lines of code")

        return extracted_content

    def get_file_text(self, path_to_file: str, relative_path=True) -> str:
        if relative_path:
            path_to_file = os.path.join(self.repository_location, path_to_file)

        try:
            with open(path_to_file, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            LOGGER.exception("reading file content")
        return ""

    def update_code_segment(
        self,
        path_to_file: str,
        line_range: Union[int, Tuple[int, int]],
        updated_code: str,
        relative_path=True,
    ):
        """
        Replaces the specified code range in the file with the improved code.

        Args:
            path_to_file (str): Path to the source code file.
            line_range (Union[int, Tuple[int, int]]): An integer or a tuple of integers representing the lines to replace.
            updated_code (str): The new code to replace the specified range with.
        """
        if relative_path:
            path_to_file = os.path.join(self.repository_location, path_to_file)

        try:
            with open(path_to_file, "r", encoding="utf-8") as file:
                file_lines = file.readlines()
                line_count = len(file_lines)

            start_line, end_line = self._normalize_line_range(
                line_range, line_count
            )

            # Find the indentation of the code range in the file
            current_indent = self._calculate_indent_level(
                file_lines, (start_line, end_line)
            )

            # Find the indentation of the improved code
            updated_code_lines = updated_code.split("\n")
            updated_code_indent = self._calculate_indent_level(
                updated_code_lines, (1, len(updated_code_lines))
            )

            # Add indentation to the improved code if its indentation is less than the file's indentation
            if updated_code_indent < current_indent:
                updated_code = self._apply_indent(
                    updated_code, current_indent
                )
                LOGGER.debug("Indentation added.")
                LOGGER.debug("Imprvoed code:")
                LOGGER.debug(updated_code)

            if isinstance(line_range, int):
                if 1 <= start_line <= end_line <= len(file_lines):
                    file_lines[start_line - 1] = updated_code + "\n"
                else:
                    LOGGER.debug("Invalid line_range. Invalid boundaries.")
                    LOGGER.debug(f"Code range: {line_range}")
                    LOGGER.debug(f"Total lines: {len(file_lines)}")
                    raise ValueError("Invalid line_range. Invalid boundaries.")
            elif isinstance(line_range, tuple) and len(line_range) == 2:
                if 1 <= start_line <= end_line <= len(file_lines):
                    file_lines[start_line - 1 : end_line] = [
                        updated_code + "\n"
                    ]
                else:
                    LOGGER.debug("Invalid line_range. Invalid boundaries.")
                    LOGGER.debug(f"Code range: {line_range}")
                    LOGGER.debug(f"Total lines: {len(file_lines)}")
                    raise ValueError("Invalid line_range. Invalid boundaries.")
            else:
                raise ValueError(
                    "Invalid line_range. Must be an int or a tuple of two ints."
                )

            with open(path_to_file, "w", encoding="utf-8") as file:
                file.writelines(file_lines)

        except FileNotFoundError:
            LOGGER.exception("improving code range")

    def _calculate_indent_level(
        self, file_lines: List[str], line_range: Union[int, Tuple[int, int]]
    ) -> int:
        if isinstance(line_range, int):
            line_range = (line_range, line_range)
        start_line, end_line = line_range
        indentations = [
            len(line) - len(line.lstrip(" "))
            for line in file_lines[start_line - 1 : end_line]
            if line.strip()  # Ignore empty lines
        ]
        return min(indentations) if indentations else 0

    def _apply_indent(self, code: str, spaces: int) -> str:
        indent_spaces = " " * spaces
        return "\n".join(indent_spaces + line for line in code.split("\n"))

    def _normalize_line_range(
        self,
        line_range: Union[int, Tuple[int, int]],
        line_count: int,
        padding: int = 0,
    ) -> Tuple[int, int]:
        """
        Adjusts the code range to ensure it is within valid boundaries.

        Args:
            line_range (int or tuple): An integer or a tuple of integers representing the lines to extract.
                                    Tuples consist of a lower and an upper bound.
            line_count (int): The total number of lines in the file.
            padding (int): The value to adjust the code range by.

        Returns:
            tuple: A tuple containing the adjusted lower and upper bounds.
        """
        if isinstance(line_range, int):
            start_line = max(1, line_range - padding)
            end_line = min(line_count, line_range + padding)
        elif isinstance(line_range, tuple) and len(line_range) == 2:
            start_line, end_line = line_range
            start_line = max(1, start_line - padding)
            end_line = min(line_count, end_line + padding)
        else:
            raise ValueError(
                "Invalid line_range. Must be an int or a tuple of two ints."
            )

        return start_line, end_line