import csv
import io
from collections import Counter

import pandas as pd


CSV_DELIMITERS = (",", ";", "\t", "|")


def detect_csv_delimiter(sample: str) -> str:
    """Choose the delimiter whose header and data rows have a stable width."""
    best_delimiter = None
    best_score = None

    for delimiter in CSV_DELIMITERS:
        try:
            reader = csv.reader(io.StringIO(sample), delimiter=delimiter)
            rows = []
            for row in reader:
                if row:
                    rows.append(row)
                if len(rows) >= 100:
                    break
        except csv.Error:
            continue

        if not rows:
            continue

        widths = [len(row) for row in rows]
        data_widths = widths[1:] or widths
        modal_width, modal_count = Counter(data_widths).most_common(1)[0]
        score = (
            widths[0] == modal_width,
            modal_count / len(data_widths),
            modal_width > 1,
            modal_width,
        )

        if best_score is None or score > best_score:
            best_delimiter = delimiter
            best_score = score

    if best_delimiter is None or best_score is None or not best_score[2]:
        raise ValueError("Could not detect the CSV delimiter.")

    return best_delimiter


def read_uploaded_csv(uploaded_file):
    """Read a binary uploaded CSV without first copying the whole file to text."""
    sample = uploaded_file.read(64 * 1024)
    uploaded_file.seek(0)

    if isinstance(sample, str):
        sample_text = sample
        encoding = None
    else:
        encoding = "utf-8-sig"
        try:
            sample_text = sample.decode(encoding)
        except UnicodeDecodeError:
            encoding = "cp1252"
            sample_text = sample.decode(encoding)

    delimiter = detect_csv_delimiter(sample_text)
    dataframe = pd.read_csv(uploaded_file, sep=delimiter, encoding=encoding)
    return dataframe, delimiter
