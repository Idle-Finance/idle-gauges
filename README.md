# Idle Gauges

1. Create a virtual env (using Python 3.8):

```
python3.8 -m venv venv
```

2. Launch the virtual env
```
source venv/bin/activate
pip install -r requirements.txt
```

3. Compile contracts:

```
brownie compile
```

## Changes to Curve contracts 

Main change to Curve contracts and Liquidity Gauge system is the use of `IdleDistributor` instead of [`ERC20CRV`](https://github.com/curvefi/curve-dao-contracts/blob/master/contracts/ERC20CRV.vy) for tokens distribution. To adapt contracts to this change, [`Minter`](https://github.com/curvefi/curve-dao-contracts/blob/master/contracts/Minter.vy) contract was renamed into `DistributorProxy`. 

### `IdleDistributor` and pending distribution parameters

The `IdleDistributor` contract mimics the dynamics expressed in `ERC20CRV` Curve's contract by distributing IDLE token rewards following a schedule decided by the contract owner. The distribution parameters are:

- `rate`: the amount of tokens distributed for second
- `startEpochTime`: the starting time for the current distribution schedule/epoch.

The distribution pending parameters (`pendingRate` and `pendingStartEpochTime`) can be changed by the contract owner by calling `updatePendingParams(uint256 newRate, uint256 newStartEpochTime)`.

`IdleDistributor` first schedule is precompiled as:

- `pendingRate`: `(356_400 * 10**18) / seconds_in_a_year` (the `INITIAL_RATE` constant)
- `pendingStartEpochTime`: the block timestamp of `IdleDistributor` deployment.

## How IDLEs are distributed to staked PYTs LP tokens

IDLE rewards are computed using the integration method explained in [Curve Docs#Liquidity Gauges](https://curve.readthedocs.io/dao-gauges.html#liquidity-gauges). The substantial difference is in how these rewards are distributed and where the rates are coming from (see [LiquidityGaugeV3](https://github.com/curvefi/curve-dao-contracts/blob/master/contracts/gauges/LiquidityGaugeV3.vy) for a code comparison):

```python
# LiquidityGaugeV3.py

@external
def __init__(_lp_token: address, _distributor_proxy: address, _admin: address):
    """
    @notice Contract constructor
    @param _lp_token Liquidity Pool contract address
    @param _distributor_proxy DistributorProxy contract address
    @param _admin Admin who can kill the gauge
    """

    ...

    # Here we set the distributor instead of the Curve token.
    # The `distributor` is no more an ERC20 token. 

    distributor: address = DistributorProxy(_distributor_proxy).distributor()
    controller: address = DistributorProxy(_distributor_proxy).controller()

    ...

    # Here we are copying distribution parameters from the `IdleDistributor` contract

    self.inflation_rate = Distributor(distributor).rate()
    self.future_epoch_time = Distributor(distributor).futureEpochTimeWrite()

...

# The most important method of `LiquidityGaugeV3` is `_checkpoint`.
# Here we are checkpointing user's IDLE rewards (mostly computing the integrate function components for the user)
# `LiquidityGaugeV3` can distribute other rewards too (we use the `_checkpoint_rewards` for that).

@internal
def _checkpoint(addr: address):
    """
    @notice Checkpoint for a user
    @param addr User address
    """
    _period: int128 = self.period
    _period_time: uint256 = self.period_timestamp[_period]
    _integrate_inv_supply: uint256 = self.integrate_inv_supply[_period]
    rate: uint256 = self.inflation_rate
    new_rate: uint256 = rate
    prev_future_epoch: uint256 = self.future_epoch_time
    if prev_future_epoch >= _period_time:
        _distributor: address = self.distributor
        self.future_epoch_time = Distributor(_distributor).futureEpochTimeWrite()
        new_rate = Distributor(_distributor).rate()
        self.inflation_rate = new_rate

    if self.is_killed:
        # Stop distributing inflation as soon as killed
        rate = 0

    # Update integral of 1/supply
    if block.timestamp > _period_time:
        _working_supply: uint256 = self.working_supply
        _controller: address = self.controller
        Controller(_controller).checkpoint_gauge(self)
        prev_week_time: uint256 = _period_time
        week_time: uint256 = min((_period_time + WEEK) / WEEK * WEEK, block.timestamp)

        for i in range(500):
            dt: uint256 = week_time - prev_week_time
            w: uint256 = Controller(_controller).gauge_relative_weight(self, prev_week_time / WEEK * WEEK)

            if _working_supply > 0:
                if prev_future_epoch >= prev_week_time and prev_future_epoch < week_time:
                    # If we went across one or multiple epochs, apply the rate
                    # of the first epoch until it ends, and then the rate of
                    # the last epoch.
                    # If more than one epoch is crossed - the gauge gets less,
                    # but that'd meen it wasn't called for more than 1 year
                    _integrate_inv_supply += rate * w * (prev_future_epoch - prev_week_time) / _working_supply
                    rate = new_rate
                    _integrate_inv_supply += rate * w * (week_time - prev_future_epoch) / _working_supply
                else:
                    _integrate_inv_supply += rate * w * dt / _working_supply
                # On precisions of the calculation
                # rate ~= 10e18
                # last_weight > 0.01 * 1e18 = 1e16 (if pool weight is 1%)
                # _working_supply ~= TVL * 1e18 ~= 1e26 ($100M for example)
                # The largest loss is at dt = 1
                # Loss is 1e-9 - acceptable

            if week_time == block.timestamp:
                break
            prev_week_time = week_time
            week_time = min(week_time + WEEK, block.timestamp)

    _period += 1
    self.period = _period
    self.period_timestamp[_period] = block.timestamp
    self.integrate_inv_supply[_period] = _integrate_inv_supply

    # Update user-specific integrals
    _working_balance: uint256 = self.working_balances[addr]
    self.integrate_fraction[addr] += _working_balance * (_integrate_inv_supply - self.integrate_inv_supply_of[addr]) / 10 ** 18
    self.integrate_inv_supply_of[addr] = _integrate_inv_supply
    self.integrate_checkpoint_of[addr] = block.timestamp

# `_update_liquidity_limit` is responsible for boosting computation.
# More details can be found at [Curve Docs#Boosting](https://curve.readthedocs.io/dao-gauges.html#boosting)

@internal
def _update_liquidity_limit(addr: address, l: uint256, L: uint256):
    """
    @notice Calculate limits which depend on the amount of IDLE token per-user.
            Effectively it calculates working balances to apply amplification
            of IDLE distribution by `distributor`
    @param addr User address
    @param l User's amount of liquidity (LP tokens)
    @param L Total amount of liquidity (LP tokens)
    """
    # To be called after totalSupply is updated
    _voting_escrow: address = self.voting_escrow
    voting_balance: uint256 = ERC20(_voting_escrow).balanceOf(addr)
    voting_total: uint256 = ERC20(_voting_escrow).totalSupply()

    lim: uint256 = l * TOKENLESS_PRODUCTION / 100
    if voting_total > 0:
        lim += L * voting_balance / voting_total * (100 - TOKENLESS_PRODUCTION) / 100

    lim = min(l, lim)
    old_bal: uint256 = self.working_balances[addr]
    self.working_balances[addr] = lim
    _working_supply: uint256 = self.working_supply + lim - old_bal
    self.working_supply = _working_supply

    log UpdateLiquidityLimit(addr, l, L, lim, _working_supply)

```

