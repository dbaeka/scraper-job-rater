import os
import tempfile
import unittest
from unittest.mock import patch, mock_open

from src.utils.helpers import get_config, extract_resume_text


class TestHelpers(unittest.TestCase):
    def test_get_config(self):
        """Test that get_config correctly loads YAML configuration."""
        mock_config = {
            'search_criteria': {
                'job_titles': ['Test Job']
            },
            'resume_path': 'test/path'
        }

        # Mock the open function and yaml.safe_load
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('yaml.safe_load', return_value=mock_config):
                config = get_config('test_config.yaml')

                # Verify the config was loaded correctly
                self.assertEqual(config['search_criteria']['job_titles'][0], 'Test Job')
                self.assertEqual(config['resume_path'], 'test/path')

                # Verify open was called with the right file
                mock_file.assert_called_once_with('test_config.yaml', 'r')

    def test_extract_resume_text(self):
        """Test that extract_resume_text correctly extracts text from PDF files."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # This test would normally create a PDF file, but we'll mock PdfReader instead
            with patch('src.utils.helpers.PdfReader') as mock_pdf_reader:
                # Set up the mock to return pages with text
                mock_page1 = type('Page', (), {'extract_text': lambda: 'Test resume text page 1'})
                mock_page2 = type('Page', (), {'extract_text': lambda: 'Test resume text page 2'})
                mock_pdf_reader.return_value.pages = [mock_page1, mock_page2]

                # Create an empty PDF file in the temp directory
                pdf_path = os.path.join(temp_dir, 'test_resume.pdf')
                with open(pdf_path, 'w') as f:
                    f.write('dummy pdf content')

                # Call the function
                result = extract_resume_text(temp_dir)

                # Verify the result
                self.assertEqual(result, 'Test resume text page 1\nTest resume text page 2')


if __name__ == '__main__':
    unittest.main()
