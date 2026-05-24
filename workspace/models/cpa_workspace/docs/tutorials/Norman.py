#!/usr/bin/env python
# coding: utf-8

# # Predicting single-cell response to unseen  combinatorial CRISPR perturbations

# In this tutorial, we will train and evaluate a CPA model on the [Norman 2019](https://www.google.com/search?q=norman+genetic+manifold&oq=norman+genetic+manifold&gs_lcrp=EgZjaHJvbWUyBggAEEUYOdIBCDMyMThqMGo3qAIAsAIA&sourceid=chrome&ie=UTF-8) dataset. See the last [Figure 5](https://www.embopress.org/doi/full/10.15252/msb.202211517) in the CPA paper. 
# 
# The goal is to predict gene expression response to perturbation responses of `X+Y` when you have seen single cells from `X` and `Y`. You can extend this model to predict 
# `X+Y` when either `X`, `Y`, or both are unseen. In this scenario, you need to use external embedding for your favourite gene representations (see an example [here](https://cpa-tools.readthedocs.io/en/latest/tutorials/combosciplex_Rdkit_embeddings.html#))
# 
# The following steps are going to be covered:
# 1. Setting up environment
# 2. Loading the dataset
# 3. Preprocessing the dataset
# 4. Creating a CPA model
# 5. Training the model
# 6. Latent space visualisation
# 7. Prediction evaluation across different perturbations

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


import os
os.chdir('/home/mohsen/projects/cpa/')
os.environ['CUDA_VISIBLE_DEVICES'] = '0'


# In[3]:


import cpa
import scanpy as sc


# In[4]:


sc.settings.set_figure_params(dpi=100)


# In[5]:


data_path = '/data/mohsen/scPert/scPerturb/Norman2019_normalized_hvg.h5ad'


# ## Loading dataset
# 
# The preprocessed Norman et. al 2019 dataset with `h5ad` extension used for saving/loading anndata objects is publicly available in the [Google Drive](https://drive.google.com/drive/folders/1pxT0fvXtqBBtdv1CCPVwJaMLHe9XpMHo?usp=sharing) and can be loaded using the `sc.read` function with the `backup_url` argument.

# In[6]:


try:
    adata = sc.read(data_path)
except:
    import gdown
    gdown.download('https://drive.google.com/uc?export=download&id=109G9MmL-8-uh7OSjnENeZ5vFbo62kI7j')
    data_path = 'Norman2019_normalized_hvg.h5ad'
    adata = sc.read(data_path)

adata


# Next, we just replace `adata.X` with raw counts to be able to train CPA with Negative Binomial (aka NB) loss.

# In[7]:


adata.X = adata.layers['counts'].copy()


# ## Pre-processing Dataset
# Preprocessing is the first step required for training a model. Just like scvi-tools models, you can call `cpa.CPA.setup_anndata` to preprocess your data. This function will accept the following arguments:
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

# In[8]:


cpa.CPA.setup_anndata(adata, 
                      perturbation_key='cond_harm',
                      control_group='ctrl',
                      dosage_key='dose_value',
                      categorical_covariate_keys=['cell_type'],
                      is_count_data=True,
                      deg_uns_key='rank_genes_groups_cov',
                      deg_uns_cat_key='cov_cond',
                      max_comb_len=2,
                     )


# In[9]:


model_params = {
    "n_latent": 32,
    "recon_loss": "nb",
    "doser_type": "linear",
    "n_hidden_encoder": 256,
    "n_layers_encoder": 4,
    "n_hidden_decoder": 256,
    "n_layers_decoder": 2,
    "use_batch_norm_encoder": True,
    "use_layer_norm_encoder": False,
    "use_batch_norm_decoder": False,
    "use_layer_norm_decoder": False,
    "dropout_rate_encoder": 0.2,
    "dropout_rate_decoder": 0.0,
    "variational": False,
    "seed": 8206,
}

trainer_params = {
    "n_epochs_kl_warmup": None,
    "n_epochs_adv_warmup": 50,
    "n_epochs_mixup_warmup": 10,
    "n_epochs_pretrain_ae": 10,
    "mixup_alpha": 0.1,
    "lr": 0.0001,
    "wd": 3.2170178270865573e-06,
    "adv_steps": 3,
    "reg_adv": 10.0,
    "pen_adv": 20.0,
    "adv_lr": 0.0001,
    "adv_wd": 7.051355554517135e-06,
    "n_layers_adv": 2,
    "n_hidden_adv": 128,
    "use_batch_norm_adv": True,
    "use_layer_norm_adv": False,
    "dropout_rate_adv": 0.3,
    "step_size_lr": 25,
    "do_clip_grad": False,
    "adv_loss": "cce",
    "gradient_clip_value": 5.0,
}


# Dataset split: We leave DUSP9+ETS2 and CNN1+CBL out of training dataset.

# In[12]:


import numpy as np


# In[15]:


adata.obs['split'] = np.random.choice(['train', 'valid'], size=adata.n_obs, p=[0.85, 0.15])
adata.obs.loc[adata.obs['cond_harm'].isin(['DUSP9+ETS2', 'CBL+CNN1']), 'split'] = 'ood'


# In[16]:


adata.obs['split'].value_counts()


# ## CPA Model
# 
# You can create a CPA model by creating an object from `cpa.CPA` class. The constructor of this class takes the following arguments:
# **Data related parameters:** 
# - `adata`: AnnData object containing train/valid/test data
# - `split_key`: The key in `adata.obs` that contains the split information
# - `train_split`: The value in `split_key` that corresponds to the training data
# - `valid_split`: The value in `split_key` that corresponds to the validation data
# - `test_split`: The value in `split_key` that corresponds to the test data
# **Model architecture parameters:**
# - `n_latent`: Number of latent dimensions
# - `recon_loss`: Reconstruction loss function. Currently, Supported losses are `nb`, `zinb`, and `gauss`.
# - `n_hidden_encoder`: Number of hidden units in the encoder
# - `n_layers_encoder`: Number of layers in the encoder
# - `n_hidden_decoder`: Number of hidden units in the decoder
# - `n_layers_decoder`: Number of layers in the decoder
# - `use_batch_norm_encoder`: Whether to use batch normalization in the encoder
# - `use_layer_norm_encoder`: Whether to use layer normalization in the encoder
# - `use_batch_norm_decoder`: Whether to use batch normalization in the decoder
# - `use_layer_norm_decoder`: Whether to use layer normalization in the decoder
# - `dropout_rate_encoder`: Dropout rate in the encoder
# - `dropout_rate_decoder`: Dropout rate in the decoder
# - `variational`: Whether to use variational inference. NOTE: False is highly recommended.
# - `seed`: Random seed

# In[17]:


model = cpa.CPA(adata=adata, 
                split_key='split',
                train_split='train',
                valid_split='valid',
                test_split='ood',
                **model_params,
               )


# ## Training CPA
# 
# In order to train your CPA model, you need to use `train` function of your `model`. This function accepts the following parameters:
# - `max_epochs`: Maximum number of epochs to train the model. CPA generally converges after high number of epochs, so you can set this to a high value.
# - `use_gpu`: If you have a GPU, you can set this to `True` to speed up the training process.
# - `batch_size`: Batch size for training. You can set this to a high value (e.g. 512, 1024, 2048) if you have a GPU. 
# - `plan_kwargs`: dictionary of parameters passed the CPA's `TrainingPlan`. You can set the following parameters:
#     * `n_epochs_adv_warmup`: Number of epochs to linearly increase the weight of adversarial loss. 
#     * `n_epochs_mixup_warmup`: Number of epochs to linearly increase the weight of mixup loss.
#     * `n_epochs_pretrain_ae`: Number of epochs to pretrain the autoencoder.
#     * `lr`: Learning rate for training autoencoder.
#     * `wd`: Weight decay for training autoencoder.
#     * `adv_lr`: Learning rate for training adversary.
#     * `adv_wd`: Weight decay for training adversary.
#     * `adv_steps`: Number of steps to train adversary for each step of autoencoder.
#     * `reg_adv`: Maximum Weight of adversarial loss.
#     * `pen_adv`: Penalty weight of adversarial loss.
#     * `n_layers_adv`: Number of layers in adversary.
#     * `n_hidden_adv`: Number of hidden units in adversary.
#     * `use_batch_norm_adv`: Whether to use batch normalization in adversary.
#     * `use_layer_norm_adv`: Whether to use layer normalization in adversary.
#     * `dropout_rate_adv`: Dropout rate in adversary.
#     * `step_size_lr`: Step size for learning rate scheduler.
#     * `do_clip_grad`: Whether to clip gradients by norm.
#     * `clip_grad_value`: Maximum value of gradient norm.
#     * `adv_loss`: Type of adversarial loss. Can be either `cce` for Cross Entropy loss or `focal` for Focal loss.
#     * `n_epochs_verbose`: Number of epochs to print latent information disentanglement evaluation.
# - `early_stopping_patience`: Number of epochs to wait before stopping training if validation metric does not improve.
# - `check_val_every_n_epoch`: Number of epochs to wait before running validation.
# - `save_path`: Path to save the best model after training.
# 
# 

# In[18]:


model.train(max_epochs=2000,
            use_gpu=True, 
            batch_size=2048,
            plan_kwargs=trainer_params,
            early_stopping_patience=5,
            check_val_every_n_epoch=5,
            save_path='/home/mohsen/projects/cpa/lightning_logs/Norman2019/',
           )


# In[19]:


cpa.pl.plot_history(model)


# ## Restore best model
# 
# In case you have already saved your pretrained model, you can restore it using the following code. The `cpa.CPA.load` function accepts the following arguments:
# - `dir_path`: path to the directory where the model is saved
# - `adata`: anndata object
# - `use_gpu`: whether to use GPU or not
# 

# In[20]:


# model = cpa.CPA.load(dir_path='/home/mohsen/projects/cpa/lightning_logs/Norman2019/',
#                      adata=adata,
#                      use_gpu=True)


# ## Latent Space Visualization
# 
# latent vectors of all cells can be computed with `get_latent_representation` function. This function produces a python dictionary with the following keys:
# - `latent_basal`: latent vectors of all cells in basal state of autoencoder
# - `latent_after`: final latent vectors which can be used for decoding
# - `latent_corrected`: batch-corrected latents if batch_key was provided

# In[21]:


latent_outputs = model.get_latent_representation(adata, batch_size=2048)


# In[22]:


latent_outputs.keys()


# In[23]:


sc.pp.neighbors(latent_outputs['latent_basal'])
sc.tl.umap(latent_outputs['latent_basal'])


# In[43]:


groups = list(np.unique(adata[adata.obs['split'] == 'ood'].obs['cond_harm'].values))
len(groups)


# As observed below, the basal representation should be free of the variation(s) of the `cond_harm`

# In[44]:


sc.pl.umap(latent_outputs['latent_basal'], 
           color='cond_harm', 
           groups=groups,
           palette=sc.pl.palettes.godsnot_102,
           frameon=False)


# We can further color them by the gene programs that each perturbation will induce

# In[26]:


sc.pl.umap(latent_outputs['latent_basal'], 
           color='pathway', 
           palette=sc.pl.palettes.godsnot_102,
           frameon=False)


# In[27]:


sc.pp.neighbors(latent_outputs['latent_after'])
sc.tl.umap(latent_outputs['latent_after'])


# Here, you can visualise that when gene embeddings are added to the basal representation, the cells treated with different drugs will be separated.

# In[45]:


sc.pl.umap(latent_outputs['latent_after'], 
           color='cond_harm', 
           groups=groups,
           palette=sc.pl.palettes.godsnot_102,
           frameon=False)


# In[29]:


sc.pl.umap(latent_outputs['latent_after'], 
           color='pathway', 
           palette=sc.pl.palettes.godsnot_102,
           frameon=False)


# ## Evaluation 

# To evaluate the model's prediction performance, we can use `model.predict()` function. $R^2$ score for each genetic interaction (GI) is computed over mean statistics of the top 50, 20, and 10 DEGs (including all genes). CPA transfers the context from control to GI-perturbed for K562 cells. Next, we will evaluate the model's prediction performance on the whole dataset, including OOD (test) cells. The model will report metrics on how well we have
# captured the variation in top `n` differentially expressed genes when compared to control cells
# (`CTRL`)  for each condition. The metrics calculate the mean accuracy (`r2_mean_deg`) and mean log-fold-change accuracy (`r2_mean_lfc_deg`).  The `R2` is the `sklearn.metrics.r2_score` from [sklearn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.r2_score.html).

# NOTE: To perform counter-factual prediction, we first need to set `adata.X` to sampled control cells. Then, we can use `model.predict()` function to predict the effect of perturbations on these cells. 

# In[31]:


adata.layers['X_true'] = adata.X.copy()


# In[32]:


ctrl_adata = adata[adata.obs['cond_harm'] == 'ctrl'].copy()

adata.X = ctrl_adata.X[np.random.choice(ctrl_adata.n_obs, size=adata.n_obs, replace=True), :]


# In[33]:


model.predict(adata, batch_size=2048)


# In[35]:


adata.layers['CPA_pred'] = adata.obsm['CPA_pred'].copy()


# In[36]:


sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)

sc.pp.normalize_total(adata, target_sum=1e4, layer='CPA_pred')
sc.pp.log1p(adata, layer='CPA_pred')


# In[37]:


adata.X.max(), adata.layers['CPA_pred'].max()


# In[53]:


import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from collections import defaultdict
from tqdm import tqdm

n_top_degs = [10, 20, 50, None] # None means all genes

results = defaultdict(list)
ctrl_adata = adata[adata.obs['cond_harm'] == 'ctrl'].copy()
for condition in tqdm(adata.obs['cond_harm'].unique()):
    if condition != 'ctrl':
        cond_adata = adata[adata.obs['cond_harm'] == condition].copy()

        deg_cat = f'K562_{condition}'
        deg_list = adata.uns['rank_genes_groups_cov'][deg_cat]
        
        x_true = cond_adata.layers['counts'].toarray()
        x_pred = cond_adata.obsm['CPA_pred']
        x_ctrl = ctrl_adata.layers['counts'].toarray()

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

            r2_mean_lfc_deg = r2_score(x_true_deg.mean(0) - x_ctrl_deg.mean(0), x_pred_deg.mean(0) - x_ctrl_deg.mean(0))
            
            results['condition'].append(condition)
            results['n_top_deg'].append(n_top_deg)
            results['r2_mean_deg'].append(r2_mean_deg)
            results['r2_mean_lfc_deg'].append(r2_mean_lfc_deg)

df = pd.DataFrame(results)


# In[54]:


df[df['condition'].isin(['DUSP9+ETS2', 'CBL+CNN1'])]

