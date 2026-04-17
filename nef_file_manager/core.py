import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple

RE_IMAGE_EXT: str = r".*\.(nef|jpg|hif|mov)$"

class Stats:
    def __init__(self):
        self.start_time = time.time()
        self.indexing_time = 0
        self.metadata_time = 0
        self.transfer_time = 0
        self.files_transferred = 0
        self.folders_created = 0
        self.total_groups = 0

    def print_summary(self, copy_only: bool):
        total_time = time.time() - self.start_time
        action = "Copied" if copy_only else "Moved"
        
        print("\n" + "="*40)
        print("ORGANIZATION SUMMARY")
        print("="*40)
        print(f"File groups processed: {self.total_groups}")
        print(f"Files {action.lower()}:         {self.files_transferred}")
        print(f"Folders created:      {self.folders_created}")
        print("-"*40)
        print(f"Indexing phase:       {self.indexing_time:.2f}s")
        print(f"Metadata phase:       {self.metadata_time:.2f}s")
        print(f"Transfer phase:       {self.transfer_time:.2f}s")
        print(f"Total time elapsed:   {total_time:.2f}s")
        print("="*40)


def organize_raw_files(from_folder: str, to_folder: str, copy_only: bool = False):
    stats = Stats()
    print(f"Indexing files in {from_folder} (Copy only: {copy_only})")
    
    # Step 1: Index files and group them by (directory, stem)
    t0 = time.time()
    file_groups: Dict[Tuple[Path, str], List[Path]] = {}
    
    for root, dirs, files in os.walk(from_folder):
        # Skip rejected folders
        if "_Rejected" in root.split(os.sep):
            continue
            
        root_path = Path(root)
        for file in files:
            fp = root_path / file
            # Group by stem to keep NEF, JPG, MOV together
            key = (fp.parent, fp.stem)
            if key not in file_groups:
                file_groups[key] = []
            file_groups[key].append(fp)
    
    stats.indexing_time = time.time() - t0

    if not file_groups:
        print("No files found to organize.")
        return

    # Step 2: Identify "primary" files for metadata extraction
    primary_files_map: Dict[str, Tuple[Path, str]] = {} # path_str -> (parent, stem)
    
    for (parent, stem), paths in file_groups.items():
        # Find the best candidate for metadata
        candidate = None
        for ext in ['.NEF', '.nef', '.JPG', '.jpg', '.HIF', '.hif', '.MOV', '.mov']:
            for p in paths:
                if p.suffix == ext:
                    candidate = p
                    break
            if candidate:
                break
        
        if candidate:
            primary_files_map[str(candidate)] = (parent, stem)

    if not primary_files_map:
        print("No RAW/Image files found in groups.")
        return
        
    stats.total_groups = len(primary_files_map)

    # Step 3: Batch Metadata Extraction
    print(f"Extracting metadata for {len(primary_files_map)} file groups...")
    t0 = time.time()
    metadata_lookup = get_batch_exif(list(primary_files_map.keys()))
    stats.metadata_time = time.time() - t0

    # Step 4: Transfer groups
    t0 = time.time()
    for file_path_str, (parent, stem) in primary_files_map.items():
        if file_path_str not in metadata_lookup:
            print(f"Could not get metadata for {file_path_str}")
            continue
            
        exif_data = metadata_lookup[file_path_str]
        to_image_folder, created = create_folder(exif_data, to_folder)
        
        if created:
            stats.folders_created += 1
            
        if to_image_folder:
            # Transfer ALL files in this group (NEF, JPG, MOV, etc)
            for file_to_move in file_groups[(parent, stem)]:
                if transfer_single_file(file_to_move, to_image_folder, copy_only):
                    stats.files_transferred += 1
    
    stats.transfer_time = time.time() - t0
    stats.print_summary(copy_only)


def get_batch_exif(file_paths: List[str]) -> Dict[str, dict]:
    """Calls exiftool once for a list of files and returns a mapping of path to metadata."""
    if not file_paths:
        return {}

    try:
        result = subprocess.run(
            ['exiftool', '-j', '-CreateDate', '-DateTimeOriginal', '-ModifyDate'] + file_paths,
            capture_output=True,
            text=True,
            check=True
        )
        batch_data = json.loads(result.stdout)
        return {item['SourceFile']: item for item in batch_data if 'SourceFile' in item}
    except Exception as e:
        print(f"Error during batch metadata extraction: {e}")
        return {}


def create_folder(image_exif: dict, base_folder: str) -> Tuple[Optional[str], bool]:
    image_dt: Optional[datetime] = get_image_datetime(image_exif)

    if image_dt is None:
        return None, False

    created = False
    # create year
    folder_year = Path(base_folder) / str(image_dt.year)
    if not folder_year.exists():
        folder_year.mkdir(parents=True, exist_ok=True)

    # create date
    folder_date = folder_year / image_dt.strftime('%Y-%m-%d')
    if not folder_date.exists():
        print(f"Creating new folder: {folder_date}")
        folder_date.mkdir(parents=True, exist_ok=True)
        created = True

    return str(folder_date), created


def transfer_single_file(file_path: Path, to_image_folder: str, copy_only: bool = False) -> bool:
    """Transfers a single file to the destination. Returns True if successful."""
    dest_path = Path(to_image_folder) / file_path.name
    
    try:
        if dest_path.exists():
            try:
                os.chflags(dest_path, 0)
            except AttributeError:
                pass 
            dest_path.unlink()

        if not copy_only:
            try:
                os.chflags(file_path, 0)
            except AttributeError:
                pass

        action = "Copying" if copy_only else "Moving"
        print(f"{action}: {file_path.name} -> {to_image_folder}")

        if copy_only:
            subprocess.run(['rsync', '-ah', str(file_path), str(dest_path)], check=True)
        else:
            shutil.move(file_path, dest_path)
        return True
    except Exception as e:
        print(f"Error transferring {file_path.name}: {e}")
        return False


def get_image_datetime(image_exif: dict) -> Optional[datetime]:
    for field in ['CreateDate', 'DateTimeOriginal', 'ModifyDate']:
        if field in image_exif:
            val = image_exif[field]
            date_str = val[0] if isinstance(val, list) else val
            try:
                return datetime.strptime(date_str[:19], '%Y:%m:%d %H:%M:%S')
            except (ValueError, TypeError):
                continue
    return None


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

    if not mount_point.startswith("/Volumes/"):
        print(f"Path {path} is not on an external volume (Mount point: {mount_point})")
        return

    print(f"Ejecting volume: {mount_point}")
    result = subprocess.run(['diskutil', 'eject', mount_point], capture_output=True, text=True)
    if result.returncode == 0:
        print("Volume ejected successfully.")
    else:
        print(f"Failed to eject volume: {result.stderr.strip()}")
