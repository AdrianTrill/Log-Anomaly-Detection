"""
Transformer Encoder for binary log-sequence anomaly detection.

Architecture:
    Token Embedding  ->  Positional Embedding  ->  Transformer Encoder Layers
    ->  Mean Pooling (over non-PAD positions)  ->  Linear Classification Head

Input:  integer token-ID sequences of shape (batch, seq_len)
Output: single logit per sequence (use BCEWithLogitsLoss for training)
"""

import math
import torch
import torch.nn as nn


class LogAnomalyTransformer(nn.Module):

    def __init__(
        self,
        vocab_size: int = 31,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 128,
        max_seq_len: int = 50,
        dropout: float = 0.1,
        pad_id: int = 0,
    ):
        super().__init__()
        self.pad_id = pad_id
        self.d_model = d_model

        self.token_emb = nn.Embedding(vocab_size, d_model, padding_idx=pad_id)
        self.pos_emb = nn.Embedding(max_seq_len, d_model)
        self.emb_dropout = nn.Dropout(dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.head = nn.Linear(d_model, 1)

        self._init_weights()

    def _init_weights(self) -> None:
        nn.init.xavier_uniform_(self.token_emb.weight)
        with torch.no_grad():
            self.token_emb.weight[self.pad_id].zero_()
        nn.init.xavier_uniform_(self.pos_emb.weight)
        nn.init.xavier_uniform_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len) integer token IDs
        Returns:
            logits: (batch,) raw scores — apply sigmoid for probabilities
        """
        padding_mask = x == self.pad_id  # True where PAD

        positions = torch.arange(x.size(1), device=x.device).unsqueeze(0)
        embedded = self.token_emb(x) + self.pos_emb(positions)
        embedded = self.emb_dropout(embedded)

        encoded = self.encoder(embedded, src_key_padding_mask=padding_mask)

        pooled = self._mean_pool(encoded, padding_mask)
        logits = self.head(pooled).squeeze(-1)
        return logits

    @staticmethod
    def _mean_pool(encoded: torch.Tensor, padding_mask: torch.Tensor) -> torch.Tensor:
        """Average encoded representations over non-PAD positions."""
        mask = ~padding_mask  # True where real tokens
        mask_expanded = mask.unsqueeze(-1).float()
        summed = (encoded * mask_expanded).sum(dim=1)
        lengths = mask_expanded.sum(dim=1).clamp(min=1)
        return summed / lengths
