import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from pathlib import Path

from nef_file_manager.core import parse_exif, get_image_datetime, create_folder, move_image


def test_parse_exif_simple():
    raw_stdout = (
        "Field 1         : Value 1\n"
        "Field 2         : Value 2\n"
        "Field 3 With Space: Value 3"
    )
    expected = {
        "Field 1": "Value 1",
        "Field 2": "Value 2",
        "Field 3 With Space": "Value 3"
    }
    assert parse_exif(raw_stdout) == expected


def test_parse_exif_repeated_key():
    raw_stdout = (
        "Field 1         : Value 1a\n"
        "Field 2         : Value 2\n"
        "Field 1         : Value 1b"
    )
    expected = {
        "Field 1": ["Value 1a", "Value 1b"],
        "Field 2": "Value 2"
    }
    assert parse_exif(raw_stdout) == expected


def test_parse_exif_empty_input():
    assert parse_exif("") == {}


def test_parse_exif_malformed_line():
    # A line without a colon should cause an error when accessing row[1]
    raw_stdout = "Field 1 : Value1\nMalformed Line Without Colon"
    with pytest.raises(IndexError):
        parse_exif(raw_stdout)


def test_get_image_datetime_valid_single():
    exif_data = {"Create Date": "2023:01:15 10:30:00"}
    expected_dt = datetime(2023, 1, 15, 10, 30, 0)
    assert get_image_datetime(exif_data) == expected_dt


def test_get_image_datetime_valid_list():
    exif_data = {"Create Date": ["2023:01:15 10:30:00", "2024:02:20 11:00:00"]}
    expected_dt = datetime(2023, 1, 15, 10, 30, 0)
    assert get_image_datetime(exif_data) == expected_dt


def test_get_image_datetime_missing_key():
    exif_data = {"Some Other Key": "Some Value"}
    with pytest.raises(KeyError):
        get_image_datetime(exif_data)


def test_get_image_datetime_invalid_format():
    exif_data = {"Create Date": "2023-01-15 10:30:00"}  # Incorrect date format
    with pytest.raises(ValueError):
        get_image_datetime(exif_data)


def test_get_image_datetime_not_string_or_list():
    exif_data = {"Create Date": 12345}
    with pytest.raises(TypeError):  # strptime expects a string
        get_image_datetime(exif_data)


@patch('nef_file_manager.core.get_image_datetime')
@patch('os.mkdir')
@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
def test_create_folder_new_year_and_date(mock_path_is_dir, mock_path_exists, mock_os_mkdir, mock_get_dt):
    # Configure mocks
    mock_get_dt.return_value = datetime(2023, 7, 15)
    # Simulate no folders exist initially
    mock_path_exists.return_value = False
    mock_path_is_dir.return_value = False

    base_folder = "/test/base"
    expected_folder_path = f"{base_folder}/2023/2023-07-15"

    result_path = create_folder({}, base_folder)

    assert result_path == expected_folder_path

    # Check that os.mkdir was called for year and date folders
    expected_year_folder = f"{base_folder}/2023"
    expected_date_folder = f"{base_folder}/2023/2023-07-15"

    # Verify os.mkdir calls
    assert mock_os_mkdir.call_count == 2
    mock_os_mkdir.assert_any_call(expected_year_folder)
    mock_os_mkdir.assert_any_call(expected_date_folder)


@patch('nef_file_manager.core.get_image_datetime')
def test_create_folder_no_datetime(mock_get_dt):
    mock_get_dt.return_value = None  # Simulate image_dt being None

    result_path = create_folder({}, "/test/base")
    assert result_path is None


@patch('nef_file_manager.core.get_image_datetime')
@patch('nef_file_manager.core.os.mkdir')
@patch('nef_file_manager.core.Path')
def test_create_folder_year_exists_date_new(mock_path_class, mock_os_mkdir, mock_get_dt):
    mock_get_dt.return_value = datetime(2023, 7, 15)

    def path_side_effect(path_str):
        mock_path = MagicMock()
        if "2023-07-15" in str(path_str):
            # Date folder doesn't exist
            mock_path.exists.return_value = False
            mock_path.is_dir.return_value = False
        else:
            # Year folder exists
            mock_path.exists.return_value = True
            mock_path.is_dir.return_value = True
        return mock_path

    mock_path_class.side_effect = path_side_effect

    result = create_folder({}, "/test/base")

    # Only date folder should be created
    assert mock_os_mkdir.call_count == 1
    mock_os_mkdir.assert_called_with("/test/base/2023/2023-07-15")


@patch('shutil.move')
@patch('glob.iglob')
def test_move_image_single_file(mock_glob_iglob, mock_shutil_move):
    # Create mock image file
    mock_image_file = MagicMock(spec=Path)
    mock_image_file.stem = "test_image"
    mock_image_file.parent = Path("/fake/source")

    # Simulate glob finding one related file
    related_file_path_str = "/fake/source/test_image.nef"
    mock_glob_iglob.return_value = [related_file_path_str]

    to_folder = "/fake/destination/2023-01-01"
    move_image(mock_image_file, to_folder)

    mock_glob_iglob.assert_called_once_with(f"{mock_image_file.parent}/**", recursive=True)
    mock_shutil_move.assert_called_once()

    # Check the call arguments
    call_args = mock_shutil_move.call_args
    assert str(call_args[0][0]) == related_file_path_str
    assert call_args[0][1] == f"{to_folder}/test_image.nef"


@patch('shutil.move')
@patch('glob.iglob')
def test_move_image_multiple_related_files(mock_glob_iglob, mock_shutil_move):
    mock_image_file = MagicMock(spec=Path)
    mock_image_file.stem = "test_image"
    mock_image_file.parent = Path("/fake/source")

    # Simulate finding multiple related files
    related_files = [
        "/fake/source/test_image.nef",
        "/fake/source/test_image.jpg",
        "/fake/source/test_image.mov",
        "/fake/source/unrelated_file.nef"  # This should be ignored
    ]
    mock_glob_iglob.return_value = related_files

    to_folder = "/fake/destination/2023-01-01"
    move_image(mock_image_file, to_folder)

    # Should be called 3 times (excluding unrelated file)
    assert mock_shutil_move.call_count == 3


@patch('shutil.move')
@patch('glob.iglob')
def test_move_image_no_matching_files(mock_glob_iglob, mock_shutil_move):
    mock_image_file = MagicMock(spec=Path)
    mock_image_file.stem = "test_image"
    mock_image_file.parent = Path("/fake/source")

    # Simulate no matching files found
    mock_glob_iglob.return_value = ["/fake/source/different_file.nef"]

    to_folder = "/fake/destination/2023-01-01"
    move_image(mock_image_file, to_folder)

    # Should not move anything
    mock_shutil_move.assert_not_called()


# Parametrized tests for different date formats (bonus pytest feature)
@pytest.mark.parametrize("date_string,expected_dt", [
    ("2023:01:15 10:30:00", datetime(2023, 1, 15, 10, 30, 0)),
    ("2024:12:31 23:59:59", datetime(2024, 12, 31, 23, 59, 59)),
    ("2022:06:15 00:00:00", datetime(2022, 6, 15, 0, 0, 0)),
])
def test_get_image_datetime_parametrized(date_string, expected_dt):
    exif_data = {"Create Date": date_string}
    assert get_image_datetime(exif_data) == expected_dt


# Test fixtures example (if you want to reuse test data)
@pytest.fixture
def sample_exif_data():
    return {
        "Create Date": "2023:07:15 14:30:00",
        "Camera Model": "Nikon D850",
        "ISO Speed": "100"
    }


def test_create_folder_with_fixture(sample_exif_data):
    with patch('nef_file_manager.core.get_image_datetime') as mock_get_dt:
        with patch('os.mkdir') as mock_mkdir:
            with patch('pathlib.Path.exists', return_value=False):
                with patch('pathlib.Path.is_dir', return_value=False):
                    mock_get_dt.return_value = datetime(2023, 7, 15)

                    result = create_folder(sample_exif_data, "/test")

                    assert result == "/test/2023/2023-07-15"
                    assert mock_mkdir.call_count == 2