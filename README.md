# Idle Gauges

Contracts used by Idle Finance to incentivize PYTs (Perpetual Yield Tranches). Contracts are adapted from [Curve DAO contracts](https://github.com/curvefi/curve-dao-contracts).

## Overview

More details about Idle Gauges workings can be found in [contracts/README.md](contracts/README.md).

View the [Curve DAO documentation](https://curve.readthedocs.io/dao-overview.html) for a more in-depth explanation of how Curve contracts works.

## Development

1. Create a virtual env (using Python 3.8):

```bash
python3.8 -m venv venv
```

2. Launch the virtual env
```bash
source venv/bin/activate
pip install -r requirements.txt
```

3. Compile contracts:

```bash
brownie compile
```

4. Test contracts:

```bash
brownie test tests/unit # unit tests
brownie test tests/e2e  --network mainnet-fork # e2e tests, needs mainnet forking
```

## Changes to Curve contracts 

- `Minter` (renamed to `DistributorProxy`): https://www.diffchecker.com/4Le95AeZ
- `LiquidityGaugeV3`: https://www.diffchecker.com/y1nPgktn
- `GaugeController`: https://www.diffchecker.com/i7GV4Y08
- `GaugeProxy`: https://www.diffchecker.com/zUhUxtv7

## Deployed contracts

### Ethereum Mainnet

Distributor: 0x1276A8ee84900bD8CcA6e9b3ccB99FF4771Fe329
DistributorProxy: 0x074306BC6a6Fc1bD02B425dd41D742ADf36Ca9C6
GaugeController: 0xaC69078141f76A1e257Ee889920d02Cc547d632f
GaugeProxy: 0xBb1CB94F14881DDa38793d7F6F99d96Db0594051
LiquidityGauge AATranche_crvALUSD: 0x21dDA17dFF89eF635964cd3910d167d562112f57
LiquidityGauge AATranche_lido: 0x675eC042325535F6e176638Dd2d4994F645502B9