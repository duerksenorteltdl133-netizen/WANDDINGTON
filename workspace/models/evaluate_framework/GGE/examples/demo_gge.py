#!/usr/bin/env python
# coding: utf-8

# # GGE: Generated Genetic Expression Evaluator
# 
# This notebook demonstrates the core functionality of the `gge-eval` library for evaluating gene expression generative models.
# 
# **Paper**: A Standardized Framework for Evaluating Gene Expression Generative Models  
# **Accepted at**: Gen2 Workshop at ICLR 2026

# ## Setup
# 
# Install the library if needed:
# ```bash
# pip install gge-eval
# ```

# In[1]:


import sys
sys.path.insert(0, '../src')


# In[9]:


import numpy as np
import pandas as pd
import anndata as ad
from scipy import sparse

# GGE imports
from gge import (
    evaluate,
    evaluate_lazy,
    evaluate_deg_space,
    evaluate_pc_space,
    compute_perturbation_effect_correlation,
)
from gge.metrics import (
    PearsonCorrelation,
    SpearmanCorrelation,
    RSquared,
    Wasserstein1Distance,
    Wasserstein2Distance,
    MMDDistance,
    MSEDistance,
)

print("GGE imported successfully!")


# ## Create Synthetic Gene Expression Data
# 
# We create realistic synthetic data with:
# - 200 samples (100 control, 100 perturbed)
# - 500 genes
# - Generated data that approximates real data with some noise

# In[3]:


np.random.seed(42)

n_samples = 200
n_genes = 500
n_control = 100
n_perturbed = 100

# Generate base expression (log-normal distribution typical of RNA-seq)
base_expression = np.random.lognormal(mean=2, sigma=1, size=(n_samples, n_genes))

# Add perturbation effect to second half (perturbed samples)
# Some genes are differentially expressed (DEGs)
n_degs = 50
deg_indices = np.random.choice(n_genes, n_degs, replace=False)
perturbation_effect = np.zeros(n_genes)
perturbation_effect[deg_indices] = np.random.uniform(-2, 2, n_degs)  # Log2 fold change

# Apply perturbation effect
real_expression = base_expression.copy()
real_expression[n_control:, :] *= np.exp(perturbation_effect)  # Apply fold change

# Create "generated" data - approximates real with some noise
generated_expression = real_expression + np.random.normal(0, 0.5, real_expression.shape)
generated_expression = np.maximum(generated_expression, 0)  # Non-negative

# Create observation metadata
obs_data = pd.DataFrame({
    'condition': ['control'] * n_control + ['perturbed'] * n_perturbed,
    'cell_type': np.random.choice(['TypeA', 'TypeB'], n_samples),
    'split': np.random.choice(['train', 'test'], n_samples, p=[0.7, 0.3]),
})

# Create gene metadata
var_data = pd.DataFrame({
    'gene_name': [f'Gene_{i}' for i in range(n_genes)],
}, index=[f'Gene_{i}' for i in range(n_genes)])

# Create AnnData objects
real_adata = ad.AnnData(
    X=real_expression,
    obs=obs_data.copy(),
    var=var_data.copy(),
)

generated_adata = ad.AnnData(
    X=generated_expression,
    obs=obs_data.copy(),
    var=var_data.copy(),
)

print(f"Real data: {real_adata.shape}")
print(f"Generated data: {generated_adata.shape}")
print(f"Conditions: {real_adata.obs['condition'].value_counts().to_dict()}")
print(f"Number of DEGs: {n_degs}")


# ## Basic Evaluation
# 
# The `evaluate()` function computes all metrics across conditions.

# In[4]:


# Run evaluation
results = evaluate(
    real_data=real_adata,
    generated_data=generated_adata,
    condition_columns=['condition'],
    metrics=['pearson', 'spearman', 'r_squared', 'wasserstein_1', 'mmd'],
)

# Display summary
print(results.summary())


# ## Individual Metrics
# 
# You can also compute metrics individually for more control.

# In[5]:


# Compute individual metrics
pearson = PearsonCorrelation()
spearman = SpearmanCorrelation()
r_squared = RSquared()
mse = MSEDistance()

# Get data for perturbed condition
mask = real_adata.obs['condition'] == 'perturbed'
real_perturbed = real_adata[mask].X
gen_perturbed = generated_adata[mask].X

# Compute metrics
pearson_result = pearson.compute(real_perturbed, gen_perturbed)
spearman_result = spearman.compute(real_perturbed, gen_perturbed)
r2_result = r_squared.compute(real_perturbed, gen_perturbed)
mse_result = mse.compute(real_perturbed, gen_perturbed)

print("Perturbed condition metrics:")
print(f"  Pearson correlation: {pearson_result.aggregate_value:.4f}")
print(f"  Spearman correlation: {spearman_result.aggregate_value:.4f}")
print(f"  R-squared: {r2_result.aggregate_value:.4f}")
print(f"  MSE: {mse_result.aggregate_value:.4f}")


# ## Perturbation-Effect Correlation (Paper Eq. 1)
# 
# This metric measures whether the model captures the **direction and magnitude** of perturbation effects:
# 
# $$\rho_{effect} = \text{corr}(\mu_{real} - \mu_{ctrl}, \mu_{gen} - \mu_{ctrl})$$
# 
# This is more informative than raw correlation when evaluating perturbation models.

# In[6]:


# Compute control mean
control_mask = real_adata.obs['condition'] == 'control'
control_mean = real_adata[control_mask].X.mean(axis=0)

# Get perturbed samples
perturbed_mask = real_adata.obs['condition'] == 'perturbed'

# Compute perturbation-effect correlation
rho_effect = compute_perturbation_effect_correlation(
    real_perturbed=real_adata[perturbed_mask].X,
    generated_perturbed=generated_adata[perturbed_mask].X,
    control_mean=control_mean,
    method='pearson',
)

print(f"Perturbation-effect correlation: {rho_effect:.4f}")
print("\nInterpretation: Higher values indicate the model better captures")
print("the direction and magnitude of perturbation effects.")


# ## PC-Space Evaluation
# 
# For global structure comparison, evaluate in principal component space.

# In[7]:


# Evaluate in PC space (50 principal components)
pc_results = evaluate_pc_space(
    real_data=real_adata,
    generated_data=generated_adata,
    condition_columns=['condition'],
    n_components=50,
)

print("PC-Space Evaluation Results:")
print(pc_results.summary())


# ## Mixed-Space Evaluation (Paper API)
# 
# The `evaluate_lazy()` function allows metrics to be computed in different spaces - raw, PCA, or DEG space.
# 
# Each metric can specify its own computation space:
# - `space="raw"`: Original gene expression space (default)
# - `space="pca"`: Principal component space with `n_components` dimensions
# - `space="deg"`: Differentially expressed genes space with `deg_lfc` and `deg_pval` thresholds

# In[8]:


# Define metrics with different spaces
metrics = [
    # Correlation in raw space
    PearsonCorrelation(space="raw"),
    SpearmanCorrelation(space="raw"),
    
    # Distances in PCA space (50 components)
    Wasserstein2Distance(space="pca", n_components=50),
    MMDDistance(space="pca", n_components=50),
    
    # R-squared in DEG space
    RSquared(space="deg", deg_lfc=0.5, deg_pval=0.05),
]

# Check metric names (automatically include space suffix)
for m in metrics:
    print(f"{m.__class__.__name__}: name='{m.name}', space='{m.space}'")


# ## Summary
# 
# This notebook demonstrated:
# 
# 1. **Basic evaluation** with `evaluate()` function
# 2. **Individual metrics** (Pearson, Spearman, R-squared, MSE)
# 3. **Perturbation-effect correlation** (Paper Eq. 1)
# 4. **PC-space evaluation** for global structure
# 5. **Mixed-space API** with `evaluate_lazy()` and per-metric space configuration
# 
# For more advanced usage, see the documentation at https://andrearubbi.github.io/GGE/
