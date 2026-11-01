"""Check NUL-separated file paths from stdin for secrets, without printing their values."""

import re
import sys
from pathlib import Path

PATTERNS = {
    "API key": r"\bsk-[A-Za-z0-9_-]{16,}",
    "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
    "GitHub token": r"\bgh[pousr]_[A-Za-z0-9]{20,}",
    "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY",
    "JWT": r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ",
    "credential assignment": (
        r"(?i)(api[_-]?key|secret|token|password|passwd)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-/+]{16,}"
    ),
    "local home path": r"/(Users|home)/[a-z][\w.-]+/",
}
SENSITIVE_NAME = re.compile(
    r"(^|/)(\.env(\.(?!example$)[^/]+)?|[^/]*\.(pem|key|p12|sqlite)|id_(rsa|ed25519)|"
    r"[^/]*credentials[^/]*|settings\.local\.json)$"
)
ENV_LINE = re.compile(r"\s*(?:export\s+)?([A-Za-z_]\w*)=(.*)")
NON_SECRET_ENV_NAME = re.compile(r"MODEL")
MIN_SECRET_LENGTH = 8


def env_values(path: Path) -> dict[str, bytes]:
    """Read values from .env as data, without executing the file."""
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ENV_LINE.fullmatch(line)
        if match and not NON_SECRET_ENV_NAME.search(match[1]):
            value = match[2].strip().strip("\"'")
            if len(value) >= MIN_SECRET_LENGTH:
                values[match[1]] = value.encode()
    return values


def scan_file(path: str, secrets: dict[str, bytes]) -> list[str]:
    findings = ["sensitive file name"] if SENSITIVE_NAME.search(path) else []
    file = Path(path)
    if not file.is_file():
        return findings

    content = file.read_bytes()
    findings += [f"value of {name} from .env" for name, value in secrets.items() if value in content]
    text = content.decode("utf-8", "ignore")
    findings += [label for label, pattern in PATTERNS.items() if re.search(pattern, text)]
    return findings


def main() -> None:
    paths = sorted({path for path in sys.stdin.buffer.read().decode().split("\0") if path})
    secrets = env_values(Path(".env"))
    results = {path: findings for path in paths if (findings := scan_file(path, secrets))}

    for path, findings in results.items():
        print(f"{path}: {', '.join(findings)}")
    print(f"Scanned {len(paths)} files against {len(secrets)} .env values: {len(results)} flagged.")
    sys.exit(1 if results else 0)


if __name__ == "__main__":
    main()
