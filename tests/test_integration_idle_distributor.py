import brownie
import pytest

from brownie import Contract  
from brownie.test import given, strategy


WEEK = 86400 * 7
SIX_MONTHS = 86400 * 186
IDLE_WHALE = '0x107a369bc066c77ff061c7d2420618a6ce31b925'

@pytest.fixture(scope="module")
def idle_token():
    yield Contract.from_explorer('0x875773784Af8135eA0ef43b5a374AaD105c5D39e')

@pytest.fixture(scope="module")
def distributor(IdleDistributor, accounts):
    yield IdleDistributor.deploy({"from": accounts[0]})

@pytest.fixture(scope="module", autouse=True)
def initial_setup(chain, distributor, idle_token):
    chain.sleep(86401)
    distributor.updateDistributionParameters()
    idle_token.transfer(distributor, idle_token.balanceOf(IDLE_WHALE), {'from': IDLE_WHALE})


# distribute integration tests

@given(duration=strategy("uint", min_value=86500, max_value=SIX_MONTHS))
def test_distribute(accounts, chain, distributor, idle_token, duration):
    distributor.setDistributorProxy(accounts[0], {"from": accounts[0]})
    creation_time = distributor.startEpochTime()
    initial_distributed = distributor.distributedIdle()
    rate = distributor.rate()
    chain.sleep(duration)

    amount = (chain.time() - creation_time) * rate
    distributor.distribute(accounts[1], amount, {"from": accounts[0]})

    assert idle_token.balanceOf(accounts[1]) == amount
    assert distributor.distributedIdle() == initial_distributed + amount


@given(duration=strategy("uint", min_value=86500, max_value=SIX_MONTHS))
def test_overdistribute(accounts, chain, distributor, duration):
    distributor.setDistributorProxy(accounts[0], {"from": accounts[0]})
    creation_time = distributor.startEpochTime()
    rate = distributor.rate()
    chain.sleep(duration)

    with brownie.reverts("amount too high"):
        distributor.distribute(accounts[1], (chain.time() - creation_time + 2) * rate, {"from": accounts[0]})


@given(durations=strategy("uint[5]", min_value=SIX_MONTHS * 0.33, max_value=SIX_MONTHS * 0.9))
def test_distribute_multiple(accounts, chain, distributor, idle_token, durations):
    distributor.setDistributorProxy(accounts[0], {"from": accounts[0]})
    distributed_idle = distributor.distributedIdle()
    balance = idle_token.balanceOf(accounts[1])
    epoch_start = distributor.startEpochTime()

    for time in durations:
        chain.sleep(time)

        if chain.time() - epoch_start > SIX_MONTHS:
            distributor.updateDistributionParameters({"from": accounts[0]})
            epoch_start = distributor.startEpochTime()

        amount = distributor.availableToDistribute() - distributed_idle
        distributor.distribute(accounts[1], amount, {"from": accounts[0]})

        balance += amount
        distributed_idle += amount

        assert idle_token.balanceOf(accounts[1]) == balance
        assert distributor.distributedIdle() == distributed_idle

def test_emergency_withdraw(accounts, distributor, idle_token):
    balance = idle_token.balanceOf(distributor)
    distributor.emergencyWithdraw(accounts[0], balance, {'from': accounts[0]})

    assert balance > 0
    assert idle_token.balanceOf(distributor) == 0