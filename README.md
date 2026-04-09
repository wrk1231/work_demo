# Opt Research

Synthetic option data generation with arbitrage-free guarantees using SVI volatility surface parameterization.

## Installation

```bash
conda create -n opt_research python=3.12.12 -y
conda activate opt_research
pip install -e .
pip install -e ".[dev]"
```

## Usage

Generate synthetic option data:

```bash
python -m opt_research.data_generator
```

Run tests:

```bash
pytest
```
