import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from pathlib import Path
import os
import json

from nef_file_manager.core import (
    get_batch_exif,
    get_image_datetime, 
    create_folder, 
    transfer_single_file, 
    organize_raw_files,
    get_mount_point,
    eject_volume
)

def test_get_batch_exif_success():
    mock_stdout = json.dumps([
        {"SourceFile": "/path/to/file1.nef", "CreateDate": "2023:01:15 10:30:00"},
        {"SourceFile": "/path/to/file2.nef", "CreateDate": "2023:01:16 11:00:00"}
    ])
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_stdout, returncode=0)
        
        result = get_batch_exif(["/path/to/file1.nef", "/path/to/file2.nef"])
        
        assert len(result) == 2
        assert result["/path/to/file1.nef"]["CreateDate"] == "2023:01:15 10:30:00"
        assert result["/path/to/file2.nef"]["CreateDate"] == "2023:01:16 11:00:00"

def test_get_image_datetime_valid():
    exif_data = {"CreateDate": "2023:01:15 10:30:00"}
    expected_dt = datetime(2023, 1, 15, 10, 30, 0)
    assert get_image_datetime(exif_data) == expected_dt

def test_get_image_datetime_fallback():
    exif_data = {"DateTimeOriginal": "2023:01:15 10:30:00"}
    expected_dt = datetime(2023, 1, 15, 10, 30, 0)
    assert get_image_datetime(exif_data) == expected_dt

def test_get_image_datetime_invalid():
    exif_data = {"CreateDate": "invalid format"}
    assert get_image_datetime(exif_data) is None

@patch('nef_file_manager.core.get_image_datetime')
@patch('pathlib.Path.mkdir')
@patch('pathlib.Path.exists')
def test_create_folder(mock_exists, mock_mkdir, mock_get_dt):
    mock_get_dt.return_value = datetime(2023, 7, 15)
    mock_exists.return_value = False
    
    base_folder = "/test/base"
    result_path, created = create_folder({}, base_folder)
    
    assert "/2023/2023-07-15" in result_path
    assert created is True
    assert mock_mkdir.call_count >= 1

@patch('os.chflags')
@patch('shutil.move')
def test_transfer_single_file_move(mock_move, mock_chflags):
    source = Path("/src/file.nef")
    dest_dir = "/dest/2023-01-01"
    
    with patch('pathlib.Path.exists', return_value=False):
        success = transfer_single_file(source, dest_dir, copy_only=False)
        
        assert success is True
        mock_move.assert_called_once()
        # On macOS, it tries to clear flags
        assert mock_chflags.call_count >= 1

@patch('subprocess.run')
def test_transfer_single_file_copy_rsync(mock_run):
    source = Path("/src/file.nef")
    dest_dir = "/dest/2023-01-01"
    
    with patch('pathlib.Path.exists', return_value=False):
        success = transfer_single_file(source, dest_dir, copy_only=True)
        
        assert success is True
        # Check if rsync was called
        args, _ = mock_run.call_args
        assert 'rsync' in args[0]

@patch('os.path.ismount')
def test_get_mount_point(mock_ismount):
    mock_ismount.side_effect = lambda p: str(p) == '/Volumes/NIKON' or str(p) == '/'
    assert get_mount_point('/Volumes/NIKON/DCIM/100') == '/Volumes/NIKON'

@patch('nef_file_manager.core.get_mount_point')
@patch('subprocess.run')
def test_eject_volume_success(mock_run, mock_get_mount):
    mock_get_mount.return_value = '/Volumes/NIKON'
    mock_run.return_value = MagicMock(returncode=0)
    
    eject_volume('/Volumes/NIKON/DCIM')
    mock_run.assert_called_once()
    assert 'eject' in mock_run.call_args[0][0]
