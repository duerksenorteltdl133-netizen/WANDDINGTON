#!/usr/bin/env python
# coding: utf-8

# # Batch correction in expression space

# In this tutorial, we will train and evaluate a CPA model on the
# Immune_ALL_human.h5ad dataset from [scib](https://github.com/theislab/scib) to perform batch correction, in gene expression space.
# 
# The following steps are going to be covered:
# 1. Setting up environment
# 2. Loading the dataset
# 3. Preprocessing the dataset
# 4. Creating a CPA model
# 5. Training the model
# 6. Latent space visualisation
# 7. Reconstructed gene expression space visualisation

# In[ ]:


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


# In[ ]:


get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')


# In[ ]:


import os
# os.chdir('/home/mohsen/projects/cpa/')
# os.environ['CUDA_VISIBLE_DEVICES'] = '0'


# In[ ]:


import cpa
import scanpy as sc
import gdown
from anndata import AnnData


# In[ ]:


sc.settings.set_figure_params(dpi=100)


# ## Loading dataset
# 
# This dataset with `h5ad` extension used for saving/loading anndata objects is publicly available in the [Google Drive](https://drive.google.com/uc?id=1Vh6RpYkusbGIZQC8GMFe3OKVDk5PWEpC) and can be downloaded using `gdown` and then loaded using the `sc.read` function.

# In[ ]:


url = 'https://drive.google.com/uc?id=1Vh6RpYkusbGIZQC8GMFe3OKVDk5PWEpC'
output = 'pbmc.h5ad'
gdown.download(url, output, quiet=False)


# In[ ]:


adata = sc.read('pbmc.h5ad')


# We are removing the `Villani` batch of the dataset since we want to work with the count data and this batch does not contain the counts.

# In[ ]:


adata = adata[~(adata.obs['batch'] == 'Villani')]


# In[ ]:


adata


# In[ ]:


adata.obs['batch'].value_counts()


# In[ ]:


adata.obs['final_annotation'].value_counts()


# ## Normalization & HVG selection
# We normalize the dataset and select the top 5000 highly variable genes from all the 12303 genes in the dataset.

# In[ ]:


sc.pp.normalize_total(adata)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(
    adata,
    n_top_genes=5000,
    batch_key="batch",
    subset=True)


# In[ ]:


adata


# In[ ]:


adata.obs


# In[ ]:


sc.pp.neighbors(adata)
sc.tl.umap(adata)

sc.pl.umap(adata,
           color=['batch', 'final_annotation'],
           frameon=False,
           wspace=0.5)


# ## Cell type annotation
# We create a new column in `adata.obs` and copy the `final_annotation` column there, removing the `+` characters in the names. (`+` is used for processing combinatorial perturbations in CPA)

# In[ ]:


adata.obs['cell_type'] = 'NaN'
for cell_type in adata.obs['final_annotation'].unique():
    adata.obs.loc[adata.obs['final_annotation'] == cell_type, 'cell_type'] = cell_type.replace('+', '')


# In[ ]:


adata.obs.head()


# Next, we just replace `adata.X` with raw counts to be able to train CPA with Negative Binomial (NB) or Zero-Inflated Negative Binomial (ZINB) loss.

# In[ ]:


adata.X = adata.layers["counts"].copy()


# ## Dataset setup
# Now is the time to setup the dataset for CPA to prepare the dataset for training. Just like scvi-tools models, you can call `cpa.CPA.setup_anndata` to setup your data. Although, we will use the `setup_anndata` arguments a bit different than our previous tutorials, since we arent' dealing with a perturbation dataset here. We are dealing with batch effect of different sources and cell types.
#  This function will accept the following arguments:
# 
# - `adata`: AnnData object containing the data to be preprocessed
# - `perturbation_key`: The key in `adata.obs` that contains the perturbation information (In this notebook's case, we provide `batch` as our perturbation)
# - `control_group`: The name of the control group in `perturbation_key` (In this notebook's case, we provide one of the batch groups as our control group)
# - `batch_key`: The key in `adata.obs` that contains the batch information (We are not providing any batch key here)
# - `dosage_key`: The key in `adata.obs` that contains the dosage information
# - `categorical_covariate_keys`: A list of keys in `adata.obs` that contain categorical covariates
# - `is_count_data`: Whether the `adata.X` is count data or not
# - `deg_uns_key`: The key in `adata.uns` that contains the differential expression results
# - `deg_uns_cat_key`: The key in `adata.obs` that contains the category information of each cell which can be used as to access differential expression results in `adata.uns[deg_uns_key]`. For example, if `deg_uns_key` is `rank_genes_groups_cov` and `deg_uns_cat_key` is `cov_cond`, then `adata.uns[deg_uns_key][cov_cond]` will contain the differential expression results for each category in `cov_cond`.
# - `max_comb_len`: The maximum number of perturbations that are applied to each cell. For example, if `max_comb_len` is 2, then the model will be trained to predict the effect of single perturbations and the effect of double perturbations.

# ### Further explanation:
# We will use the function `custom_predict` later in this notebook, which accepts customized covariate keys as input, and will return a customized reconstructed gene expression, containing just the covariates you specified to you.
# For example, we could have multiple keys in `categorical_covariate_keys` here, and only add the `cell_type` effect to the gene expression reconstruction process.

# In[ ]:


cpa.CPA.setup_anndata(adata,
                      perturbation_key='batch',
                      control_group='Sun_sample1_CS',
                      categorical_covariate_keys=['cell_type'],
                      is_count_data=True,
                      max_comb_len=1,
                     )


# In[ ]:


model_params = {
    "n_latent": 64,
    "recon_loss": "nb",
    "doser_type": "linear",
    "n_hidden_encoder": 128,
    "n_layers_encoder": 2,
    "n_hidden_decoder": 512,
    "n_layers_decoder": 2,
    "use_batch_norm_encoder": True,
    "use_layer_norm_encoder": False,
    "use_batch_norm_decoder": False,
    "use_layer_norm_decoder": True,
    "dropout_rate_encoder": 0.0,
    "dropout_rate_decoder": 0.1,
    "variational": False,
    "seed": 6977,
}

trainer_params = {
    "n_epochs_kl_warmup": None,
    "n_epochs_pretrain_ae": 30,
    "n_epochs_adv_warmup": 50,
    "n_epochs_mixup_warmup": 0,
    "mixup_alpha": 0.0,
    "adv_steps": None,
    "n_hidden_adv": 64,
    "n_layers_adv": 3,
    "use_batch_norm_adv": True,
    "use_layer_norm_adv": False,
    "dropout_rate_adv": 0.3,
    "reg_adv": 20.0,
    "pen_adv": 5.0,
    "lr": 0.0003,
    "wd": 4e-07,
    "adv_lr": 0.0003,
    "adv_wd": 4e-07,
    "adv_loss": "cce",
    "doser_lr": 0.0003,
    "doser_wd": 4e-07,
    "do_clip_grad": True,
    "gradient_clip_value": 1.0,
    "step_size_lr": 10,
}


# ## CPA Model
# 
# You can create a CPA model by creating an object from `cpa.CPA` class. The constructor of this class takes the following arguments:
# **Data related parameters:**
# - `adata`: AnnData object containing train/valid/test data
# - Optional:
#     - `split_key`: The key in `adata.obs` that contains the split information
#     - `train_split`: The value in `split_key` that corresponds to the training data
#     - `valid_split`: The value in `split_key` that corresponds to the validation data
#     - `test_split`: The value in `split_key` that corresponds to the test data
# 
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

# In[ ]:


model = cpa.CPA(adata=adata,
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

# In[ ]:


model.train(max_epochs=2000,
            use_gpu=True,
            batch_size=512,
            plan_kwargs=trainer_params,
            early_stopping_patience=5,
            check_val_every_n_epoch=5,
            save_path='pbmc',
           )


# In[ ]:


cpa.pl.plot_history(model)


# ## Restore best model
# 
# In case you have already saved your pretrained model, you can restore it using the following code. The `cpa.CPA.load` function accepts the following arguments:
# - `dir_path`: path to the directory where the model is saved
# - `adata`: anndata object
# - `use_gpu`: whether to use GPU or not

# In[ ]:


# model = cpa.CPA.load(dir_path='pbmc/',
#                      adata=adata,
#                      use_gpu=True)


# ## Latent and gene expression prediction

# ### `model.custom_predict`:
# ```
# Predicts the output of the model on the given input data.
# 
# Args:
#     covars_to_add (Optional[Sequence[str]]): List of covariates to add to the basal latent representation.
#     basal (bool): Whether to use just the basal latent representation. If True, `add_batch` and `add_pert` are ignored.
#     add_batch (bool): Whether to add the batch covariate to the latent representation.
#     add_pert (bool): Whether to add the perturbation covariate to the latent representation.
#     adata (Optional[AnnData]): The input data to predict on.
#     indices (Optional[Sequence[int]]): The indices of the cells to predict on.
#     batch_size (Optional[int]): The batch size to use for prediction.
#     n_samples (int): The number of samples to use for stochastic prediction.
#     return_mean (bool): Whether to return the mean of the samples or all the samples.
# 
# Returns:
#     latent_outputs (AnnData): A dictionary of AnnData objects containing the predicted gene expression for the specified
#     covariates, and latent representations for different covariate combinations.
# ```

# * Keep in mind that here, our `perturbation_key` is actually our batch, and therefore, when we specify `add_pert=False`, we are removing the batch effect from our prediction.
# 
# * We did not specify any key as the `batch_key` in our `setup_anndata`, therefore `add_batch` being True or False makes no difference.

# In[ ]:


# Predict using cell_type embeddings, removing the batch embeddings (batch corrected)
output_no_batch = model.custom_predict(adata=adata,
                   covars_to_add=['cell_type'],
                   add_batch=False,
                   add_pert=False,
                   batch_size=2048)

# Predict using cell_type and batch embeddings (reconstruct the original gene expressions containing batch effect)
output_batch = model.custom_predict(adata=adata,
                   covars_to_add=['cell_type'],
                   add_batch=False,
                   add_pert=True,
                   batch_size=2048)

# Reconstruct only the basal latents, ignoring both batch and cell types (basically just noise)
output_basal = model.custom_predict(adata=adata,
                   covars_to_add=['cell_type'],
                   basal=True,
                   batch_size=2048)


# * If we had more than 1 covariate, we could specify just the ones we wanted to affect our gene expression reconstruction in `covars_to_add` argument.

# ### `custom_predict` returns a dictionary of the following `AnnData` objects:
# - `latent_x_pred`: Gene Expression Reconstruction Prediction (with respect to specified arguments in `custom_predict`)
# - `latent_z`: Latent --> `z_basal + z_pert + z_covs`
# - `latent_z_corrected`: Latent --> `z_basal + z_pert + z_covs_without_batch`
# - `latent_z_no_pert`: Latent --> `z_basal + z_covs`
# - `latent_z_no_pert_corrected`: Latent --> `z_basal + z_covs_without_batch`
# - `latent_z_basal`: Latent --> `z_basal`

# In[ ]:


output_batch.keys()


# ## Visualization

# ### We first visualize latent vectors of cells:

# In[ ]:


# @title latent: basal + cell_type + batch
ad = output_batch['latent_z']
sc.pp.neighbors(ad)
sc.tl.umap(ad)

sc.pl.umap(ad,
        color=['batch', 'cell_type'],
        frameon=False,
        wspace=0.5)


# In[ ]:


#@title latent: basal + cell_type
ad = output_batch['latent_z_no_pert']
sc.pp.neighbors(ad)
sc.tl.umap(ad)

sc.pl.umap(ad,
        color=['batch', 'cell_type'],
        frameon=False,
        wspace=0.5)


# In[ ]:


#@title latent: basal
ad = output_batch['latent_z_basal']

sc.pp.neighbors(ad)
sc.tl.umap(ad)

sc.pl.umap(ad,
        color=['batch', 'cell_type'],
        frameon=False,
        wspace=0.5)


# ### **Most Important** --> Now we visualize reconstructed gene expressions using UMAP in different conditions:

# In[ ]:


#@title Gene Expression Reconstruction: basal + cell_type + batch (contains batch effect)
ad = output_batch['latent_x_pred']

sc.pp.log1p(ad)

sc.pp.neighbors(ad)
sc.tl.umap(ad)

sc.pl.umap(ad,
        color=['batch', 'cell_type'],
        frameon=False,
        wspace=0.5)


# In[ ]:


#@title Gene Expression Reconstruction: basal + cell_type (batch effect removed)
ad = output_no_batch['latent_x_pred']

sc.pp.log1p(ad)

sc.pp.neighbors(ad)
sc.tl.umap(ad)

sc.pl.umap(ad,
        color=['batch', 'cell_type'],
        frameon=False,
        wspace=0.5)


# As you can see, we have succesfully reconstructed the gene expression space, removing the batch effect using CPA. We can now use the batch effect removed reconstructed gene expressions for further analysis in our work.
