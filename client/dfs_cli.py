import argparse
import sys
from pathlib import Path

import requests


DEFAULT_COORDINATOR_URL = "http://localhost:8000"


def upload(args) -> None:
    coordinator = args.coordinator.rstrip("/")
    path = Path(args.path)
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    with path.open("rb") as f:
        files = {"file": (path.name, f)}
        resp = requests.post(f"{coordinator}/files", files=files)
    resp.raise_for_status()
    data = resp.json()
    print(f"Uploaded file_id={data['file_id']} original_name={data['original_name']}")


def download(args) -> None:
    coordinator = args.coordinator.rstrip("/")
    output = Path(args.output)

    resp = requests.get(f"{coordinator}/files/{args.file_id}", stream=True)
    resp.raise_for_status()

    with output.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 64):
            if chunk:
                f.write(chunk)
    print(f"Downloaded to {output}")


def info(args) -> None:
    coordinator = args.coordinator.rstrip("/")
    resp = requests.get(f"{coordinator}/files/{args.file_id}/metadata")
    resp.raise_for_status()
    print(resp.json())


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Distributed File Storage CLI")
    parser.add_argument(
        "--coordinator",
        default=DEFAULT_COORDINATOR_URL,
        help=f"Coordinator base URL (default: {DEFAULT_COORDINATOR_URL})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_upload = subparsers.add_parser("upload", help="Upload a file")
    p_upload.add_argument("path", help="Path to local file to upload")
    p_upload.set_defaults(func=upload)

    p_download = subparsers.add_parser("download", help="Download a file")
    p_download.add_argument("file_id", help="ID of file to download")
    p_download.add_argument("output", help="Output path")
    p_download.set_defaults(func=download)

    p_info = subparsers.add_parser("info", help="Show file metadata")
    p_info.add_argument("file_id", help="ID of file to inspect")
    p_info.set_defaults(func=info)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

