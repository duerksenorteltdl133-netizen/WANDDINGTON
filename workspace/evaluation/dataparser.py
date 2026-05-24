import json
import os
import warnings

os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/numba_cache")
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

import scanpy as sc
import sc_agent.ui as ui

# Suppress noisy Scanpy read warnings.
warnings.filterwarnings('ignore')

class DataParser:
    """
    Single-cell dataset parsing utility.
    Extracts metadata from `.h5ad` files and produces an LLM-friendly JSON summary.
    """
    def __init__(self):
        # Reduce verbose Scanpy logging.
        sc.settings.verbosity = 0 

    def profile_dataset(self, h5ad_path: str) -> str:
        """
        Read an `.h5ad` file and return a JSON string of core dataset features.
        """
        if not os.path.exists(h5ad_path):
            return json.dumps({"error": f"File not found: {h5ad_path}"}, ensure_ascii=False)
            
        try:
            ui.log("Parser", f"parsing single-cell dataset: {os.path.basename(h5ad_path)}")
            
            # Key optimization: use `backed='r'` mode.
            # This avoids loading the full matrix into memory and only reads metadata (`obs`, `var`).
            adata = sc.read_h5ad(h5ad_path, backed='r')
            
            # 1. Extract basic dimensions.
            n_cells, n_genes = adata.shape
            
            # 2. Heuristically identify perturbation and cell-type columns.
            obs_columns = list(adata.obs.columns)
            # Common perturbation-related keywords.
            pert_keywords = ['condition', 'perturb', 'trt', 'dose', 'drug', 'ko']
            pert_columns = [col for col in obs_columns if any(kw in col.lower() for kw in pert_keywords)]
            
            # Common cell-type-related keywords.
            ct_keywords = ['cell_type', 'celltype', 'cluster', 'seurat_clusters']
            ct_columns = [col for col in obs_columns if any(kw in col.lower() for kw in ct_keywords)]
            
            # 3. Inspect highly variable genes (HVGs).
            has_hvg = 'highly_variable' in adata.var.columns
            # Count HVGs when available.
            if has_hvg:
                # In backed mode, convert lightly before summing.
                hvg_count = int(sum(adata.var['highly_variable'])) 
            else:
                hvg_count = 0
            
            # 4. Assemble the standard report.
            report = {
                "dataset_name": os.path.basename(h5ad_path),
                "status": "success",
                "dimensions": {
                    "number_of_cells": n_cells,
                    "number_of_genes": n_genes
                },
                "metadata_features": {
                    "all_obs_columns": obs_columns,
                    "potential_perturbation_keys": pert_columns,
                    "potential_cell_type_keys": ct_columns
                },
                "gene_features": {
                    "highly_variable_genes_calculated": has_hvg,
                    "hvg_count": hvg_count
                }
            }
            
            # 5. Preview concrete perturbation categories (top 10).
            if pert_columns:
                main_pert_col = pert_columns[0]
                # Count cells for each perturbation condition.
                unique_perts = adata.obs[main_pert_col].value_counts().head(10).to_dict()
                report["perturbation_preview"] = {
                    "column_used": main_pert_col,
                    "top_conditions_cell_count": unique_perts
                }
            
            # Release the file handle.
            adata.file.close()
            
            return json.dumps(report, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({"error": f"Failed to parse dataset: {str(e)}"}, ensure_ascii=False)
