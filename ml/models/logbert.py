"""
LogBERT — BERT-style model for log-sequence anomaly detection.

Two-phase approach:
  Phase 1 (pre-training):  Masked Log Key Prediction (MLKP)
      Randomly mask template IDs in a sequence, train the encoder to predict
      the original tokens.  This learns general log pattern representations
      without using any labels.

  Phase 2 (fine-tuning):   Supervised binary classification
      Freeze-then-unfreeze the pre-trained encoder, add a classification head
      on the [CLS] output, and fine-tune with BCEWithLogitsLoss.

Key differences from LogAnomalyTransformer:
  - Two special tokens: [MASK] and [CLS] (added on top of existing vocab)
  - CLS-based pooling instead of mean pooling
  - Separate MLM and classification heads
  - Two forward paths: forward_mlm() and forward_cls()

Input:  integer token-ID sequences of shape (batch, seq_len)
        [CLS] is prepended internally — callers pass raw sequences.
"""

import torch
import torch.nn as nn


class LogBERT(nn.Module):

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
        self.original_vocab_size = vocab_size

        self.mask_id = vocab_size
        self.cls_id = vocab_size + 1
        effective_vocab = vocab_size + 2

        self.token_emb = nn.Embedding(effective_vocab, d_model, padding_idx=pad_id)
        self.pos_emb = nn.Embedding(max_seq_len + 1, d_model)  # +1 for [CLS]
        self.emb_dropout = nn.Dropout(dropout)
        self.emb_norm = nn.LayerNorm(d_model)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.mlm_head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model),
            nn.Linear(d_model, effective_vocab),
        )

        self.cls_head = nn.Linear(d_model, 1)

        self._init_weights()

    def _init_weights(self) -> None:
        nn.init.xavier_uniform_(self.token_emb.weight)
        with torch.no_grad():
            self.token_emb.weight[self.pad_id].zero_()
        nn.init.xavier_uniform_(self.pos_emb.weight)
        nn.init.xavier_uniform_(self.cls_head.weight)
        nn.init.zeros_(self.cls_head.bias)
        for module in self.mlm_head:
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)

    def _prepend_cls(self, x: torch.Tensor) -> torch.Tensor:
        """Prepend [CLS] token: (batch, seq_len) -> (batch, seq_len + 1)."""
        batch_size = x.size(0)
        cls_col = torch.full(
            (batch_size, 1), self.cls_id, dtype=x.dtype, device=x.device
        )
        return torch.cat([cls_col, x], dim=1)

    def _encode(self, x: torch.Tensor) -> torch.Tensor:
        """
        Shared encoder pass.

        Args:
            x: (batch, seq_len) raw token IDs (before CLS prepend)
        Returns:
            encoded: (batch, seq_len + 1, d_model) encoder outputs
        """
        x = self._prepend_cls(x)
        padding_mask = x == self.pad_id

        positions = torch.arange(x.size(1), device=x.device).unsqueeze(0)
        embedded = self.token_emb(x) + self.pos_emb(positions)
        embedded = self.emb_norm(embedded)
        embedded = self.emb_dropout(embedded)

        return self.encoder(embedded, src_key_padding_mask=padding_mask)

    def forward_mlm(self, x: torch.Tensor) -> torch.Tensor:
        """
        MLM forward pass for pre-training.

        Args:
            x: (batch, seq_len) sequences with some tokens replaced by MASK_ID
        Returns:
            logits: (batch, seq_len + 1, effective_vocab) per-position token logits
                    Loss is computed externally on masked positions only.
        """
        encoded = self._encode(x)
        return self.mlm_head(encoded)

    def forward_cls(self, x: torch.Tensor) -> torch.Tensor:
        """
        Classification forward pass for fine-tuning / inference.

        Args:
            x: (batch, seq_len) unmasked sequences
        Returns:
            logits: (batch,) raw scores — apply sigmoid for probabilities
        """
        encoded = self._encode(x)
        cls_output = encoded[:, 0, :]
        return self.cls_head(cls_output).squeeze(-1)
