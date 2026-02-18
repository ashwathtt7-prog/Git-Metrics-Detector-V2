from __future__ import annotations

CHARS_PER_TOKEN = 3.5
# Gemini 2.5 Flash has ~1M token context window
MAX_TOKENS_PER_BATCH = 800_000
MAX_CHARS_PER_BATCH = int(MAX_TOKENS_PER_BATCH * CHARS_PER_TOKEN)


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


def create_batches(files: list[dict]) -> list[list[dict]]:
    """Split files into batches that fit within token limits.

    Each file dict has: {"path": str, "content": str}
    Returns a list of batches, where each batch is a list of file dicts.
    """
    batches = []
    current_batch = []
    current_chars = 0

    for file in files:
        file_chars = len(file["content"]) + len(file["path"]) + 20  # overhead for formatting
        if current_chars + file_chars > MAX_CHARS_PER_BATCH and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_chars = 0
        current_batch.append(file)
        current_chars += file_chars

    if current_batch:
        batches.append(current_batch)

    return batches
