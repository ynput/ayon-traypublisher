import pytest
import csv
import io
from unittest.mock import patch, MagicMock
from csv_ingest import ingest_csv


@patch('csv_ingest.get_project')
@patch('csv_ingest.get_folder_by_path')
@patch('csv_ingest.create_folder')
@patch('csv_ingest.update_folder')
def test_ingest_csv_with_description(
    mock_update, mock_create, mock_get_folder, mock_get_project
):
    mock_get_project.return_value = True
    mock_get_folder.return_value = None

    csv_content = "folder,parent,description\nAssets,,Top level folder\nCharacters,Assets,Character models\n"
    csv_file = io.StringIO(csv_content)

    with patch('csv_ingest.open', return_value=csv_file):
        ingest_csv('test_project', 'dummy.csv')

    # Check that create_folder was called with descriptions
    assert mock_create.call_count == 2
    calls = mock_create.call_args_list
    assert calls[0][1]['folder_data']['description'] == 'Top level folder'
    assert calls[1][1]['folder_data']['description'] == 'Character models'


@patch('csv_ingest.get_project')
@patch('csv_ingest.get_folder_by_path')
@patch('csv_ingest.update_folder')
@patch('csv_ingest.create_folder')
def test_ingest_csv_update_existing_description(
    mock_create, mock_update, mock_get_folder, mock_get_project
):
    mock_get_project.return_value = True
    # Simulate existing folder
    mock_get_folder.return_value = {'id': 'folder_id_1'}

    csv_content = "folder,parent,description\nExistingFolder,,Updated description\n"
    csv_file = io.StringIO(csv_content)

    with patch('csv_ingest.open', return_value=csv_file):
        ingest_csv('test_project', 'dummy.csv')

    mock_update.assert_called_once_with(
        'test_project', 'folder_id_1', description='Updated description'
    )
    mock_create.assert_not_called()
