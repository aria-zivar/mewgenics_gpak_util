#!/usr/bin/env python3
# Mewgenics GPAK Utility - Original @ https://github.com/Tiftid/mewgenics_gpak_util

import argparse
import os
import struct
import sys
from pathlib import Path
from tqdm import tqdm

HEADER = b"\\H\x00\x00"

def unpack(gpak_path, output_dir=None):
    gpak_path = Path(gpak_path)
    output_dir = Path(output_dir) if output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(gpak_path, "rb") as f:
        if f.read(4) != HEADER:
            raise ValueError("Invalid GPAK header")

        # Start picking through the various metadata
        entries = []
        while True:
            path_len = struct.unpack("<H", f.read(2))[0]

            if path_len == 0:
                f.read(4)
                break
            if path_len > 1024:
                f.seek(-2, 1)
                break

            path_bytes = f.read(path_len)

            # If we start hitting garbage, we're in the right area for data
            if sum(32 <= b <= 126 for b in path_bytes) < len(path_bytes) * 0.8:
                f.seek(-(path_len + 2), 1)
                break

            try:
                path = path_bytes.decode("utf-8")
            except UnicodeDecodeError:
                path = path_bytes.decode("latin-1")

            size = struct.unpack("<I", f.read(4))[0]
            entries.append((path, size))

        for path, size in tqdm(entries, desc="Extracting", unit="file"):
            out_path = output_dir / path
            out_path.parent.mkdir(parents=True, exist_ok=True)

            with open(out_path, "wb") as out:
                remaining = size
                while remaining:
                    chunk = f.read(min(4096, remaining))
                    if not chunk:
                        raise ValueError(f"Unexpected EOF reading {path}")
                    out.write(chunk)
                    remaining -= len(chunk)

        print(f"Extracted {len(entries)} files to {output_dir}")


def pack(input_dir, gpak_path):
    input_dir = Path(input_dir)
    gpak_path = Path(gpak_path)

    if not input_dir.is_dir():
        raise ValueError(f"Not a directory: {input_dir}")

    entries = []
    for path in tqdm(sorted(input_dir.rglob("*")), desc="Scanning", unit="file"):
        if path.is_file():
            rel = str(path.relative_to(input_dir)).replace(os.sep, "/")
            entries.append((rel, path, path.stat().st_size))

    if not entries:
        raise ValueError(f"No files in {input_dir}")

    # Write all these cats back into the bag ヽ(✿ﾟ▽ﾟ)ノ
    with open(gpak_path, "wb") as f:
        f.write(HEADER)

        for rel, _, size in tqdm(entries, desc="Writing metadata", unit="file"):
            path_bytes = rel.encode("utf-8")
            f.write(struct.pack("<H", len(path_bytes)))
            f.write(path_bytes)
            f.write(struct.pack("<I", size))

        for rel, abs_path, _ in tqdm(entries, desc="Packing", unit="file"):
            with open(abs_path, "rb") as src:
                while chunk := src.read(4096):
                    f.write(chunk)

        print(f"Packed {len(entries)} files into {gpak_path}")


def main():
    parser = argparse.ArgumentParser(description="Pack/unpack Mewgenics .gpak files")
    subs = parser.add_subparsers(dest="pack_unpack", required=True)

    p = subs.add_parser("unpack")
    p.add_argument("gpak")
    p.add_argument("-o", "--output")

    p = subs.add_parser("pack")
    p.add_argument("dir")
    p.add_argument("gpak")

    args = parser.parse_args()

    try:
        if args.unpack_pack == "pack_unpack":
            unpack(args.gpak, args.output)
        else:
            pack(args.dir, args.gpak)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    main()
