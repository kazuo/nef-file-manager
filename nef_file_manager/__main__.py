import argparse
import os
import shutil
import subprocess
from datetime import datetime
from typing import Optional

from pathlib import Path

import glob
import re

RE_JPG: str = r"(.*)\.(jpg|hif)"
RE_NEF: str = r"(.*)\.(nef|mov)"

def main(from_folder: str, to_folder: str):
    print(f"Checking RAW files in {from_folder}")
    from_folder_glob = f"{Path(from_folder)}/**"
    # move NEF folders first, then orphaned jpg/hif files
    for regex in [RE_NEF, RE_JPG]:
        for file in glob.iglob(from_folder_glob, recursive=True):
            fp = Path(file)
            matched_file = re.match(regex, fp.name, re.IGNORECASE)
            if matched_file is None:
                continue

            result = subprocess.run(['exiftool', file], capture_output=True, text=True)
            if result.returncode != 0:
                print(f'Could not open {file}')
                continue

            try:
                exif_data = parse_exif(result.stdout)
                to_image_folder = create_folder(exif_data, to_folder)
                move_image(fp, to_image_folder)
            except Exception as e:
                print('Caught an error', e)

def parse_exif(raw_stdout: str) -> dict:
    rows: list = raw_stdout.splitlines()
    data = {}
    for row in rows:
        row = row.split(':', 1)
        # no idea if labels are unique, but let's handle cases when it's not
        label = row[0].strip()
        value = row[1].strip()
        if label in data:
            if isinstance(data[label], list):
                data[label].append(value)
            else:
                data[label] = [data[label], value]
        else:
            data[label] = value

    return data

def create_folder(image_exif: dict, base_folder: str) -> Optional[str]:
    image_dt: Optional[datetime] = get_image_datetime(image_exif)

    if image_dt is None:
        return None

    # create year
    folder_year = f"{base_folder}/{image_dt.year}"
    if not Path(folder_year).exists() or not Path(folder_year).is_dir():
        os.mkdir(folder_year)

    # create date
    folder_date = f"{folder_year}/{image_dt.strftime('%Y-%m-%d')}"
    if not Path(folder_date).exists() or not Path(folder_date).is_dir():
        print(f"Creating new folder: {folder_date}")
        os.mkdir(folder_date)

    return folder_date


def move_image(image_file: Path, to_image_folder: str):
    re_nef = fr"({image_file.stem})\.(nef|jpg|hif|mov)"
    for nef_file in glob.iglob(f"{image_file.parent}/**", recursive=True):
        nef_fp = Path(nef_file)
        matched_file = re.match(re_nef, nef_fp.name, re.IGNORECASE)
        if matched_file is None:
            continue

        print(f"{nef_fp} -> {to_image_folder}/{nef_fp.name}")
        shutil.move(nef_fp, f"{to_image_folder}/{nef_fp.name}", shutil.copy2)


def get_image_datetime(image_exif: dict) -> Optional[datetime]:
    create_date = image_exif["Create Date"][0] \
        if isinstance(image_exif["Create Date"], list) \
        else image_exif["Create Date"]
    return datetime.strptime(create_date, '%Y:%m:%d %H:%M:%S')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Organize RAW files by date based on EXIF data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m nef_file_manager "/path/to/source" "/path/to/target"
  python -m nef_file_manager --source "/Users/user/Pictures/Nikon Transfer 2" --target "/Users/user/Pictures/RAW"
        """
    )

    parser.add_argument(
        "source",
        nargs="?",
        help="Source folder containing RAW files to organize"
    )

    parser.add_argument(
        "target",
        nargs="?",
        help="Target folder where organized files will be moved"
    )

    parser.add_argument(
        "-s", "--source",
        dest="source_flag",
        help="Source folder (alternative to positional argument)"
    )

    parser.add_argument(
        "-t", "--target",
        dest="target_flag",
        help="Target folder (alternative to positional argument)"
    )

    args = parser.parse_args()

    # Use flag values if provided, otherwise use positional arguments
    source_folder = args.source_flag or args.source
    target_folder = args.target_flag or args.target

    # Set defaults if no arguments provided
    if not source_folder:
        home_dir = Path.home()
        source_folder = str(home_dir / "Pictures" / "Nikon Transfer 2")
        print(f"Using default source folder: {source_folder}")

    if not target_folder:
        home_dir = Path.home()
        target_folder = str(home_dir / "Pictures" / "RAW")
        print(f"Using default target folder: {target_folder}")

    # Validate that folders exist
    if not Path(source_folder).exists():
        print(f"Error: Source folder '{source_folder}' does not exist")
        exit(1)

    if not Path(target_folder).exists():
        print(f"Target folder '{target_folder}' does not exist. Creating it...")
        Path(target_folder).mkdir(parents=True, exist_ok=True)

    main(source_folder, target_folder)
