import shlex
import subprocess
import time

BASH_PATH = r"D:\Git\Git\usr\bin\bash.exe"
ALLOWED_COMMANDS = {"find", "grep", "head", "ls", "wc", "cat", "tail", "date", "pwd", "ps",}
FORBIDDEN_SHELL_CHARS = set("><`\n\r$")
COMPOUND_OPERATORS = {"|", "&&", "||", ";"}


def _validate_command(command: str) -> str | None:
    """Validate a sequence of allowed commands joined by shell operators."""
    if any(character in FORBIDDEN_SHELL_CHARS for character in command):
        return "Error: redirection, command substitution, and multi-line commands are not allowed"

    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="|&;()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError as exception:
        return f"Error: invalid command syntax: {exception}"

    if not tokens:
        return "Error: empty command"

    expecting_command = True
    for token in tokens:
        if token in COMPOUND_OPERATORS:
            if expecting_command:
                return f"Error: unexpected operator '{token}'"
            expecting_command = True
            continue
        if expecting_command:
            # 只检查子命令的第一个词是否在白名单里
            if token not in ALLOWED_COMMANDS:
                return (
                    f"Error: command '{token}' is not allowed. "
                    f"Only {', '.join(sorted(ALLOWED_COMMANDS))} are permitted."
                )
            expecting_command = False
        # 非首词（参数）不再逐个校验

    if expecting_command:
        return "Error: command cannot end with an operator"
    return None



def bash(command: str, timeout: int = 30, max_output_chars: int = 50000) -> str:
    """Execute a shell command via bash using Git Bash.

    Only allows find, grep, head, ls, and wc. Commands may be combined with
    pipes, &&, ||, or ;. Redirection, command substitution, and subshells
    remain disallowed.

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

    # Exit code 0 means success; 1 is kept for grep-style "no match" results.
    # Anything else (negative or >= 2) is reported as a failure while preserving
    # the exit code, stdout, and stderr for diagnostics.
    output = "\n".join(lines)
    if process.returncode not in (0, 1):
        return f"Command failed:\n{output}"

    return output
