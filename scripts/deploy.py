from brownie import accounts, Distributor, DistributorProxy, GaugeController, GaugeProxy

import click

TIMELOCK = '0xD6dABBc2b275114a2366555d6C481EF08FDC2556'
TREASURY_LEAGUE = '0xFb3bD022D5DAcF95eE28a6B07825D4Ff9C5b3814'
DEVELOPER_LEAGUE = '0xe8eA8bAE250028a8709A3841E0Ae1a44820d677b'
STKIDLE = '0xaac13a116ea7016689993193fce4badc8038136f'
IDLE = '0x875773784Af8135eA0ef43b5a374AaD105c5D39e'

def main():
    deployer = click.prompt("Account", type=click.Choice(accounts.load()))

    # deploy needed contracts
    distributor = Distributor.deploy(IDLE, TREASURY_LEAGUE, DEVELOPER_LEAGUE, {'from': deployer})
    gauge_controller = GaugeController.deploy(STKIDLE, {'from': deployer})
    gauge_proxy = GaugeProxy.deploy(TIMELOCK, DEVELOPER_LEAGUE, {'from': deployer})
    distributor_proxy = DistributorProxy.deploy(distributor, gauge_controller, {'from': deployer})
    distributor.setDistributorProxy(distributor_proxy, {"from": deployer})


    # config senior tranches gauge type    
    gauge_controller.add_type(b"AATranche Gauge", 10 * 1e18, {'from': deployer})


    # change ownerships
    gauge_controller.commit_transfer_ownership(TIMELOCK, {'from': deployer})
    gauge_controller.apply_transfer_ownership({'from': deployer})
    distributor.transferOwnership(TIMELOCK, {'from': deployer})


    # publish sources
    Distributor.publish_source(distributor)
    DistributorProxy.publish_source(distributor_proxy)
    GaugeController.publish_source(gauge_controller)
    GaugeProxy.publish_source(gauge_proxy)


    # print deployed contracts 
    print(f'Distributor address: {distributor.address}')
    print(f'DistributorProxy address: {distributor_proxy.address}')
    print(f'GaugeController address: {gauge_controller.address}')
    print(f'GaugeProxy address: {gauge_proxy.address}')