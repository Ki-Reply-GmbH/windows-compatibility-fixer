import re
import os
from typing import Optional
import requests
from git import Repo
from src.config import LOGGER


class GitManager:
    def __init__(
        self,
        local_workspace: str,
        repository_url: str,
        account_name: str,
        security_token: str,
    ):
        self._local_workspace = local_workspace
        self._repo_details = {
            "repository_url": repository_url,
            "account_name": account_name,
            "security_token": security_token,
            "project_name": None,
            "account_owner": None,
            "domain_url": None,
            "clone_url": None,
        }

        self._source_tree: Optional[Repo] = None
        self._feature_branch_name = ""

    @property
    def project_name(self):
        return self._repo_details["project_name"]

    def initialize(self):
        """
        Clones the repository and checks if there are new commits at the head
        branch.

        :return: True if a fix branch with the most recent commit already
                 exists, False otherwise.
        """
        self._extract_repository_info()
        self._source_tree = Repo.clone_from(
            self._repo_details["clone_url"],
            os.path.join(
                self._local_workspace, self._repo_details["project_name"]
            ),
        )
        bot_name = "TechDebotBot"
        bot_email = "tech-debt-bot@reply.de"
        self._configure_author_info(name=bot_name, email=bot_email)

        latest_commit = self._current_revision_id()
        self._cleanup_obsolete_branches(
            author_name="Timo",
            current_branch_id=latest_commit,
        )

        return self._check_branch_presence(latest_commit)

    def create_feature_branch(self, identifier: str):
        if self._source_tree is None:
            raise ValueError(
                "Repository is not initialized. Call initialize() first."
            )
        latest_commit = self._current_revision_id()
        self._feature_branch_name = (
            f"tech-debt-bot-{identifier}-{latest_commit}"
        )

        # Create new fix branch from default branch
        main_branch = self._determine_main_branch()
        self._source_tree.git.checkout(main_branch)
        self._source_tree.git.checkout("-b", self._feature_branch_name)
        LOGGER.debug(f"Checked out to fix branch: {self._feature_branch_name}")

    def stage_and_record(self, message: str):
        """
        Commits and pushes changes to the repository.
        """
        if self._source_tree is None:
            raise ValueError(
                "Repository is not initialized. Call initialize() first."
            )

        self._source_tree.git.add(".")
        self._source_tree.git.commit("-m", message)

    def create_merge_request(self, title: str, body: str, base: str):
        """
        Open a pull request on the repository.

        Parameters:
        title (str): The title of the pull request.
        body (str): The body description of the pull request.
        base (str): The name of the target branch (base).
        """
        if self._source_tree is None:
            raise ValueError(
                "Repository is not initialized. Call initialize() first."
            )

        url = f"https://api.{self._repo_details["domain_url"]}/repos/{self._repo_details["account_owner"]}/{self._repo_details["project_name"]}/pulls"

        headers = {
            "Content-type": "application/json",
            "Accept": "application/json",
            "Authorization": f"token {self._repo_details["security_token"]}",
        }
        data = {
            "title": title,
            "body": body,
            "head": self._feature_branch_name,
            "base": base,
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 201:
            LOGGER.info("Pull request created successfully.")
        else:
            LOGGER.error(
                "Failed to create pull request: %d", response.status_code
            )
            LOGGER.error(response.text)
            LOGGER.error("URL:\n" + str(url))
            LOGGER.error("HEADERS:\n" + str(headers))
            LOGGER.error("DATA:\n" + str(data))

    def publish_and_verify_remote(self):
        current_branch = self._source_tree.active_branch.name
        tracking_branch = self._source_tree.git.rev_parse(
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{u}",
            with_exceptions=False,
        )

        if not tracking_branch:
            self._source_tree.git.push("--set-upstream", "origin", current_branch)
        else:
            self._source_tree.git.push()

    def _extract_repository_info(self):
        pattern = r"https://([^/]+)/([^/]+)/([^/]+)"
        match = re.match(pattern, self._repo_details["repository_url"])
        if not match:
            LOGGER.error("Invalid repository URL.")
            raise ValueError("Invalid repository URL.")

        domain, owner, repo = match.groups()
        self._repo_details["account_owner"] = owner
        self._repo_details["project_name"] = repo
        self._repo_details["account_owner"] = owner
        self._repo_details["domain_url"] = domain
        self._repo_details["clone_url"] = (
            f"https://{self._repo_details["account_name"]}:{self._repo_details["security_token"]}@{domain}/{owner}/{repo}.git"
        )

    def _current_revision_id(self) -> str:
        if self._source_tree is None:
            raise ValueError(
                "Repository is not initialized. Call initialize() first."
            )

        return self._source_tree.head.commit.hexsha[:7]

    def _configure_author_info(self, name: str, email: str):
        if self._source_tree is None:
            raise ValueError(
                "Repository is not initialized. Call initialize() first."
            )
        config = self._source_tree.config_writer()
        config.set_value("user", "name", name)
        config.set_value("user", "email", email)
        config.release()

    def _check_branch_presence(self, branch_id: str) -> bool:
        if self._source_tree is None:
            raise ValueError(
                "Repository is not initialized. Call initialize() first."
            )

        branches = self._source_tree.git.branch("-a").split("\n")
        for branch in branches:
            LOGGER.debug(f"Branch: {branch}")
            if branch_id in branch:
                return True
        return False

    def _cleanup_obsolete_branches(
        self, author_name: str, current_branch_id: str
    ):
        """
        Deletes all branches that start with 'tech-debt-bot-' and have the last
        commit from author_name, except for the branch specified by
        current_branch_id.
        """
        branches = self._find_automation_branches()
        for branch in branches:
            LOGGER.debug(f"Checking branch: {branch}")
            if self._should_remove_branch(
                branch, author_name, current_branch_id
            ):
                LOGGER.debug(f"Trying to delete branch: {branch}")
                self._remove_branch(branch)

    def _find_automation_branches(self) -> list:
        """
        Retrieves all branches that start with 'tech-debt-bot-'.

        :return: A list of branch names.
        """
        if self._source_tree is None:
            raise ValueError(
                "Repository is not initialized. Call initialize() first."
            )

        branches = self._source_tree.git.branch(
            "-a", "--list", "*tech-debt-bot-*"
        ).split("\n")
        return [branch.strip() for branch in branches if branch.strip()]

    def _retrieve_changesets(self, branch: str) -> list:
        """
        Retrieves all commits for a given branch.
        """
        if self._source_tree is None:
            raise ValueError(
                "Repository is not initialized. Call initialize() first."
            )

        return list(self._source_tree.iter_commits(branch))

    def _remove_branch(self, branch: str):
        if self._source_tree is None:
            raise ValueError(
                "Repository is not initialized. Call initialize() first."
            )
        if branch.startswith("remotes/origin/"):
            branch = branch.replace("remotes/origin/", "")
        self._source_tree.git.push("origin", "--delete", branch)
        LOGGER.info(f"Deleted branch: {branch}")

    def _should_remove_branch(
        self, branch: str, author_name: str, current_branch_id: str
    ) -> bool:
        """
        Checks if a branch should be considered an old fix branch and be deleted.

        :param branch: The branch name.
        :param author_name: The username to check for the last commit.
        :param current_branch_id: The branch name to exclude from deletion.
        :return: True if the branch should be deleted, False otherwise.
        """
        if current_branch_id in branch:
            return False

        commits = self._retrieve_changesets(branch)
        if not commits:
            return False

        last_commit = commits[0]
        if last_commit.author.name == author_name:
            return True

        return False

    def _determine_main_branch(self):
        """
        Returns the name of the default branch in the repository.
        """
        try:
            # Get the symbolic reference for the default branch
            default_ref = self._source_tree.git.symbolic_ref(
                "refs/remotes/origin/HEAD"
            )
            # Extract the branch name from the reference
            main_branch = default_ref.split("/")[-1]
            return main_branch
        except Exception as e:
            LOGGER.error(f"Failed to determine the default branch: {e}")
            raise