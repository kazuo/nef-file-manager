import pytest
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path
from nef_file_manager.__main__ import main

def test_main_source_not_found_with_repr():
    """Test that the error message uses repr() and exits when source is not found."""
    with patch("sys.argv", ["nef_file_manager", "/non/existent/path"]), \
         patch("sys.exit") as mock_exit, \
         patch("builtins.print") as mock_print:
        
        main()
        
        # Verify that print was called with the repr of the path
        any_call_with_error = any("Error: Source folder '/non/existent/path'" in str(call) for call in mock_print.call_args_list)
        assert any_call_with_error
        mock_exit.assert_called_with(1)

def test_main_source_with_trailing_space_fallback():
    """Test that the logic successfully falls back to a path with a trailing space."""
    source_path = "/Volumes/NIKON"
    source_with_space = "/Volumes/NIKON "
    
    with patch("sys.argv", ["nef_file_manager", source_path, "/tmp/target"]), \
         patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.mkdir"), \
         patch("nef_file_manager.__main__.organize_raw_files") as mock_organize, \
         patch("pathlib.Path.resolve") as mock_resolve:
        
        # First call for source_path (/Volumes/NIKON) -> False
        # Second call for alt_path (/Volumes/NIKON ) -> True
        # Third call for target_path -> True
        mock_exists.side_effect = [False, True, True]
        
        mock_resolve.side_effect = lambda: MagicMock(__str__=lambda self: source_with_space)
        
        main()
        
        mock_organize.assert_called_once()
        args, _ = mock_organize.call_args
        assert " " in str(args[0])

def test_main_source_without_strip():
    """Test that leading/trailing spaces in source are preserved (no longer stripped)."""
    source_path = "  /path/with/spaces  "
    
    with patch("sys.argv", ["nef_file_manager", source_path]), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.mkdir"), \
         patch("nef_file_manager.__main__.organize_raw_files") as mock_organize, \
         patch("pathlib.Path.resolve") as mock_resolve:
        
        mock_resolve.side_effect = lambda: MagicMock(__str__=lambda self: source_path)
        
        main()
        
        mock_organize.assert_called_once()
        args, _ = mock_organize.call_args
        assert args[0] == source_path
