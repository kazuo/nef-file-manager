import argparse

from pathlib import Path

from .core import organize_raw_files

def main():
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
    
    organize_raw_files(source_folder, target_folder)

if __name__ == "__main__":
    main()
