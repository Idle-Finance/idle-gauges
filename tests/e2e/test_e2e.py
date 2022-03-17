import pytest

from brownie import Contract, interface, ZERO_ADDRESS

MAX_UINT256 = 2**256 - 1
WEEK = 7 * 86400

DAI_WHALE = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
FEI_WHALE = "0x956F47F50A910163D8BF957Cf5846D573E7f87CA"
IDLE_GOVERNABLE_FUND = "0xb0aa1f98523ec15932dd5faac5d86e57115571c7"


def approx(a, b, precision=1e-10):
    if a == b == 0:
        return True
    return 2 * abs(a - b) / (a + b) <= precision


@pytest.fixture(scope="function")
def reward_coin(ERC20LP, accounts):
    yield ERC20LP.deploy("Rewards", "RWRD", 18, 10**9, {"from": accounts[0]})


@pytest.fixture(scope="function")
def idle_token():
    yield Contract.from_explorer("0x875773784Af8135eA0ef43b5a374AaD105c5D39e")


@pytest.fixture(scope="function")
def tranche_dai():
    yield Contract.from_explorer("0xd0DbcD556cA22d3f3c142e9a3220053FD7a247BC")


@pytest.fixture(scope="function")
def tranche_fei():
    yield Contract.from_explorer("0x77648A2661687ef3B05214d824503F6717311596")


@pytest.fixture(scope="function")
def distributor(Distributor, idle_token, accounts):
    yield Distributor.deploy(idle_token, accounts[0], accounts[0], {"from": accounts[0]})


@pytest.fixture(scope="function")
def voting_escrow():
    # stkIDLE
    yield Contract.from_explorer("0xaac13a116ea7016689993193fce4badc8038136f")


@pytest.fixture(scope="function")
def gauge_controller(GaugeController, accounts, voting_escrow):
    yield GaugeController.deploy(voting_escrow, {"from": accounts[0]})


@pytest.fixture(scope="function")
def distributor_proxy(DistributorProxy, accounts, gauge_controller, distributor):
    yield DistributorProxy.deploy(distributor, gauge_controller, {"from": accounts[0]})


@pytest.fixture(scope="function")
def gauge_dai(LiquidityGaugeV3, accounts, tranche_dai, distributor_proxy):
    yield LiquidityGaugeV3.deploy(
        tranche_dai.AATranche(), distributor_proxy, accounts[0], {"from": accounts[0]}
    )


@pytest.fixture(scope="function")
def gauge_fei(LiquidityGaugeV3, accounts, tranche_fei, distributor_proxy):
    yield LiquidityGaugeV3.deploy(
        tranche_fei.AATranche(), distributor_proxy, accounts[0], {"from": accounts[0]}
    )


@pytest.fixture(scope="function")
def admin(accounts):
    yield accounts[0]


@pytest.fixture(scope="function")
def dai():
    yield Contract.from_explorer("0x6B175474E89094C44Da98b954EedeAC495271d0F")


@pytest.fixture(scope="function")
def fei():
    yield Contract.from_explorer("0x956F47F50A910163D8BF957Cf5846D573E7f87CA")

def test_e2e_claimable_idle_per_gauge_when_voting(
    admin,
    accounts,
    chain,
    idle_token,
    voting_escrow,
    distributor,
    distributor_proxy,
    gauge_controller,
    tranche_dai,
    tranche_fei,
    gauge_dai,
    gauge_fei,
    dai,
    fei,
):
    # initialize distributor
    chain.mine(timedelta=86400 + 1)
    distributor.setDistributorProxy(distributor_proxy, {"from": admin})
    distributor.updateDistributionParameters({"from": admin})
    idle_token.transfer(distributor, 178_200 * 1e18, {"from": IDLE_GOVERNABLE_FUND})

    # gauges config
    gauge_controller.add_type("Senior Tranches LP token", 10**18, {"from": admin})
    gauge_controller.add_gauge(gauge_dai, 0, 1, {"from": admin})
    gauge_controller.add_gauge(gauge_fei, 0, 1, {"from": admin})

    # alice and bob config
    (alice, bob) = (accounts[1], accounts[2])

    # transfer a different amount of IDLEs to alice and bob
    idle_token.transfer(alice, 100 * 1e18, {"from": IDLE_GOVERNABLE_FUND})
    idle_token.transfer(bob, 10 * 1e18, {"from": IDLE_GOVERNABLE_FUND})

    # alice and bob creates locks
    idle_token.approve(voting_escrow, 100 * 1e18, {"from": alice})
    voting_escrow.create_lock(100 * 1e18, 1668902400, {"from": alice})

    idle_token.approve(voting_escrow, 10 * 1e18, {"from": bob})
    voting_escrow.create_lock(10 * 1e18, 1668902400, {"from": bob})

    # vote for gauge weights
    gauge_controller.vote_for_gauge_weights(gauge_dai, 10000, {"from": alice})
    gauge_controller.vote_for_gauge_weights(gauge_fei, 10000, {"from": bob})

    # transfer DAI and FEI to alice and bob
    dai.transfer(alice, 1000 * 1e18, {"from": DAI_WHALE})
    fei.transfer(bob, 1000 * 1e18, {"from": FEI_WHALE})

    # deposit into tranches
    dai.approve(tranche_dai, 1000 * 1e18, {"from": alice})
    tranche_dai.depositAA(1000 * 1e18, {"from": alice})

    fei.approve(tranche_fei, 1000 * 1e18, {"from": bob})
    tranche_fei.depositAA(1000 * 1e18, {"from": bob})

    # stake into gauges
    aa_dai = interface.ERC20(tranche_dai.AATranche())
    aa_dai.approve(gauge_dai, aa_dai.balanceOf(alice), {"from": alice})
    gauge_dai.deposit(aa_dai.balanceOf(alice), {"from": alice})

    aa_fei = interface.ERC20(tranche_fei.AATranche())
    aa_fei.approve(gauge_fei, aa_fei.balanceOf(bob), {"from": bob})
    gauge_fei.deposit(aa_fei.balanceOf(bob), {"from": bob})

    # sleep for a while
    chain.sleep(4 * WEEK)
    chain.mine()

    # mint idles
    distributor_proxy.distribute(gauge_dai, {"from": alice})
    distributor_proxy.distribute(gauge_fei, {"from": bob})

    assert idle_token.balanceOf(bob) < idle_token.balanceOf(alice)
    assert (
        idle_token.balanceOf(bob) + idle_token.balanceOf(alice)
        <= distributor.availableToDistribute()
    )


def test_e2e_boost_user_claimable_in_same_gauge(
    admin,
    accounts,
    chain,
    idle_token,
    voting_escrow,
    distributor,
    distributor_proxy,
    gauge_controller,
    tranche_dai,
    gauge_dai,
    dai,
):
    # initialize distributor
    chain.mine(timedelta=86400 + 1)
    distributor.setDistributorProxy(distributor_proxy, {"from": admin})
    distributor.updateDistributionParameters({"from": admin})
    idle_token.transfer(distributor, 178_200 * 1e18, {"from": IDLE_GOVERNABLE_FUND})

    # gauges config
    gauge_controller.add_type("Senior Tranches LP token", 10**18, {"from": admin})
    gauge_controller.add_gauge(gauge_dai, 0, 1, {"from": admin})

    # alice and bob config
    (alice, bob) = (accounts[3], accounts[4])

    # transfer a different amount of IDLEs to alice and bob
    idle_token.transfer(alice, 100 * 1e18, {"from": IDLE_GOVERNABLE_FUND})

    # alice creates locks while bob has not lock
    idle_token.approve(voting_escrow, 100 * 1e18, {"from": alice})
    voting_escrow.create_lock(100 * 1e18, 1668902400, {"from": alice})

    # transfer DAI to alice and bob
    dai.transfer(alice, 1000 * 1e18, {"from": DAI_WHALE})
    dai.transfer(bob, 1000 * 1e18, {"from": DAI_WHALE})

    # deposit into tranches
    dai.approve(tranche_dai, 1000 * 1e18, {"from": alice})
    tranche_dai.depositAA(1000 * 1e18, {"from": alice})

    dai.approve(tranche_dai, 1000 * 1e18, {"from": bob})
    tranche_dai.depositAA(1000 * 1e18, {"from": bob})

    # stake into gauges
    aa_dai = interface.ERC20(tranche_dai.AATranche())
    aa_dai.approve(gauge_dai, aa_dai.balanceOf(alice), {"from": alice})
    gauge_dai.deposit(aa_dai.balanceOf(alice), {"from": alice})

    aa_dai = interface.ERC20(tranche_dai.AATranche())
    aa_dai.approve(gauge_dai, aa_dai.balanceOf(bob), {"from": bob})
    gauge_dai.deposit(aa_dai.balanceOf(bob), {"from": bob})

    # sleep for a while
    chain.sleep(4 * WEEK)
    chain.mine()

    # mint idles
    distributor_proxy.distribute(gauge_dai, {"from": alice})
    distributor_proxy.distribute(gauge_dai, {"from": bob})

    assert idle_token.balanceOf(bob) < idle_token.balanceOf(alice)


def test_e2e_vote_reflect_on_next_epoch(
    admin,
    accounts,
    chain,
    idle_token,
    voting_escrow,
    distributor,
    distributor_proxy,
    gauge_controller,
    tranche_dai,
    tranche_fei,
    gauge_dai,
    gauge_fei,
    dai,
    fei,
):
    # initialize distributor
    chain.mine(timedelta=86400 + 1)
    distributor.setDistributorProxy(distributor_proxy, {"from": admin})
    distributor.updateDistributionParameters({"from": admin})
    idle_token.transfer(distributor, 178_200 * 1e18, {"from": IDLE_GOVERNABLE_FUND})

    # gauges config
    gauge_controller.add_type("Senior Tranches LP token", 10**18, {"from": admin})
    gauge_controller.add_gauge(gauge_dai, 0, 1, {"from": admin})
    gauge_controller.add_gauge(gauge_fei, 0, 1, {"from": admin})

    # alice and bob config
    (alice, bob) = (accounts[5], accounts[6])

    # transfer a different amount of IDLEs to alice and bob
    idle_token.transfer(alice, 100 * 1e18, {"from": IDLE_GOVERNABLE_FUND})
    idle_token.transfer(bob, 10 * 1e18, {"from": IDLE_GOVERNABLE_FUND})

    # alice and bob creates locks
    idle_token.approve(voting_escrow, 100 * 1e18, {"from": alice})
    voting_escrow.create_lock(100 * 1e18, 1668902400, {"from": alice})

    idle_token.approve(voting_escrow, 10 * 1e18, {"from": bob})
    voting_escrow.create_lock(10 * 1e18, 1668902400, {"from": bob})

    # vote for gauge weights
    gauge_controller.vote_for_gauge_weights(gauge_dai, 1000, {"from": alice})
    gauge_controller.vote_for_gauge_weights(gauge_fei, 1000, {"from": alice})

    # transfer DAI and FEI to alice and bob
    dai.transfer(alice, 1000 * 1e18, {"from": DAI_WHALE})
    fei.transfer(bob, 1000 * 1e18, {"from": FEI_WHALE})

    # deposit into tranches
    dai.approve(tranche_dai, 1000 * 1e18, {"from": alice})
    tranche_dai.depositAA(1000 * 1e18, {"from": alice})

    fei.approve(tranche_fei, 1000 * 1e18, {"from": bob})
    tranche_fei.depositAA(1000 * 1e18, {"from": bob})

    # stake into gauges
    aa_dai = interface.ERC20(tranche_dai.AATranche())
    aa_dai.approve(gauge_dai, aa_dai.balanceOf(alice), {"from": alice})
    gauge_dai.deposit(aa_dai.balanceOf(alice), {"from": alice})

    aa_fei = interface.ERC20(tranche_fei.AATranche())
    aa_fei.approve(gauge_fei, aa_fei.balanceOf(bob), {"from": bob})
    gauge_fei.deposit(aa_fei.balanceOf(bob), {"from": bob})

    # sleep for a while
    chain.sleep(2 * WEEK)
    chain.mine()

    assert gauge_controller.get_gauge_weight(gauge_dai) > 1
    assert gauge_controller.get_gauge_weight(gauge_fei) > 1

    # mint idles
    distributor_proxy.distribute(gauge_dai, {"from": alice})
    distributor_proxy.distribute(gauge_fei, {"from": bob})

    assert idle_token.balanceOf(alice) > 0
    assert idle_token.balanceOf(bob) > 0

    # reset IDLE balance to 0 for both bob and alice
    idle_token.transfer(admin, idle_token.balanceOf(alice), {"from": alice})
    idle_token.transfer(admin, idle_token.balanceOf(bob), {"from": bob})

    gauge_controller.vote_for_gauge_weights(gauge_dai, 0, {"from": alice})

    # sleep for a while
    chain.sleep(2 * WEEK)
    chain.mine()

    assert gauge_controller.get_gauge_weight(gauge_dai) == 1
    assert gauge_controller.get_gauge_weight(gauge_fei) > 1

    distributor_proxy.distribute(gauge_dai, {"from": alice})
    distributor_proxy.distribute(gauge_fei, {"from": bob})

    assert idle_token.balanceOf(bob) > idle_token.balanceOf(alice)

def test_e2e_rewards(
    MultiRewards,
    admin,
    accounts,
    chain,
    idle_token,
    distributor,
    distributor_proxy,
    gauge_controller,
    tranche_dai,
    gauge_dai,
    dai,
    reward_coin,
):
    # initialize distributor
    chain.mine(timedelta=86400 + 1)
    distributor.setDistributorProxy(distributor_proxy, {"from": admin})
    distributor.updateDistributionParameters({"from": admin})
    idle_token.transfer(distributor, 178_200 * 1e18, {"from": IDLE_GOVERNABLE_FUND})

    # initialize multirewards
    multirewards = MultiRewards.deploy(admin, tranche_dai.AATranche(), {"from": admin})
    multirewards.addReward(reward_coin, admin, WEEK, {"from": admin})
    reward_coin.approve(multirewards, 10_000 * 1e18, {"from": admin})
    multirewards.notifyRewardAmount(reward_coin, 10_000 * 1e18, {"from": admin})

    # gauges config
    gauge_controller.add_type("Senior Tranches LP token", 10**18, {"from": admin})
    gauge_controller.add_gauge(gauge_dai, 0, 1, {"from": admin})

    # alice
    alice = accounts[5]

    # transfer DAI to alice
    dai.transfer(alice, 1000 * 1e18, {"from": DAI_WHALE})

    # deposit into tranches
    dai.approve(tranche_dai, 1000 * 1e18, {"from": alice})
    tranche_dai.depositAA(1000 * 1e18, {"from": alice})

    # stake into gauges
    aa_dai = interface.ERC20(tranche_dai.AATranche())
    aa_dai.approve(gauge_dai, aa_dai.balanceOf(alice), {"from": alice})
    gauge_dai.deposit(aa_dai.balanceOf(alice), {"from": alice})

    # config rewards
    sigs = [
        multirewards.stake.signature[2:],
        multirewards.withdraw.signature[2:],
        multirewards.getReward.signature[2:],
    ]

    sigs = f"0x{sigs[0]}{sigs[1]}{sigs[2]}{'00' * 20}"

    gauge_dai.set_rewards(
        multirewards, sigs, [reward_coin] + [ZERO_ADDRESS] * 7, {"from": admin}
    )

    # sleep for a while
    chain.sleep(2 * WEEK)
    chain.mine()

    # claims rewards
    gauge_dai.claim_rewards({"from": alice})

    assert approx(reward_coin.balanceOf(alice), 10_000 * 1e18, 1e-2)