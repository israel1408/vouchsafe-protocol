// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./EscrowVault.sol";

contract VaultFactory is Ownable {
    address public usdcToken;
    address public platformFeeRecipient;
    address public treasuryRecipient;

    mapping(bytes32 => address) public getVaultByTicket;
    address[] public allVaults;

    event VaultCreated(
        bytes32 indexed ticketId,
        address vaultAddress,
        address indexed buyer,
        address indexed seller,
        uint256 amount
    );

    constructor(
        address _usdcToken,
        address _platformFeeRecipient,
        address _treasuryRecipient
    ) Ownable(msg.sender) {
        usdcToken = _usdcToken;
        platformFeeRecipient = _platformFeeRecipient;
        treasuryRecipient = _treasuryRecipient;
    }

    function createVault(
        string calldata ticketIdStr,
        address seller,
        uint256 amountUSDC
    ) external returns (address vaultAddress) {
        bytes32 ticketId = keccak256(abi.encodePacked(ticketIdStr));
        require(getVaultByTicket[ticketId] == address(0), "VaultFactory: Ticket already exists");

        EscrowVault newVault = new EscrowVault(
            usdcToken,
            msg.sender, // Buyer
            seller,
            amountUSDC,
            platformFeeRecipient,
            treasuryRecipient
        );

        vaultAddress = address(newVault);
        getVaultByTicket[ticketId] = vaultAddress;
        allVaults.push(vaultAddress);

        emit VaultCreated(ticketId, vaultAddress, msg.sender, seller, amountUSDC);
    }

    function updateFeeRecipients(address _platformFee, address _treasury) external onlyOwner {
        platformFeeRecipient = _platformFee;
        treasuryRecipient = _treasury;
    }
}
