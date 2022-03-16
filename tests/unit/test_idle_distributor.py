import pytest
import brownie

from brownie.test import given, strategy

WEEK = 86400 * 7

@pytest.fixture(scope="function")
def fake_idle(ERC20LP, accounts):
    token = ERC20LP.deploy("Fake IDLE", "fIDLE", 18, 100000000000 * 1e18, {'from': accounts[0]})
    token.set_minter(accounts[0])
    token.mint(accounts[0], 100000000000 * 1e18)
    return token

@pytest.fixture(scope="function")
def distributor(Distributor, fake_idle, accounts):
    yield Distributor.deploy(fake_idle, accounts[0], {"from": accounts[0]})

# initial setup

def initial_setup(chain, distributor, accounts, fake_idle):
    chain.sleep(86401)
    distributor.updateDistributionParameters()
    fake_idle.transfer(distributor, fake_idle.balanceOf(accounts[0]), {'from': accounts[0]})


# test epoch time distribution

def test_start_epoch_time_write(distributor, chain):
    creation_time = distributor.startEpochTime()
    chain.sleep(WEEK)
    chain.mine()

    # the constant function should not report a changed value
    assert distributor.startEpochTime() == creation_time

    # the state-changing function should show the changed value
    assert distributor.startEpochTimeWrite().return_value == creation_time + WEEK

    # after calling the state-changing function, the view function is changed
    assert distributor.startEpochTime() == creation_time + WEEK


def test_start_epoch_time_write_same_epoch(distributor):
    # calling `start_epoch_token_write` within the same epoch should not raise
    distributor.startEpochTimeWrite()
    distributor.startEpochTimeWrite()


def test_update_mining_parameters(distributor, chain, accounts):
    creation_time = distributor.startEpochTime()
    new_epoch = creation_time + WEEK - chain.time()
    chain.sleep(new_epoch)
    distributor.updateDistributionParameters({"from": accounts[0]})


def test_update_mining_parameters_same_epoch(distributor, chain, accounts):
    creation_time = distributor.startEpochTime()
    new_epoch = creation_time + WEEK - chain.time()
    chain.sleep(new_epoch - 3)
    with brownie.reverts("epoch still running"):
        distributor.updateDistributionParameters({"from": accounts[0]})


# test setters


def test_set_distributor_proxy_only_owner(accounts, distributor):
    with brownie.reverts("Ownable: caller is not the owner"):
        distributor.setDistributorProxy(accounts[2], {"from": accounts[1]})


def test_set_pending_rate_only_admin(accounts, distributor):
    with brownie.reverts("Ownable: caller is not the owner"):
        distributor.setPendingRate(1, {"from": accounts[1]})


# distribution delay


def test_rate(accounts, chain, distributor):
    assert distributor.rate() == 0

    chain.sleep(86401)
    distributor.updateDistributionParameters({"from": accounts[0]})

    assert distributor.rate() > 0


def test_start_epoch_time(accounts, chain, distributor):
    creation_time = distributor.startEpochTime()
    assert creation_time == distributor.tx.timestamp + 86400 - WEEK

    chain.sleep(86401)
    distributor.updateDistributionParameters({"from": accounts[0]})

    assert distributor.startEpochTime() == creation_time + WEEK


def test_available_to_distribute(accounts, chain, distributor):
    assert distributor.availableToDistribute() == 0

    chain.sleep(86401)

    distributor.updateDistributionParameters({"from": accounts[0]})
    chain.mine(timedelta=WEEK)

    # this is not a precise comparison because `availableToDistribute`
    # depends on block.timestamp

    assert distributor.availableToDistribute() > 0
    assert distributor.epochStartingDistributed() == 0    

# test pending rate

def test_pending_rate(accounts, chain, distributor):
    chain.sleep(86401)
    distributor.updateDistributionParameters({"from": accounts[0]})
    distributor.setPendingRate(100, {"from": accounts[0]})
    
    assert distributor.rate() > 0

    chain.mine(timedelta=WEEK)
    distributor.updateDistributionParameters({"from": accounts[0]})
    assert distributor.rate() == 100

def test_rate_to_zero(accounts, chain, distributor):
    chain.sleep(86401)
    distributor.updateDistributionParameters({"from": accounts[0]})
    distributor.setPendingRate(0, {"from": accounts[0]})

    assert distributor.rate() > 0

    chain.mine(timedelta=WEEK)
    distributor.updateDistributionParameters({"from": accounts[0]})
    assert distributor.rate() == 0


# distribute

@given(duration=strategy("uint", min_value=86500, max_value=WEEK))
def test_distribute(accounts, chain, distributor, fake_idle, duration):
    initial_setup(chain, distributor, accounts, fake_idle)

    distributor.setDistributorProxy(accounts[0], {"from": accounts[0]})
    creation_time = distributor.startEpochTime()
    initial_distributed = distributor.distributed()
    rate = distributor.rate()
    chain.sleep(duration)

    amount = (chain.time() - creation_time) * rate
    distributor.distribute(accounts[1], amount, {"from": accounts[0]})

    assert fake_idle.balanceOf(accounts[1]) == amount
    assert distributor.distributed() == initial_distributed + amount

@given(duration=strategy("uint", min_value=86500, max_value=WEEK))
def test_overdistribute(accounts, chain, fake_idle, distributor, duration):
    initial_setup(chain, distributor, accounts, fake_idle)

    distributor.setDistributorProxy(accounts[0], {"from": accounts[0]})
    creation_time = distributor.startEpochTime()
    rate = distributor.rate()
    chain.sleep(duration)

    with brownie.reverts("amount too high"):
        distributor.distribute(accounts[1], (chain.time() - creation_time + 2) * rate, {"from": accounts[0]})


@given(durations=strategy("uint[5]", min_value=WEEK * 0.33, max_value=WEEK * 0.9))
def test_distribute_multiple(accounts, chain, distributor, fake_idle, durations):
    initial_setup(chain, distributor, accounts, fake_idle)

    distributor.setDistributorProxy(accounts[0], {"from": accounts[0]})
    distributed_idle = distributor.distributed()
    balance = fake_idle.balanceOf(accounts[1])
    epoch_start = distributor.startEpochTime()

    assert epoch_start > 0

    for time in durations:
        chain.mine(timedelta=time)

        if chain.time() - epoch_start > WEEK:
            distributor.updateDistributionParameters({"from": accounts[0]})
            epoch_start = distributor.startEpochTime()

        amount = distributor.availableToDistribute() - distributed_idle
        distributor.distribute(accounts[1], amount, {"from": accounts[0]})

        balance += amount
        distributed_idle += amount

        assert fake_idle.balanceOf(accounts[1]) == balance
        assert distributor.distributed() == distributed_idle

def test_emergency_withdraw(chain, accounts, distributor, fake_idle):
    initial_setup(chain, distributor, accounts, fake_idle)

    balance = fake_idle.balanceOf(distributor)
    distributor.emergencyWithdraw(balance, {'from': accounts[0]})

    assert balance > 0
    assert fake_idle.balanceOf(distributor) == 0