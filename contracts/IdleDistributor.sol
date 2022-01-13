// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {Ownable} from "@openzeppelin/access/Ownable.sol";
import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";

/// @title IdleDistributor
/// @author dantop114
/// @notice Distribution contract that handles IDLE distribution for Idle Liquidity Gauges.
contract IdleDistributor is Ownable {
    /// Events

    /// @notice Event emitted when distributor proxy is updated
    event UpdateDistributorProxy(address oldProxy, address newProxy);

    /// @notice Event emitted when distribution parameters are updated
    ///         for upcoming distribution epoch
    event UpdatePendingDistributionParameters(uint256 time, uint256 rate);

    /// @notice Event emitted when distribution parameters are updated
    event UpdateDistributionParameters(uint256 time, uint256 rate);

    /// Immutables and constants

    /// @notice A year in seconds
    uint256 public constant YEAR = 86400 * 365;

    /// @notice Distribution rate denominator
    uint256 public constant RATE_DENOMINATOR = 10**18;

    /// @notice Initial distribution rate (as per IIP-*)
    /// @dev 356_400 IDLEs in a year leading to 178_200 IDLEs in 6 months
    uint256 public constant INITIAL_RATE = (356_400 * 10**18) / YEAR;

    /// @notice The IDLE token (the token to distribute)
    IERC20 immutable IDLE = IERC20(0x875773784Af8135eA0ef43b5a374AaD105c5D39e);

    /// Variable state

    /// @notice Distributed IDLEs so far
    uint256 public distributedIdle;

    /// @notice Running distribution epoch
    /// @dev Initiates at -1 to indicate no epoch is running
    ///      when this contract is deployed
    int128 public distributionEpoch = -1;

    /// @notice Running distribution epoch rate
    uint256 public rate;

    /// @notice Running distribution epoch starting epoch time
    uint256 public startEpochTime;

    /// @notice Total distributed IDLEs when current epoch starts
    uint256 public epochStartingDistributed;

    /// @notice Distribution rate pending for upcoming epoch
    uint256 public pendingRate = INITIAL_RATE;

    /// @notice Next distribution epoch starting timestamp
    uint256 public pendingStartEpochTime = block.timestamp;

    /// @notice The DistributorProxy contract
    address public distributorProxy;

    /// @notice Update the DistributorProxy contract
    /// @dev Only owner can call this method
    /// @param proxy New DistributorProxy contract
    function setDistributorProxy(address proxy)  external onlyOwner {
        address distributorProxy_ = distributorProxy;
        distributorProxy = proxy;

        emit UpdateDistributorProxy(distributorProxy_, proxy);
    }

    /// @notice Update pending epoch parameters
    /// @dev Only owner can call this method
    /// @param newRate Rate for upcoming epoch
    /// @param newStartEpochTime Timestamp of upcoming epoch start
    function updatePendingParams(uint256 newRate, uint256 newStartEpochTime) onlyOwner external {
        pendingRate = newRate;
        pendingStartEpochTime = newStartEpochTime;

        emit UpdatePendingDistributionParameters(newStartEpochTime, newRate);
    }

    /// @dev Updates internal state to match current epoch
    ///      distribution parameters
    function _updateDistributionParameters() internal {
        uint256 _pendingRate = pendingRate;

        rate = _pendingRate; // set new distribution rate
        startEpochTime = pendingStartEpochTime; // set start epoch timestamp
        epochStartingDistributed = distributedIdle; // set distributed IDLE to 0 when epoch begins

        pendingRate = 0; // reset pending rate
        pendingStartEpochTime = 0; // reset pending start epoch time

        emit UpdateDistributionParameters(block.timestamp, _pendingRate);
    }

    /// @notice Updates distribution rate and start timestamp of the epoch
    /// @dev Callable by anyone if pending epoch should start
    function updateDistributionParameters() external {
        require(block.timestamp >= pendingStartEpochTime, "Pending starting time not met.");
        _updateDistributionParameters();
    }

    /// @notice Get timestamp of the current distribution epoch start
    /// @return epochStartTime Timestamp of the current epoch start
    function startEpochTimeWrite() external returns(uint256 epochStartTime) {
        uint256 _pendingStartEpoch = pendingStartEpochTime;

        if(_pendingStartEpoch != 0 && block.timestamp >= _pendingStartEpoch) {
            _updateDistributionParameters();
            epochStartTime = startEpochTime;
        } else {
            epochStartTime = startEpochTime;
        }
    }

    /// @notice Get timestamp of the next distribution epoch start
    /// @return futureEpochTime Timestamp of the next epoch start
    function futureEpochTimeWrite() external returns(uint256 futureEpochTime) {
        uint256 _pendingStartEpochTime = pendingStartEpochTime;

        if(_pendingStartEpochTime != 0 && block.timestamp >= _pendingStartEpochTime) {
            _updateDistributionParameters();
            futureEpochTime = _pendingStartEpochTime;
        } else {
            futureEpochTime = startEpochTime;
        }
    }

    /// @dev Returns max available IDLEs to distribute
    function _availableToDistribute() internal view returns(uint256) {
        return distributedIdle + (block.timestamp - startEpochTime) * rate;
    }

    /// @notice Returns max available IDLEs for current distribution epoch
    function availableToDistribute() external view returns(uint256) {
        return _availableToDistribute();
    }

    /// @notice Distribute `amount` IDLE to address `to`
    /// @param to The account that will receive IDLEs
    /// @param amount The amount of IDLEs to distribute
    function distribute(address to, uint256 amount) external {
        require(msg.sender == distributorProxy, "Caller is not distributor proxy");
        require(to != address(0), "Can't distribute to address zero");

        uint256 _pendingStartEpochTime = pendingStartEpochTime;

        if(_pendingStartEpochTime != 0 && block.timestamp >= _pendingStartEpochTime) {
            _updateDistributionParameters();
        }

        uint256 _distributedIdle = distributedIdle + amount;
        require(_distributedIdle <= _availableToDistribute(), "Exceeds available to distribute");
        distributedIdle = _distributedIdle;

        IDLE.transfer(to, amount);
    }
}
