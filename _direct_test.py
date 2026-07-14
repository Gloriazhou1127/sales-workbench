"""Direct test of the CSV import filtering logic using actual app.py code"""
import sys
sys.path.insert(0, 'server')

import io, csv

csv_path = "_test_upload.csv"

# Replicate _parse_file logic
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    csv_reader = csv.reader(f)
    raw_headers = next(csv_reader)
    
    # Dedup
    seen = set()
    headers = []
    col_index = []
    for i, h in enumerate(raw_headers):
        h_clean = h.strip() if h else ''
        if h_clean and h_clean not in seen:
            seen.add(h_clean)
            headers.append(h_clean)
            col_index.append(i)
    
    print(f"Headers ({len(headers)}): {headers}")
    
    rows_data = []
    for row in csv_reader:
        if any(v and v.strip() for v in row):
            d = {}
            for j, idx in enumerate(col_index):
                if idx < len(row):
                    d[headers[j]] = row[idx]
            rows_data.append(d)
    
    print(f"Total rows: {len(rows_data)}")
    
    # Now replicate the _get_col and filtering logic
    CUSTOMER_SALES_COUNT_KEYS = ('教学一体机售卖台数', '一体机售卖台数', '售卖台数', 'sales_count')

    def _get_col(row, *keys):
        for k in keys:
            if k in row:
                return row[k]
        return None

    filtered = 0
    for row_idx, row in enumerate(rows_data):
        sales_str = str(_get_col(row, *CUSTOMER_SALES_COUNT_KEYS) or '')
        sales_count = 0
        try:
            sales_count = int(float(sales_str.replace(',', '').replace('--', '0')))
        except (ValueError, TypeError):
            sales_count = 0
        if sales_count >= 5:
            filtered += 1
            if filtered <= 20:
                name = str(_get_col(row, *('客户',)) or '')
                print(f"  FILTER #{row_idx}: name={name} sales_raw={sales_str!r} sales_int={sales_count}")
    
    print(f"\nTotal filtered: {filtered} / {len(rows_data)}")
