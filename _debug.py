"""Debug: test the CSV parsing and filtering logic"""
import csv
import io

path = "_test_upload.csv"

with open(path, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    raw_headers = next(reader)
    
    # De-duplicate (same logic as _parse_file)
    seen = set()
    headers = []
    col_index = []
    for i, h in enumerate(raw_headers):
        h_clean = h.strip() if h else ''
        if h_clean and h_clean not in seen:
            seen.add(h_clean)
            headers.append(h_clean)
            col_index.append(i)
    
    print("Headers after dedup:", headers)
    print("Has '教学一体机售卖台数':", '教学一体机售卖台数' in headers)
    
    # Find the index of the sales count column
    sales_idx = None
    for j, h in enumerate(headers):
        if h == '教学一体机售卖台数':
            sales_idx = j
            break
    
    print(f"Sales count column index in headers: {sales_idx}")
    
    # Test first 20 rows
    filtered = 0
    total = 0
    for row in reader:
        if any(v and v.strip() for v in row):
            d = {}
            for j, idx in enumerate(col_index):
                if idx < len(row):
                    d[headers[j]] = row[idx]
            
            name = d.get('客户', '')
            sales_val = d.get('教学一体机售卖台数', '')
            
            # Filtering logic
            sales_str = str(sales_val or '')
            sales_count = 0
            try:
                sales_count = int(float(sales_str.replace(',', '').replace('--', '0')))
            except (ValueError, TypeError):
                sales_count = 0
            
            if sales_count >= 5:
                filtered += 1
                if total < 20:
                    print(f"  FILTERED: name={name} sales={sales_val} count={sales_count}")
            total += 1
            if total >= 50:
                break
    
    print(f"\nTotal processed: {total}, Filtered (>=5): {filtered}")
