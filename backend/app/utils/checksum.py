from hashlib import sha256
from pathlib import Path


def calculate_sha256(
    file_path: Path,
    chunk_size: int = 65_536,
) -> str:
    """Calculate the SHA-256 checksum of a file."""

    digest = sha256()

    with file_path.open("rb") as source_file:
        while chunk := source_file.read(chunk_size):
            digest.update(chunk)

    return digest.hexdigest()
