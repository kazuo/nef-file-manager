import glob
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

RE_JPG: str = r"(.*)\.(jpg|hif)"
RE_NEF: str = r"(.*)\.(nef|mov)"


def organize_raw_files(from_folder: str, to_folder: str, copy_only: bool = False):
    print(f"Checking RAW files in {from_folder} (Copy only: {copy_only})")
    from_folder_glob = f"{Path(from_folder)}/**"
    # move/copy NEF folders first, then orphaned jpg/hif files
    for regex in [RE_NEF, RE_JPG]:
        for file in glob.iglob(from_folder_glob, recursive=True):
            fp = Path(file)

            if "_Rejected" in fp.parts:
                continue

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
                if to_image_folder:
                    transfer_image(fp, to_image_folder, copy_only)
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


def transfer_image(image_file: Path, to_image_folder: str, copy_only: bool = False):
    re_nef = fr"({image_file.stem})\.(nef|jpg|hif|mov)"
    for nef_file in glob.iglob(f"{image_file.parent}/**", recursive=True):
        nef_fp = Path(nef_file)

        if "_Rejected" in nef_fp.parts:
            continue

        matched_file = re.match(re_nef, nef_fp.name, re.IGNORECASE)
        if matched_file is None:
            continue

        dest_path = Path(f"{to_image_folder}/{nef_fp.name}")
        if dest_path.exists():
            # Remove immutable flag if present
            os.chflags(dest_path, 0)
            dest_path.unlink()

        # If we are moving, we might need to clear flags on source
        if not copy_only:
            os.chflags(nef_fp, 0)

        action = "Copying" if copy_only else "Moving"
        print(f"{action}: {nef_fp} -> {dest_path}")

        if copy_only:
            # Use rsync for copying as it's better for large files and robust
            subprocess.run(['rsync', '-ah', str(nef_fp), str(dest_path)])
        else:
            shutil.move(nef_fp, dest_path)


def get_image_datetime(image_exif: dict) -> Optional[datetime]:
    create_date = image_exif["Create Date"][0] \
        if isinstance(image_exif["Create Date"], list) \
        else image_exif["Create Date"]
    return datetime.strptime(create_date, '%Y:%m:%d %H:%M:%S')


def get_mount_point(path: str) -> Optional[str]:
    """Find the mount point for a given path on macOS."""
    p = Path(path).resolve()
    while True:
        if os.path.ismount(str(p)):
            return str(p)
        if p == p.parent:
            break
        p = p.parent
    return None


def eject_volume(path: str):
    """Eject the volume containing the given path if it is an external volume."""
    mount_point = get_mount_point(path)
    if not mount_point:
        print(f"Could not find mount point for {path}")
        return

    # Check if it's an external volume (usually under /Volumes on macOS)
    if not mount_point.startswith("/Volumes/"):
        print(f"Path {path} is not on an external volume (Mount point: {mount_point})")
        return

    print(f"Ejecting volume: {mount_point}")
    result = subprocess.run(['diskutil', 'eject', mount_point], capture_output=True, text=True)
    if result.returncode == 0:
        print("Volume ejected successfully.")
    else:
        print(f"Failed to eject volume: {result.stderr.strip()}")
