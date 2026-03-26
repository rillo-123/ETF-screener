import json
from pathlib import Path
from ETF_screener.xetra_extractor import XETRETFExtractor

def update():
    # Load names from CSV
    extractor = XETRETFExtractor()
    potential = extractor.extract_etf_tickers()
    
    # Load current JSON
    etfs_path = Path('config/etfs.json')
    if not etfs_path.exists():
        print("etfs.json not found")
        return
        
    with open(etfs_path, 'r') as f:
        data = json.load(f)
        
    updated = 0
    for ticker, name in potential.items():
        if ticker not in data:
            data[ticker] = {"status": "active", "name": name}
            updated += 1
        else:
            info = data[ticker]
            if not isinstance(info, dict):
                data[ticker] = {"status": "active", "name": name}
                updated += 1
            elif "name" not in info or not info["name"]:
                info["name"] = name
                updated += 1
            
    # Save back
    with open(etfs_path, 'w') as f:
        json.dump(data, f, indent=2)
        
    print(f"Updated {updated} tickers with names in etfs.json")

if __name__ == "__main__":
    update()
