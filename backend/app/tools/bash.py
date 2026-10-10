import os
import shlex
import subprocess
import time

from app.tools.security import get_project_root

BASH_PATH = r"D:\Git\Git\usr\bin\bash.exe"


def _validate_command(command: str) -> str | None:
    """Reject commands that use rm."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    if any(token == "rm" for token in tokens):
        return "Error: 不要使用 rm 命令，即使看起来没用的文件也保留着"
    return None



def bash(command: str, timeout: int = 30, max_output_chars: int = 50000) -> str:
    """Execute a shell command via bash using Git Bash.

    Commands are executed as-is without a whitelist; only commands that
    use rm are rejected.

    Args:
        command: The shell command to execute.
        timeout: Maximum seconds to wait for the command; defaults to 30
        max_output_chars: Maximum characters for stdout/stderr each; defaults to 50000
    """
    command_stripped = command.strip()
    if not command_stripped:
        return "Error: empty command"
    validation_error = _validate_command(command_stripped)
    if validation_error:
        return validation_error

    project_root = get_project_root()
    command_to_run = command_stripped
    if project_root is not None:
        command_to_run = f"cd -- {shlex.quote(project_root.as_posix())} && {command_stripped}"

    # 清理后端 uv 环境相关的环境变量，避免子进程 bash 继承 backend/.venv
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    paths = [p for p in env["PATH"].split(os.pathsep) if "backend/.venv" not in p]
    env["PATH"] = os.pathsep.join(paths)

    process = None
    try:
        process = subprocess.Popen(
            [BASH_PATH, "-c", command_to_run],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        
        # Poll with short communicate() timeouts: this drains the pipes on
        # every iteration (avoiding the deadlock from the old poll()-only
        # loop) while still letting us react promptly to timeout.
        started_at = time.monotonic()
        poll_interval = 0.1
        stdout_raw = stderr_raw = None
        while True:
            # Check timeout before each poll
            if time.monotonic() - started_at >= timeout:
                process.kill()
                process.communicate()
                return f"Command timed out after {timeout}s: {command}"
            
            try:
                stdout_raw, stderr_raw = process.communicate(timeout=poll_interval)
                break
            except subprocess.TimeoutExpired:
                pass
            
    except Exception as e:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate()
        return f"Command failed: {e}"

    stdout = stdout_raw.strip() if stdout_raw else ""
    stderr = stderr_raw.strip() if stderr_raw else ""
    
    # Truncate output if too long
    stdout_truncated = False
    stderr_truncated = False
    if len(stdout) > max_output_chars:
        stdout = stdout[:max_output_chars]
        stdout_truncated = True
    if len(stderr) > max_output_chars:
        stderr = stderr[:max_output_chars]
        stderr_truncated = True

    lines = [
        f"exit code: {process.returncode}",
        f"stdout:\n{stdout or '(no stdout)'}",
    ]
    if stdout_truncated:
        lines.append(f"(stdout truncated at {max_output_chars} chars)")
    lines.append(f"stderr:\n{stderr or '(no stderr)'}")
    if stderr_truncated:
        lines.append(f"(stderr truncated at {max_output_chars} chars)")

    output = "\n".join(lines)

    return output
