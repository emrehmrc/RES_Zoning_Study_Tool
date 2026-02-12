
import unittest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock streamlit before importing ui modules
sys.modules['streamlit'] = MagicMock()

from ui.tab_scoring import ScoringTab

class TestRasterSelection(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.mock_state = MagicMock()
        self.tab = ScoringTab(self.mock_state)

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)

    def result_files(self, files):
        """Helper to create files in test dir"""
        for f in files:
            Path(os.path.join(self.test_dir, f)).touch()

    def test_scan_empty_directory(self):
        result = self.tab._scan_directory_for_rasters(self.test_dir)
        self.assertEqual(result, [])

    def test_scan_valid_rasters(self):
        files = ['image1.tif', 'image2.tiff', 'MAP.TIF']
        self.result_files(files)
        
        result = self.tab._scan_directory_for_rasters(self.test_dir)
        self.assertEqual(len(result), 3)
        self.assertIn('image1.tif', result)
        self.assertIn('image2.tiff', result)
        self.assertIn('MAP.TIF', result)

    def test_scan_mixed_files(self):
        files = ['data.csv', 'image.png', 'raster.tif']
        self.result_files(files)
        
        result = self.tab._scan_directory_for_rasters(self.test_dir)
        self.assertEqual(result, ['raster.tif'])

    def test_scan_non_existent_directory(self):
        result = self.tab._scan_directory_for_rasters("non_existent_path_12345")
        self.assertEqual(result, [])
    
    def test_scan_file_path_instead_of_dir(self):
        file_path = os.path.join(self.test_dir, 'test.txt')
        Path(file_path).touch()
        
        result = self.tab._scan_directory_for_rasters(file_path)
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()
