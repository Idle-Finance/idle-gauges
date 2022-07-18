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

- Distributor: 0x1276A8ee84900bD8CcA6e9b3ccB99FF4771Fe329
- DistributorProxy: 0x074306BC6a6Fc1bD02B425dd41D742ADf36Ca9C6
- GaugeController: 0xaC69078141f76A1e257Ee889920d02Cc547d632f
- GaugeProxy: 0xBb1CB94F14881DDa38793d7F6F99d96Db0594051
- LiquidityGauge AATranche_crvALUSD: 0x21dDA17dFF89eF635964cd3910d167d562112f57
- LiquidityGauge AATranche_lido: 0x675eC042325535F6e176638Dd2d4994F645502B9
- LiquidityGauge AATranche_frax: 0x7ca919Cf060D95B3A51178d9B1BCb1F324c8b693
- LiquidityGauge AATranche_mim: 0x8cC001dd6C9f8370dB99c1e098e13215377Ecb95
- LiquidityGauge AATranche_3eur: 0xDfB27F2fd160166dbeb57AEB022B9EB85EA4611C
- LiquidityGauge AATranche_stecrv: 0x30a047d720f735Ad27ad384Ec77C36A4084dF63E
- LiquidityGauge AATranche_musd: 0xAbd5e3888ffB552946Fc61cF4C816A73feAee42E
- LiquidityGauge AATranche_mstable: 0x41653c7AF834F895Db778B1A31EF4F68Be48c37c
- LiquidityGauge AATranche_pbtc: 0x2bea05307b42707be6cce7a16d700a06ff93a29d
- LiquidityGauge AATranche_eagEUR: 0x8f195979f7af6c500b4688e492d07036c730c1b2
- LiquidityGauge AATranche_eUSDC: 0x1cd24f833af78ae877f90569eaec3174d6769995
- LiquidityGauge AATranche_eDAI: 0x57d59d4bbb0e2432f1698f33d4a47b3c7a9754f3
- LiquidityGauge AATranche_eUSDT: 0x0c3310b0b57b86d376040b755f94a925f39c4320

- Multirewards AATranche_lido: 0xA357AF9430e4504419A7A05e217D4A490Ecec6FA

Factory for minimal clone: 0x91baced76e3e327ba7850ef82a7a8251f6e43fb8
Cloneable Multirewards implementation:
0x1e086b7d6e6ab3e537f921d60ca8e318fe8b32d7 
- Multirewards AATranche_musd3crv: 0x7f366a2b4c4380fd9746cf10b4ded562c890b0b1
- Multirewards AATranche_pbtc: 0x7d4091D8b28d09b4135905213DE105C45d7F459d