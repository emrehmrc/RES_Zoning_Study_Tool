import io
import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from api.csv_utils import detect_csv_delimiter, read_uploaded_csv


class CSVUtilsTests(unittest.TestCase):
    def test_detects_semicolon_when_unquoted_wkt_contains_commas(self):
        content = (
            "cell_id;wkt;score;distance\n"
            "0;POLYGON ((0 0, 1 0, 1 1, 0 0));12,5;3,1\n"
            "1;POLYGON ((0 0, 2 0, 2 2, 1 3, 0 0));13,5;4,1\n"
        )

        self.assertEqual(detect_csv_delimiter(content), ";")

        dataframe, delimiter = read_uploaded_csv(io.BytesIO(content.encode("utf-8")))
        self.assertEqual(delimiter, ";")
        self.assertEqual(dataframe.shape, (2, 4))
        self.assertEqual(dataframe.loc[1, "cell_id"], 1)
        self.assertTrue(dataframe.loc[1, "wkt"].startswith("POLYGON"))

    def test_detects_standard_comma_csv_with_quoted_wkt(self):
        content = (
            'cell_id,wkt,score\n'
            '0,"POLYGON ((0 0, 1 0, 1 1, 0 0))",12.5\n'
        )

        dataframe, delimiter = read_uploaded_csv(io.BytesIO(content.encode("utf-8")))
        self.assertEqual(delimiter, ",")
        self.assertEqual(dataframe.shape, (1, 3))
        self.assertEqual(dataframe.loc[0, "score"], 12.5)

    def test_reads_utf8_bom(self):
        content = "cell_id;wkt;name\n0;POINT (0 0);Turkiye\n"
        dataframe, delimiter = read_uploaded_csv(
            io.BytesIO(b"\xef\xbb\xbf" + content.encode("utf-8"))
        )

        self.assertEqual(delimiter, ";")
        self.assertEqual(dataframe.columns.tolist(), ["cell_id", "wkt", "name"])


if __name__ == "__main__":
    unittest.main()
