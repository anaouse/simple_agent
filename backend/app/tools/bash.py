import subprocess
import time

BASH_PATH = r"D:\Git\Git\usr\bin\bash.exe"
ALLOWED_COMMANDS = {"find", "grep", "head", "ls", "wc", "cat", "tail", "date", "pwd", "ps", "backlog"}


def _validate_command(command: str) -> str | None:
    """Validate that the first word of the command is allowed."""
    parts = command.split(maxsplit=1)
    if not parts:
        return "Error: empty command"
    first_word = parts[0]
    if first_word not in ALLOWED_COMMANDS:
        return (
            f"Error: command '{first_word}' is not allowed. "
            f"Only {', '.join(sorted(ALLOWED_COMMANDS))} are permitted."
        )
    return None



def bash(command: str, timeout: int = 30, max_output_chars: int = 50000) -> str:
    """Execute a shell command via bash using Git Bash.

    Only checks the first word of the command against a fixed whitelist.
    Arguments and compound operators are passed through to bash as-is.

    Args:
        command: The shell command to execute, e.g., 'ls -la /some/path'
        timeout: Maximum seconds to wait for the command; defaults to 30
        max_output_chars: Maximum characters for stdout/stderr each; defaults to 50000
    """
    command_stripped = command.strip()
    if not command_stripped:
        return "Error: empty command"
    validation_error = _validate_command(command_stripped)
    if validation_error:
        return validation_error

    process = None
    try:
        process = subprocess.Popen(
            [BASH_PATH, "-c", command_stripped],
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
