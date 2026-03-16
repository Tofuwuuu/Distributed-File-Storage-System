# Distributed File Storage System

A simplified distributed file system (like a mini Dropbox) that demonstrates **data replication**, **chunking/partitioning**, and **high availability** across multiple storage nodes.

## Overview

- **Coordinator service**: FastAPI application that exposes upload/download APIs, splits files into fixed-size chunks, and coordinates where chunks are stored.
- **Storage nodes**: Two FastAPI services that store chunks on their local filesystem.
- **Metadata DB**: PostgreSQL database that tracks which chunks belong to which files and which nodes store each chunk.
- **Client CLI**: Python script that calls the coordinator API to upload and download files.

Each file is split into chunks (e.g., 1MB), every chunk is **hashed with SHA-256** to get a content ID, and the system writes each chunk to **two different storage nodes** for replication. The coordinator records chunk locations in the metadata DB and uses them later to reassemble the file for downloads.

## Running the system

Prerequisites:

- Docker and Docker Compose installed.
- Python 3.11 (for running the CLI locally).

Steps:

1. Build and start the stack:
   - `docker compose up --build`
2. Once all services are healthy, you can interact with the coordinator API on `http://localhost:8000`.
3. Use the `client/dfs_cli.py` script to upload and download files via the coordinator.

### Demo: upload, node failure, and download

In a separate terminal (from the project root):

- Upload a file:
  - `python client/dfs_cli.py upload path/to/local-file.txt`
  - Note the printed `file_id`.
- Stop one storage node (e.g., `storage1`):
  - `docker compose stop storage1`
- Download the file again using only the remaining replicas:
  - `python client/dfs_cli.py download <file_id> downloaded.txt`
  - Verify that `downloaded.txt` matches the original file.

### CLI commands

- **Upload**:
  - `python client/dfs_cli.py upload path/to/file.ext`
- **Download**:
  - `python client/dfs_cli.py download <file_id> output.ext`
- **Inspect metadata**:
  - `python client/dfs_cli.py info <file_id>`

## Architecture

- Client CLI → Coordinator (FastAPI)
- Coordinator → PostgreSQL for metadata
- Coordinator → Storage nodes (FastAPI) for chunk store/get

This project is designed as a learning-oriented prototype to showcase **content-addressable storage**, **replication**, and **basic fault tolerance**: even if one storage node container is stopped, files remain retrievable from the remaining replicas.
