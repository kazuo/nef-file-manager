import argparse
import sys
from pathlib import Path

from .core import organize_raw_files, eject_volume

def main():
    parser = argparse.ArgumentParser(
        description="Organize RAW files by date based on EXIF data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m nef_file_manager "/path/to/source" "/path/to/target"
  python -m nef_file_manager --source "/Users/user/Pictures/Nikon Transfer 2" --target "/Users/user/Pictures/RAW"
  python -m nef_file_manager --copy "/path/to/source" "/path/to/target"
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

    parser.add_argument(
        "-c", "--copy",
        action="store_true",
        help="Copy files instead of moving them"
    )

    parser.add_argument(
        "-e", "--eject",
        action="store_true",
        help="Eject the source volume after copying (only if it's an external volume)"
    )

    args = parser.parse_args()
    
    # Use flag values if provided, otherwise use positional arguments
    source_input = (args.source_flag or args.source or "").strip()
    target_input = (args.target_flag or args.target or "").strip()
    
    # Set defaults if no arguments provided
    if not source_input:
        home_dir = Path.home()
        source_path = home_dir / "Pictures" / "Nikon Transfer 2"
        print(f"Using default source folder: {source_path}")
    else:
        source_path = Path(source_input).expanduser()
    
    if not target_input:
        home_dir = Path.home()
        target_path = home_dir / "Pictures" / "RAW"
        print(f"Using default target folder: {target_path}")
    else:
        target_path = Path(target_input).expanduser()
    
    # Validate that source folder exists
    if not source_path.exists():
        print(f"Error: Source folder '{source_path}' does not exist.")
        sys.exit(1)
    
    # Ensure target folder exists
    if not target_path.exists():
        print(f"Target folder '{target_path}' does not exist. Creating it...")
        target_path.mkdir(parents=True, exist_ok=True)
    
    # Resolve paths to handle symlinks and get absolute paths
    final_source = str(source_path.resolve())
    final_target = str(target_path.resolve())
    
    print(f"Source: {final_source}")
    print(f"Target: {final_target}")
    
    organize_raw_files(final_source, final_target, copy_only=args.copy)

    # Automatically eject if flag is set
    if args.eject:
        eject_volume(final_source)

if __name__ == "__main__":
    main()
