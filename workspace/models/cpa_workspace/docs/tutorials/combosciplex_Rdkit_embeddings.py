#!/usr/bin/env python
# coding: utf-8

# # Predicting combinatorial drug perturbations using RDKit embeddings for drugs

# While CPA can predict unseen combinations using its default setting, it can not predict completely unseen perturbations. We have extended CPA to work with external perturbation embeddings ([chemCPA](https://arxiv.org/abs/2204.13545). Ultimately, these embeddings should capture the similarities and differences between perturbations. They can be obtained from any resources (e.g., generative models encoding drugs or Chemo-physical properties of molecules). Here, we showcase how to leverage an external embedding from [RDKit](https://www.rdkit.org/docs/GettingStartedInPython.html), which returns a vector representing the Chemo-physical features of molecules. This will allow us to predict perturbation completely absent in the training data, conditional on similar molecules in training data; otherwise, predictions will not be reliable. Here, we train CPA on the Combo Sci-Plex data as we did [here](https://cpa-tools.readthedocs.io/en/latest/tutorials/combosciplex.html) using RDKit embeddings extracted with RDKit python package. The model's performance was finally evaluated on the same held-out drugs (OOD drugs) as the previous tutorial. The rationale is the same if you would like to include other perturbation embedding as shown in the chemCPA paper.

# In[1]:


import sys
#if branch is stable, will install via pypi, else will install from source
branch = "latest"
IN_COLAB = "google.colab" in sys.modules

if IN_COLAB and branch == "stable":
    get_ipython().system('pip install cpa-tools')
    get_ipython().system('pip install scanpy')
elif IN_COLAB and branch != "stable":
    get_ipython().system('pip install --quiet --upgrade jsonschema')
    get_ipython().system('pip install git+https://github.com/theislab/cpa')
    get_ipython().system('pip install scanpy')


# In[2]:


from sklearn.metrics import r2_score
import numpy as np

import os
# os.chdir('/home/mohsen/projects/cpa/') # For local run
# os.environ['CUDA_VISIBLE_DEVICES'] = '0' # For dedicated GPU usage


# Import CPA package

# In[3]:


import cpa
import scanpy as sc


# In[4]:


sc.settings.set_figure_params(dpi=100)


# In[5]:


data_path = '/home/mohsen/projects/cpa/datasets/combo_sciplex_prep_hvg_filtered.h5ad'


# ## Data Loading

# Combo sciplex dataset can be loaded using scanpy's read function. The dataset is already preprocessed and stored in the data folder. The following columns in `adata.obs` are required for training the model:
# 
# - `condition_ID`: Single/Combinatorial CHEMBL IDs of the drugs applied to the cells
# - `log_dose`: Log-transformed dosages of the drugs applied to the cells
# - `cell_type`: Cell types of the cells (All A549 in this case)
# - `smiles_rkdit`: Canonical SMILES representation of the drugs separated by ".." for combinatorial perturbations
# - `cov_drug_dose`: Covariates+Drug+Dosage information of the drugs applied to the cells (used for accessing top DEGs from adata.uns['rank_genes_groups_cov'])
# - `split_1ct_MEC`: Train/valid/ood split information of the cells

# In[6]:


try:
    adata = sc.read(data_path)
except:
    import gdown
    gdown.download('https://drive.google.com/uc?export=download&id=1RRV0_qYKGTvD3oCklKfoZQFYqKJy4l6t')
    data_path = 'combo_sciplex_prep_hvg_filtered.h5ad'
    adata = sc.read(data_path)

adata


# ## Data preparation

# __IMPORTANT__: Currenlty because of the standartized evaluation procedure, we need to provide adata.obs['control'] (0 if not control, 1 for cells to use as control). And we also need to provide de_genes in .uns['rank_genes_groups']. 

# In[7]:


adata.obs['split_1ct_MEC'].value_counts()


# In the following, we will extract OOD drugs and visualize cells perturbed by them.

# In[10]:


ood_conds = list(adata[adata.obs['split_1ct_MEC'] == 'ood'].obs['condition_ID'].value_counts().index)
ood_conds


# In[11]:


adata.obs['condition_split'] = adata.obs['condition_ID'].apply(lambda x: x if x in ood_conds else 'other')


# In[12]:


sc.settings.verbosity = 3


# In[13]:


sc.pp.neighbors(adata)
sc.tl.umap(adata)


# In[15]:


sc.settings.set_figure_params(dpi=100)


# In[24]:


sc.pl.umap(adata, 
           color='condition_split', 
           groups=ood_conds, 
           palette=sc.pl.palettes.godsnot_102,
           na_in_legend=False,
           na_color='grey',
           frameon=False)


# In[25]:


adata.X = adata.layers['counts'].copy()


# ## Data setup
# Data setup is the first step required for training CPA. Just like scvi-tools models, you can call `cpa.CPA.setup_anndata` to preprocess your data. This function will accept the following arguments:
# 
# - `adata`: AnnData object containing the data to be preprocessed
# - `perturbation_key`: The key in `adata.obs` that contains the perturbation information
# - `control_group`: The name of the control group in `perturbation_key`
# - `batch_key`: The key in `adata.obs` that contains the batch information
# - `dosage_key`: The key in `adata.obs` that contains the dosage information
# - `categorical_covariate_keys`: A list of keys in `adata.obs` that contain categorical covariates
# - `is_count_data`: Whether the `adata.X` is count data or not
# - `deg_uns_key`: The key in `adata.uns` that contains the differential expression results
# - `deg_uns_cat_key`: The key in `adata.obs` that contains the category information of each cell which can be used as to access differential expression results in `adata.uns[deg_uns_key]`. For example, if `deg_uns_key` is `rank_genes_groups_cov` and `deg_uns_cat_key` is `cov_cond`, then `adata.uns[deg_uns_key][cov_cond]` will contain the differential expression results for each category in `cov_cond`.
# - `max_comb_len`: The maximum number of perturbations that are applied to each cell. For example, if `max_comb_len` is 2, then the model will be trained to predict the effect of single perturbations and the effect of double perturbations.

# In[9]:


cpa.CPA.setup_anndata(adata, 
                      perturbation_key='condition_ID',
                      dosage_key='log_dose',
                      control_group='CHEMBL504',
                      batch_key=None,
                      smiles_key='smiles_rdkit',
                      is_count_data=True,
                      categorical_covariate_keys=['cell_type'],
                      deg_uns_key='rank_genes_groups_cov',
                      deg_uns_cat_key='cov_drug_dose',
                      max_comb_len=2,
                     )


# ## Training CPA

# You can specify all the parameters for the model in a dictionary of parameters. If they are not specified, default values will be selected.
# 
# * `ae_hparams` are technical parameters of the architecture of the autoencoder.
#     * `n_latent`: number of latent dimensions for the autoencoder
#     * `recon_loss`: the type of reconstruction loss function to use
#     * `doser_type`: the type of doser to use
#     * `n_hidden_encoder`: number of hidden neurons in each hidden layer of the encoder
#     * `n_layers_encoder`: number of hidden layers in the encoder
#     * `n_hidden_decoder`: number of hidden neurons in each hidden layer of the decoder
#     * `n_layers_decoder`: number of hidden layers in the decoder
#     * `use_batch_norm_encoder`: if `True`, batch normalization will be used in the encoder
#     * `use_layer_norm_encoder`: if `True`, layer normalization will be used in the encoder
#     * `use_batch_norm_decoder`: if `True`, batch normalization will be used in the decoder
#     * `use_layer_norm_decoder`: if `True`, layer normalization will be used in the decoder
#     * `dropout_rate_encoder`: dropout rate used in the encoder
#     * `dropout_rate_decoder`: dropout rate used in the decoder
#     * `variational`: if `True`, variational autoencoder will be employed as the main perturbation response predictor
#     * `seed`: number for setting the seed for generating random numbers.
# * `trainer_params` are training parameters of CPA.
#     * `n_epochs_adv_warmup`: number of epochs for adversarial warmup
#     * `n_epochs_kl_warmup`: number of epochs for KL divergence warmup
#     * `n_epochs_pretrain_ae`: number of epochs to pre-train the autoencoder
#     * `adv_steps`: number of steps used to train adversarial classifiers after a single step of training the autoencoder
#     * `mixup_alpha`: mixup interpolation coefficient
#     * `n_epochs_mixup_warmup`: number of epochs for mixup warmup
#     * `lr`: learning rate of the trainer
#     * `wd`: weight decay of the trainer
#     * `doser_lr`: learning rate of doser parameters
#     * `doser_wd`: weight decay of doser parameters
#     * `adv_lr`: learning rate of adversarial classifiers
#     * `adv_wd`: weight decay rate of adversarial classifiers
#     * `pen_adv`: penalty for adversarial classifiers
#     * `reg_adv`: regularization for adversarial classifiers
#     * `n_layers_adv`: number of hidden layers in adversarial classifiers
#     * `n_hidden_adv`: number of hidden neurons in each hidden layer of adversarial classifiers
#     * `use_batch_norm_adv`: if `True`, batch normalization will be used in the adversarial classifiers
#     * `use_layer_norm_adv`: if `True`, layer normalization will be used in the adversarial classifiers
#     * `dropout_rate_adv`: dropout rate used in the adversarial classifiers
#     * `step_size_lr`: learning rate step size
#     * `do_clip_grad`: if `True`, gradient clipping will be used
#     * `adv_loss`: the type of loss function to use for adversarial training
#     * `gradient_clip_value`: value to clip gradients to, if `do_clip_grad` is `True`

# In[10]:


ae_hparams = {'n_latent': 64,
 'recon_loss': 'nb',
 'doser_type': 'linear',
 'n_hidden_encoder': 256,
 'n_layers_encoder': 3,
 'n_hidden_decoder': 512,
 'n_layers_decoder': 2,
 'use_batch_norm_encoder': True,
 'use_layer_norm_encoder': False,
 'use_batch_norm_decoder': True,
 'use_layer_norm_decoder': False,
 'dropout_rate_encoder': 0.25,
 'dropout_rate_decoder': 0.25,
 'variational': False,
 'seed': 6478}

trainer_params = {'n_epochs_kl_warmup': None,
 'n_epochs_pretrain_ae': 50,
 'n_epochs_adv_warmup': 100,
 'n_epochs_mixup_warmup': 10,
 'mixup_alpha': 0.1,
 'adv_steps': None,
 'n_hidden_adv': 128,
 'n_layers_adv': 3,
 'use_batch_norm_adv': False,
 'use_layer_norm_adv': False,
 'dropout_rate_adv': 0.2,
 'reg_adv': 10.0,
 'pen_adv': 0.1,
 'lr': 0.0003,
 'wd': 4e-07,
 'adv_lr': 0.0003,
 'adv_wd': 4e-07,
 'adv_loss': 'cce',
 'doser_lr': 0.0003,
 'doser_wd': 4e-07,
 'do_clip_grad': False,
 'gradient_clip_value': 1.0,
 'step_size_lr': 10}


# ## Model instantiation

# __NOTE__: Run the following 3 cells if you haven't already trained CPA from scratch.
# 
# Here, we create a CPA model using `cpa.CPA` given all hyper-parameters.

# In[11]:


adata.obs['split_1ct_MEC'].value_counts()


# In[12]:


model = cpa.CPA(adata=adata, 
                split_key='split_1ct_MEC',
                train_split='train',
                valid_split='valid',
                test_split='ood',
                use_rdkit_embeddings=True,
                **ae_hparams,
               )


# ## Training CPA

# After creating a CPA object, we train the model with the following arguments:
# * `max_epochs`: Maximum number of epochs to train the models.
# * `use_gpu`: If `True`, will use the available GPU to train the model.
# * `batch_size`: Number of samples to use in each mini-batches.
# * `early_stopping_patience`: Number of epochs with no improvement in early stopping callback.
# * `check_val_every_n_epoch`: Interval of checking validation losses.
# * `save_path`: Path to save the model after the training has finished.

# In[13]:


model.train(max_epochs=2000,
            use_gpu=True, 
            batch_size=512,
            plan_kwargs=trainer_params,
            early_stopping_patience=10,
            check_val_every_n_epoch=5,
            save_path='/home/mohsen/projects/cpa/lightning_logs/combo_rdkit/',
           )


# In[14]:


cpa.pl.plot_history(model)


# If you already trained CPA, you can restore model weights by running the following cell:

# In[15]:


# model = cpa.CPA.load(dir_path='/home/mohsen/projects/cpa/lightning_logs/combo_rdkit/', 
#                      adata=adata, use_gpu=True)


# ## Latent space UMAP visualization

# Here, we visualize the latent representations of all cells. We computed basal and final latent representations with `model.get_latent_representation` function. The function will return a python dictionary as output with the following keys:
# 
# - `latent_basal`: Basal latent representation of the cells (before perturbation) as anndata object
# - `latent_after`: Final latent representation of the cells (after perturbation) as anndata object
# - `latent_corrected`: Batch-corrected (if `batch_key` was provided when calling `setup_anndata`) latent representation of the cells (after perturbation) as anndata object

# In[16]:


latent_outputs = model.get_latent_representation(adata, batch_size=1024)


# In[17]:


sc.settings.verbosity = 3


# In[18]:


latent_basal_adata = latent_outputs['latent_basal']
latent_adata = latent_outputs['latent_after']


# In[19]:


sc.pp.neighbors(latent_basal_adata)
sc.tl.umap(latent_basal_adata)


# In[20]:


latent_basal_adata


# ### Basal Latent

# The basal representation should be free of the variation(s) of the `'condition_ID' as observed below 

# In[21]:


sc.pl.umap(latent_basal_adata, color=['condition_ID'], frameon=False, wspace=0.2)


# In[22]:


sc.pp.neighbors(latent_adata)
sc.tl.umap(latent_adata)


# ### Final Latent

# Here, you can visualize that when the drug embedding is added to the basal representation, the cells treated with different drugs will be separated from each other.

# In[23]:


sc.pl.umap(latent_adata, color=['condition_ID'], frameon=False, wspace=0.2)


# ### Evaluation 

# Next, we will evaluate the model's prediction performance on the whole dataset, including OOD (test) cells. The model will report metrics on how well we have
# captured the variation in top `n` differentially expressed genes when compared to control cells
# (DMSO, [CHEMBL 504](https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL504/))  for each condition. The metrics calculate the mean accuracy (`r2_mean_deg`), the variance (`r2_var_deg`) and similar metrics (`r2_mean_lfc_deg` and `log fold change`)to measure the log fold change of the predicted cells vs control`((LFC(control, ground truth) ~ LFC(control, predicted cells))`.  The `R2` is the `sklearn.metrics.r2_score` from [sklearn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.r2_score.html).

# In[ ]:


model.predict(adata, batch_size=1024)


# In[25]:


import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from collections import defaultdict
from tqdm import tqdm

n_top_degs = [10, 20, 50, None] # None means all genes

results = defaultdict(list)
ctrl_adata = adata[adata.obs['condition_ID'] == 'CHEMBL504'].copy()
for cat in tqdm(adata.obs['cov_drug_dose'].unique()):
    if 'CHEMBL504' not in cat:
        cat_adata = adata[adata.obs['cov_drug_dose'] == cat].copy()

        deg_cat = f'{cat}'
        deg_list = adata.uns['rank_genes_groups_cov'][deg_cat]
        
        x_true = cat_adata.layers['counts'].toarray()
        x_pred = cat_adata.obsm['CPA_pred']
        x_ctrl = ctrl_adata.layers['counts'].toarray()

        x_true = np.log1p(x_true)
        x_pred = np.log1p(x_pred)
        x_ctrl = np.log1p(x_ctrl)

        for n_top_deg in n_top_degs:
            if n_top_deg is not None:
                degs = np.where(np.isin(adata.var_names, deg_list[:n_top_deg]))[0]
            else:
                degs = np.arange(adata.n_vars)
                n_top_deg = 'all'
                
            x_true_deg = x_true[:, degs]
            x_pred_deg = x_pred[:, degs]
            x_ctrl_deg = x_ctrl[:, degs]
            
            r2_mean_deg = r2_score(x_true_deg.mean(0), x_pred_deg.mean(0))
            r2_var_deg = r2_score(x_true_deg.var(0), x_pred_deg.var(0))

            r2_mean_lfc_deg = r2_score(x_true_deg.mean(0) - x_ctrl_deg.mean(0), x_pred_deg.mean(0) - x_ctrl_deg.mean(0))
            r2_var_lfc_deg = r2_score(x_true_deg.var(0) - x_ctrl_deg.var(0), x_pred_deg.var(0) - x_ctrl_deg.var(0))

            cov, cond, dose = cat.split('_')
            
            results['cell_type'].append(cov)
            results['condition'].append(cond)
            results['dose'].append(dose)
            results['n_top_deg'].append(n_top_deg)
            results['r2_mean_deg'].append(r2_mean_deg)
            results['r2_var_deg'].append(r2_var_deg)
            results['r2_mean_lfc_deg'].append(r2_mean_lfc_deg)
            results['r2_var_lfc_deg'].append(r2_var_lfc_deg)

df = pd.DataFrame(results)


# `n_top_deg` shows how many DEGs genes were used to calculate the metric. 

# In[26]:


df[df['n_top_deg'] == 20]


# We can further visualize these per condition

# In[27]:


for cat in adata.obs["cov_drug_dose"].unique():
    if "CHEMBL504" not in cat:
        cat_adata = adata[adata.obs["cov_drug_dose"] == cat].copy()

        cat_adata.X = np.log1p(cat_adata.layers["counts"].A)
        cat_adata.obsm["CPA_pred"] = np.log1p(cat_adata.obsm["CPA_pred"])

        deg_list = adata.uns["rank_genes_groups_cov"][f'{cat}'][:20]

        print(cat, f"{cat_adata.shape}")
        cpa.pl.mean_plot(
            cat_adata,
            pred_obsm_key="CPA_pred",
            path_to_save=None,
            deg_list=deg_list,
            # gene_list=deg_list[:5],
            show=True,
            verbose=True,
        )


# ## Visualizing similarity between drug embeddings

# CPA learns an embedding for each covariate, and those can visualised to compare the similarity between perturbation (i.e. which perturbation have similar gene expression responses) 

# In[28]:


cpa_api = cpa.ComPertAPI(adata, model, 
                         de_genes_uns_key='rank_genes_groups_cov', 
                         pert_category_key='cov_drug_dose',
                         control_group='CHEMBL504',
                         )


# In[29]:


cpa_plots = cpa.pl.CompertVisuals(cpa_api, fileprefix=None)


# In[30]:


cpa_api.num_measured_points['train']


# In[31]:


drug_adata = cpa_api.get_pert_embeddings()
drug_adata.shape


# In[32]:


cpa_plots.plot_latent_embeddings(drug_adata.X, kind='perturbations', titlename='Drugs')

