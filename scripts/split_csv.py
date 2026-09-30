"""Split a CSV into batches, keeping the header in every file."""

import argparse
import csv
from pathlib import Path


def split_csv(source, destination, batch_size):
    with source.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)

    destination.mkdir(parents=True)
    files = []
    for index, start in enumerate(range(0, len(rows), batch_size), 1):
        target = destination / f"batch_{index:03d}.csv"
        with target.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows[start:start + batch_size])
        files.append(target)
    return len(rows), files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--output-dir", type=Path, default=Path("input/batches"))
    args = parser.parse_args()

    count, files = split_csv(args.input_csv, args.output_dir, args.batch_size)
    print(f"Split {count} devices into {len(files)} batches.")
    print(f"Output: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
