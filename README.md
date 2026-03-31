# NEF File Manager

Organize RAW files (NEF, JPG, HIF, MOV) into a structured folder hierarchy (Year/Date) based on their EXIF data.

## Requirements

Requires `exiftool`: [https://exiftool.org](https://exiftool.org).

### Install (macOS)
```bash
brew install exiftool
```

## Usage

You can run the script using `python -m nef_file_manager`.

### Basic Usage (Move files)
By default, files are **moved** from the source to the target folder.
```bash
python -m nef_file_manager "/path/to/source" "/path/to/target"
```

### Copy files (Instead of moving)
Use the `-c` or `--copy` flag to **copy** files using `rsync` instead of moving them. This is recommended when transferring from external volumes like CFe cards.
```bash
python -m nef_file_manager --copy "/path/to/source" "/path/to/target"
```

### Options
- `source`: Positional argument for the source folder.
- `target`: Positional argument for the target folder.
- `-s`, `--source`: Alternative way to specify the source folder.
- `-t`, `--target`: Alternative way to specify the target folder.
- `-c`, `--copy`: Copy files instead of moving them.

### Default Folders
If no arguments are provided, the script defaults to:
- Source: `~/Pictures/Nikon Transfer 2`
- Target: `~/Pictures/RAW`
