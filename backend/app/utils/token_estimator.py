from __future__ import annotations

CHARS_PER_TOKEN = 3.0
DEFAULT_MAX_TOKENS_PER_BATCH = 10_000


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


def create_batches(
    files: list[dict],
    max_tokens: int = DEFAULT_MAX_TOKENS_PER_BATCH,
) -> list[list[dict]]:
    """Split files into batches that fit within token limits.

    Each file dict has: {"path": str, "content": str}
    Returns a list of batches, where each batch is a list of file dicts.
    """
    max_chars = int(max_tokens * CHARS_PER_TOKEN)
    batches = []
    current_batch = []
    current_chars = 0

    for file in files:
        file_chars = len(file["content"]) + len(file["path"]) + 20
        if current_chars + file_chars > max_chars and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_chars = 0
        current_batch.append(file)
        current_chars += file_chars

    if current_batch:
        batches.append(current_batch)

    return batches
