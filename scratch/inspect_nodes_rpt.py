import sys, os, pandas as pd
sys.path.append(os.getcwd())
from extraction.out.swmm_rpt_base import _extract_nodes_rpt

model_dir = r'scratch\\swmm_case_test1'
res = _extract_nodes_rpt(model_dir)
merged = res['merged_results']
print('All merged rows:', merged.shape)
print(merged[['node_id','type','Avg_Depth','Max_Depth','Max_HGL','Time_of_Max_Depth']])
print('Unique types:', merged['type'].unique().tolist())
