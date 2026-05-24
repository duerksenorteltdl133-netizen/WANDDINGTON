#!/usr/bin/env python
# coding: utf-8

# ## Predicting combinatorial drug perturbations

# In this tutorial, we train CPA on combo-sciplex dataset. This dataset is available [here](https://drive.google.com/uc?export=download&id=1RRV0_qYKGTvD3oCklKfoZQFYqKJy4l6t). See [lotfollahi et al.](https://www.embopress.org/doi/full/10.15252/msb.202211517) for more info
# (also [see](https://cpa-tools.readthedocs.io/en/latest/tutorials/combosciplex_Rdkit_embeddings.html) how you can use external drug embedding to improve your prediction and predict unseen drugs). See [Fig.3](https://www.embopress.org/doi/full/10.15252/msb.202211517) in the paper for more analysis. 

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
# os.chdir('/home/mohsen/projects/cpa/')
# os.environ['CUDA_VISIBLE_DEVICES'] = '0'


# In[3]:


import cpa
import scanpy as sc


# In[4]:


sc.settings.set_figure_params(dpi=100)


# In[5]:


data_path = '/home/mohsen/projects/cpa/datasets/combo_sciplex_prep_hvg_filtered.h5ad'


# ## Data Loading

# In[6]:


try:
    adata = sc.read(data_path)
except:
    import gdown
    gdown.download('https://drive.google.com/uc?export=download&id=1RRV0_qYKGTvD3oCklKfoZQFYqKJy4l6t')
    data_path = 'combo_sciplex_prep_hvg_filtered.h5ad'
    adata = sc.read(data_path)

adata


# ## Data setup

# __IMPORTANT__: Currenlty because of the standartized evaluation procedure, we need to provide adata.obs['control'] (0 if not control, 1 for cells to use as control). And we also need to provide de_genes in .uns['rank_genes_groups']. 

# In order to effectively assess the performance of the model, we have left out all cells perturbed by the following single/combinatorial perturbations. These cells are also used in the original paper for evaluation of CPA (See Figure 3 in the paper).
# 
# * CHEMBL1213492+CHEMBL491473
# * CHEMBL483254+CHEMBL4297436
# * CHEMBL356066+CHEMBL402548
# * CHEMBL483254+CHEMBL383824
# * CHEMBL4297436+CHEMBL383824

# In[7]:


adata.obs['split_1ct_MEC'].value_counts()


# In[8]:


adata.X = adata.layers['counts'].copy()


# In[9]:


cpa.CPA.setup_anndata(adata, 
                      perturbation_key='condition_ID',
                      dosage_key='log_dose',
                      control_group='CHEMBL504',
                      batch_key=None,
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

# In[9]:


ae_hparams = {
    "n_latent": 128,
    "recon_loss": "nb",
    "doser_type": "logsigm",
    "n_hidden_encoder": 512,
    "n_layers_encoder": 3,
    "n_hidden_decoder": 512,
    "n_layers_decoder": 3,
    "use_batch_norm_encoder": True,
    "use_layer_norm_encoder": False,
    "use_batch_norm_decoder": True,
    "use_layer_norm_decoder": False,
    "dropout_rate_encoder": 0.1,
    "dropout_rate_decoder": 0.1,
    "variational": False,
    "seed": 434,
}

trainer_params = {
    "n_epochs_kl_warmup": None,
    "n_epochs_pretrain_ae": 30,
    "n_epochs_adv_warmup": 50,
    "n_epochs_mixup_warmup": 3,
    "mixup_alpha": 0.1,
    "adv_steps": 2,
    "n_hidden_adv": 64,
    "n_layers_adv": 2,
    "use_batch_norm_adv": True,
    "use_layer_norm_adv": False,
    "dropout_rate_adv": 0.3,
    "reg_adv": 20.0,
    "pen_adv": 20.0,
    "lr": 0.0003,
    "wd": 4e-07,
    "adv_lr": 0.0003,
    "adv_wd": 4e-07,
    "adv_loss": "cce",
    "doser_lr": 0.0003,
    "doser_wd": 4e-07,
    "do_clip_grad": False,
    "gradient_clip_value": 1.0,
    "step_size_lr": 45,
}


# ## Model instantiation

# __NOTE__: Run the following 3 cells if you haven't already trained CPA from scratch.
# 
# Here, we create a CPA model using `cpa.CPA` given all hyper-parameters.

# In[10]:


adata.obs['split_1ct_MEC'].value_counts()


# In[11]:


model = cpa.CPA(adata=adata, 
                split_key='split_1ct_MEC',
                train_split='train',
                valid_split='valid',
                test_split='ood',
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

# In[12]:


model.train(max_epochs=2000,
            use_gpu=True, 
            batch_size=128,
            plan_kwargs=trainer_params,
            early_stopping_patience=10,
            check_val_every_n_epoch=5,
            save_path='/home/mohsen/projects/cpa/lightning_logs/combo/',
           )


# In[13]:


cpa.pl.plot_history(model)


# If you already trained CPA, you can restore model weights by running the following cell:

# In[9]:


model = cpa.CPA.load(dir_path='/home/mohsen/projects/cpa/lightning_logs/combo/', 
                     adata=adata, use_gpu=True)


# ## Latent space UMAP visualization

# Here, we visualize the latent representations of all cells. We computed basal and final latent representations with `model.get_latent_representation` function. 

# In[10]:


latent_outputs = model.get_latent_representation(adata, batch_size=1024)


# In[13]:


sc.settings.verbosity = 3


# In[11]:


latent_basal_adata = latent_outputs['latent_basal']
latent_adata = latent_outputs['latent_after']


# In[12]:


sc.pp.neighbors(latent_basal_adata)
sc.tl.umap(latent_basal_adata)


# In[13]:


latent_basal_adata


# The basal representation should be free of the variation(s) of the `'condition_ID' as observed below 

# In[14]:


sc.pl.umap(latent_basal_adata, color=['condition_ID'], frameon=False, wspace=0.2)


# Here, you can visualize that when the drug embedding is added to the basal representation, the cells treated with different drugs will be separated.

# In[15]:


sc.pp.neighbors(latent_adata)
sc.tl.umap(latent_adata)


# In[16]:


sc.pl.umap(latent_adata, color=['condition_ID'], frameon=False, wspace=0.2)


# ## Evaluation 

# Next, we will evaluate the model's prediction performance on the whole dataset, including OOD (test) cells. The model will report metrics on how well we have
# captured the variation in top `n` differentially expressed genes when compared to control cells
# (DMSO, [CHEMBL 504](https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL504/))  for each condition. The metrics calculate the mean accuracy (`r2_mean_deg`), the variance (`r2_var_deg`) and similar metrics (`r2_mean_lfc_deg` and `log fold change`)to measure the log fold change of the predicted cells vs control`((LFC(control, ground truth) ~ LFC(control, predicted cells))`.  The `R2` is the `sklearn.metrics.r2_score` from [sklearn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.r2_score.html).

# In[20]:


model.predict(adata, batch_size=1024)


# In[21]:


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


# In[22]:


df[df['n_top_deg'] == 20]


# `n_top_deg` shows how many DEGs genes were used to calculate the metric. 

# We can further visualize these per condition

# In[21]:


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

# In[15]:


cpa_api = cpa.ComPertAPI(adata, model, 
                         de_genes_uns_key='rank_genes_groups_cov', 
                         pert_category_key='cov_drug_dose',
                         control_group='CHEMBL504',
                         )


# In[18]:


cpa_plots = cpa.pl.CompertVisuals(cpa_api, fileprefix=None)


# In[16]:


cpa_api.num_measured_points['train']


# In[17]:


drug_adata = cpa_api.get_pert_embeddings()
drug_adata.shape


# In[19]:


cpa_plots.plot_latent_embeddings(drug_adata.X, kind='perturbations', titlename='Drugs')

