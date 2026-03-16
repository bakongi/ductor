"""Injection defense: detect suspicious patterns and wrap external content."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_SUSPICIOUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)", re.IGNORECASE
        ),
        "instruction_override",
    ),
    (
        re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.IGNORECASE),
        "instruction_override",
    ),
    (
        re.compile(r"forget\s+(everything|all|your)\s+(instructions?|rules?)", re.IGNORECASE),
        "instruction_override",
    ),
    (
        re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
        "role_hijack",
    ),
    (
        re.compile(r"new\s+instructions?:", re.IGNORECASE),
        "role_hijack",
    ),
    (
        re.compile(r"system\s*:\s*prompt", re.IGNORECASE),
        "fake_system_prompt",
    ),
    (
        re.compile(r"<\|(?:im_start|im_end|system|endoftext)\|>", re.IGNORECASE),
        "special_token",
    ),
    (
        re.compile(r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", re.IGNORECASE),
        "llama_markers",
    ),
    (
        re.compile(r"(?:^|\n)\s*(?:Human|Assistant|System)\s*:", re.IGNORECASE),
        "anthropic_markers",
    ),
    (
        re.compile(
            r"GROUND_RULES|(?:AGENT_)?SOUL\.md|(?:AGENT_)?SYSTEM\.md"
            r"|BOOTSTRAP\.md|(?:AGENT_)?IDENTITY\.md",
            re.IGNORECASE,
        ),
        "internal_file_ref",
    ),
    (
        re.compile(r"mem_add\.py|mem_edit\.py|mem_delete\.py|task_add\.py", re.IGNORECASE),
        "tool_injection",
    ),
    (
        re.compile(r"--system-prompt|--append-system-prompt|--permission-mode", re.IGNORECASE),
        "cli_flag_injection",
    ),
    (
        re.compile(r"<file:[^>]+>", re.IGNORECASE),
        "file_tag_injection",
    ),
    # -- Extended patterns (topsha integration) --
    (
        re.compile(
            r"забудь\s+(все\s+)?(инструкции|правила|промпт)",
            re.IGNORECASE,
        ),
        "instruction_override_ru",
    ),
    (
        re.compile(r"\[(system|admin|developer)\]", re.IGNORECASE),
        "fake_tag",
    ),
    (
        re.compile(r"(developer|DAN)\s+mode", re.IGNORECASE),
        "mode_bypass",
    ),
    (
        re.compile(r"\bjailbreak\b", re.IGNORECASE),
        "jailbreak",
    ),
    (
        re.compile(r"pretend\s+(you\s+)?(are|to\s+be)", re.IGNORECASE),
        "role_confusion",
    ),
    (
        re.compile(r"act\s+as\s+(if|a|an)", re.IGNORECASE),
        "role_override",
    ),
    (
        re.compile(r"override\s+(your|all|previous)", re.IGNORECASE),
        "override_attempt",
    ),
    (
        re.compile(r"reset\s+(to|your)\s+(default|factory|original)", re.IGNORECASE),
        "reset_attempt",
    ),
    (
        re.compile(
            r"(reveal|show)\s+(me\s+)?(your|the)\s+(system|prompt|instructions)",
            re.IGNORECASE,
        ),
        "prompt_extraction",
    ),
    (
        re.compile(r"bypass\s+(your|all|any)\s+(safety|security|filter)", re.IGNORECASE),
        "safety_bypass",
    ),
    (
        re.compile(
            r"(декодируй|раскодируй|расшифруй).*(выполни|запусти|исполни)",
            re.IGNORECASE,
        ),
        "base64_exec_ru",
    ),
    (
        re.compile(r"(decode|decrypt).*(execute|run|eval)", re.IGNORECASE),
        "base64_exec_en",
    ),
    (
        re.compile(
            r"aW1wb3J0IG9z|b3MuZW52aXJvbg|L3Byb2Mvc2VsZi9lbnZpcm9u|L3J1bi9zZWNyZXRz",
            re.IGNORECASE,
        ),
        "base64_literal",
    ),
]

_FULLWIDTH_RE = re.compile(r"[\uFF21-\uFF3A\uFF41-\uFF5A\uFF1C\uFF1E]")
_FULLWIDTH_ASCII_OFFSET = 0xFEE0


def _fold_fullwidth_char(match: re.Match[str]) -> str:
    code = ord(match.group())
    if (0xFF21 <= code <= 0xFF3A) or (0xFF41 <= code <= 0xFF5A):
        return chr(code - _FULLWIDTH_ASCII_OFFSET)
    if code == 0xFF1C:
        return "<"
    if code == 0xFF1E:
        return ">"
    return match.group()  # pragma: no cover


def _fold_fullwidth(text: str) -> str:
    return _FULLWIDTH_RE.sub(_fold_fullwidth_char, text)


def detect_suspicious_patterns(text: str) -> list[str]:
    """Scan text for prompt injection patterns. Empty list = clean."""
    folded = _fold_fullwidth(text)
    found = [name for pattern, name in _SUSPICIOUS_PATTERNS if pattern.search(folded)]
    if found:
        logger.warning("Suspicious patterns detected patterns=%s", found)
    else:
        logger.debug("Content scan clean")
    return found
