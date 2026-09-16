// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./EscrowVault.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract EscrowVaultFactory is Ownable {
    address public protocolWallet;
    address public oracleWorker; // Off-chain bot/backend authorized to trigger payouts

    mapping(bytes32 => address) public ticketToVault;
    address[] public allVaults;

    event VaultCreated(
        bytes32 indexed ticketId,
        address vaultAddress,
        address indexed buyer,
        address indexed seller,
        address serverOwner,
        uint256 amount
    );
    event VaultReleasedByOracle(bytes32 indexed ticketId, address vaultAddress);

    modifier onlyOracle() {
        require(msg.sender == oracleWorker, "Unauthorized: Only Oracle Worker");
        _;
    }

    constructor(address _protocolWallet, address _oracleWorker) Ownable(msg.sender) {
        protocolWallet = _protocolWallet;
        oracleWorker = _oracleWorker;
    }

    function createVault(
        bytes32 ticketId,
        address buyer,
        address seller,
        address serverOwner,
        address tokenAddress,
        uint256 amount,
        uint256 timelockDuration
    ) external returns (address) {
        require(ticketToVault[ticketId] == address(0), "Vault already exists for ticket");

        EscrowVault vault = new EscrowVault(
            buyer,
            seller,
            serverOwner,
            protocolWallet,
            tokenAddress,
            amount,
            timelockDuration
        );

        address vaultAddress = address(vault);
        ticketToVault[ticketId] = vaultAddress;
        allVaults.push(vaultAddress);

        emit VaultCreated(ticketId, vaultAddress, buyer, seller, serverOwner, amount);
        return vaultAddress;
    }

    function triggerRelease(bytes32 ticketId) external onlyOracle {
        address vaultAddress = ticketToVault[ticketId];
        require(vaultAddress != address(0), "Vault does not exist");

        EscrowVault(vaultAddress).release();
        emit VaultReleasedByOracle(ticketId, vaultAddress);
    }

    function setProtocolWallet(address _newWallet) external onlyOwner {
        protocolWallet = _newWallet;
    }

    function setOracleWorker(address _newOracle) external onlyOwner {
        oracleWorker = _newOracle;
    }
}
