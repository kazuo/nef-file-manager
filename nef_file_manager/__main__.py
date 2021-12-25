import os
import shutil
from datetime import datetime
from typing import Optional

from exif import Image
from pathlib import Path

import glob
import re

RE_JPG: str = r"(.*)\.(jpg)"


def main(from_folder: str, to_folder: str):
    print(f"Checking RAW files in {from_folder}")
    from_folder_glob = f"{Path(from_folder)}/**"
    for file in glob.iglob(from_folder_glob, recursive=True):
        fp = Path(file)
        matched_file = re.match(RE_JPG, fp.name, re.IGNORECASE)
        if matched_file is None:
            continue

        try:
            with open(file, 'rb') as opened_file:
                image = Image(opened_file)
            to_image_folder = create_folder(image, to_folder)
            move_image(fp, to_image_folder)
        except ValueError as e:
            print('Caught an error', e)


def create_folder(image: Image, base_folder: str) -> Optional[str]:
    image_dt: Optional[datetime] = get_image_datetime(image)

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
    re_nef = fr"({image_file.stem})\.(nef)"
    for nef_file in glob.iglob(f"{image_file.parent}/**", recursive=True):
        nef_fp = Path(nef_file)
        matched_file = re.match(re_nef, nef_fp.name, re.IGNORECASE)
        if matched_file is None:
            continue

        print(f"{image_file} -> {to_image_folder}/{image_file.name}")
        shutil.move(image_file, f"{to_image_folder}/{image_file.name}", shutil.copy2)
        print(f"{nef_fp} -> {to_image_folder}/{nef_fp.name}")
        shutil.move(nef_fp, f"{to_image_folder}/{nef_fp.name}", shutil.copy2)


def get_image_datetime(image_file: Image) -> Optional[datetime]:
    return datetime.strptime(image_file['datetime'], '%Y:%m:%d %H:%M:%S') if image_file.has_exif else None


if __name__ == "__main__":
    nikon_transfer_folder = "/Users/rmarin/Pictures/Nikon Transfer 2"
    target_folder = "/Users/rmarin/Pictures/RAW"
    main(nikon_transfer_folder, target_folder)
