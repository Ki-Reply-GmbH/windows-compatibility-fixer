import subprocess
import sys

class Builder():
  def __init__(self, project_dir):
    self._project_dir = project_dir
    self.error = None

  def build_with_dotnet(self):
    try:
      subprocess.run(
        ["dotnet", "build" ,"--configuration", "Release"],
        cwd=self._project_dir,
        check=True,
        stdout=sys.stdout,
        stderr=sys.stderr
      )
    except subprocess.CalledProcessError as e:
      self.error = e
