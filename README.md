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