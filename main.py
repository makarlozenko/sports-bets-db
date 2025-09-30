# Formulate dataset from pandas to gluonts
import torch
from tactis.gluon.estimator import TACTiSEstimator
from tactis.gluon.trainer import TACTISTrainer
from tactis.gluon.dataset import generate_hp_search_datasets, generate_prebacktesting_datasets, generate_backtesting_datasets
from tactis.gluon.metrics import compute_validation_metrics
from tactis.gluon.plots import plot_four_forecasts
from gluonts.evaluation.backtest import make_evaluation_predictions

import pandas as pd
import numpy as np

from gluonts.dataset.common import ListDataset, MetaData
from gluonts.dataset.field_names import FieldName
from gluonts.dataset.multivariate_grouper import MultivariateGrouper



file_location = r"C:\Users\Admin\Desktop\Universitetas\Tactisextended_data.csv"



df = (
    pd.read_csv(file_location)                # <- your file
      .assign(timestamp=lambda d: pd.to_datetime(d["timestamp"]))
      .set_index("timestamp")
      .sort_index()
)
FREQ = "Q"
PRED_LEN = 12
history_length = 7 * PRED_LEN


series = [
    {
        FieldName.START : pd.Timestamp(df.index[0], freq=FREQ),  # <-- add freq!
        FieldName.TARGET: df[col].to_numpy(dtype=np.float32),
        FieldName.ITEM_ID: col,
    }
    for col in df.columns
]

# 80/20 split:

train_entries, valid_entries = [], []

for entry in series:                      # one loop per original column
    target      = entry[FieldName.TARGET]
    n_total     = len(target)

    cut_point   = int(0.8 * n_total)      # ---- 80 % cutoff
    cut_point   = max(cut_point, history_length + 1)  # safety guard

    # ------------------ training slice (0 ... cut_point-1)
    e_train = entry.copy()
    e_train[FieldName.TARGET] = target[:cut_point]
    train_entries.append(e_train)

    start_idx   = cut_point - history_length
    e_valid = entry.copy()
    e_valid[FieldName.START] = (
        entry[FieldName.START]
        + pd.tseries.frequencies.to_offset(FREQ) * start_idx
    )
    e_valid[FieldName.TARGET] = target[start_idx:]
    valid_entries.append(e_valid)


train_ds = MultivariateGrouper()(train_entries)
valid_ds = MultivariateGrouper()(valid_entries)
metadata = MetaData(freq=FREQ, prediction_length=PRED_LEN)

# Tactis call:



estimator = TACTiSEstimator(
    model_parameters = {
        "flow_series_embedding_dim": 5,
        "copula_series_embedding_dim": 5,
        "flow_input_encoder_layers": 2,
        "copula_input_encoder_layers": 2,
        "input_encoding_normalization": True,
        "data_normalization": "standardization",
        "loss_normalization": "series",
        "bagging_size": 4,
        "positional_encoding":{
            "dropout": 0.0,
        },
        "flow_temporal_encoder":{
            "attention_layers": 2,
            "attention_heads": 1,
            "attention_dim": 16,
            "attention_feedforward_dim": 16,
            "dropout": 0.0,
        },
        "copula_temporal_encoder":{
            "attention_layers": 2,
            "attention_heads": 1,
            "attention_dim": 16,
            "attention_feedforward_dim": 16,
            "dropout": 0.0,
        },
        "copula_decoder":{
            "min_u": 0.05,
            "max_u": 0.95,
            "attentional_copula": {
                "attention_heads": 3,
                "attention_layers": 1,
                "attention_dim": 8,
                "mlp_layers": 2,
                "mlp_dim": 48,
                "resolution": 20,
                "activation_function": "relu"
            },
            "dsf_marginal": {
                "mlp_layers": 2,
                "mlp_dim": 48,
                "flow_layers": 2,
                "flow_hid_dim": 8,
            },
        },
    },
    num_series = train_ds.list_data[0]["target"].shape[0],
    history_length = history_length,
    prediction_length = metadata.prediction_length,
    freq = metadata.freq,
    trainer = TACTISTrainer(
        epochs_phase_1 = 20,
        epochs_phase_2 = 20,
        batch_size = 12,
        #num_batches_per_epoch = 512,
        learning_rate = 1e-3,
        weight_decay = 1e-4,
        #maximum_learning_rate = 1e-3,
        clip_gradient = 1e3,
        device = torch.device("cuda:0"),
        checkpoint_dir = "checkpoints",
    ),
    cdf_normalization = False,
    num_parallel_samples = 100,
)

model = estimator.train(train_ds, valid_ds, num_workers=16)