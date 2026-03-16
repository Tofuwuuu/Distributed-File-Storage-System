import hashlib
from typing import BinaryIO, Iterator, Tuple


def iter_file_chunks(f: BinaryIO, chunk_size: int) -> Iterator[Tuple[bytes, int, str]]:
    """
    Yield (data, size, chunk_id) for each chunk in the file.
    chunk_id is the hex-encoded SHA-256 of the chunk bytes.
    """
    index = 0
    while True:
        data = f.read(chunk_size)
        if not data:
            break
        size = len(data)
        chunk_id = hashlib.sha256(data).hexdigest()
        yield data, size, chunk_id
        index += 1

