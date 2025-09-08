import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pandas as pd
from extraction.out.swmm_links_rpt import extract_swmmlinks_rpt

def main(folder):
    data = extract_swmmlinks_rpt(folder)
    mr = data.get('merged_results', pd.DataFrame())
    print('merged_results cols:', list(mr.columns))
    print('head row:', mr.head(1).to_dict(orient='records'))

if __name__ == '__main__':
    folder = sys.argv[1]
    main(folder)

