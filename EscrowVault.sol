// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract EscrowVault is ReentrancyGuard {
    enum VaultState { AwaitingDeposit, FundsLocked, Released, Refunded }

    IERC20 public immutable usdcToken;
    address public immutable factory;
    address public immutable buyer;
    address public immutable seller;
    address public immutable platformFeeRecipient;
    
    uint256 public immutable amountUSDC;
    VaultState public state;

    uint256 public constant SELLER_BPS = 9800;      // 98.0%
    uint256 public constant PLATFORM_BPS = 160;     // 1.6%
    uint256 public constant TREASURY_BPS = 40;      // 0.4%
    address public immutable treasuryRecipient;

    event VaultFunded(uint256 amount);
    event VaultReleased(uint256 sellerAmount, uint256 platformFee, uint256 treasuryFee);
    event VaultRefunded(uint256 amount);

    modifier onlyBuyer() {
        require(msg.sender == buyer, "EscrowVault: Only buyer can call");
        _;
    }

    modifier onlyFactoryOrBuyer() {
        require(msg.sender == buyer || msg.sender == factory, "EscrowVault: Unauthorized");
        _;
    }

    constructor(
        address _usdcToken,
        address _buyer,
        address _seller,
        uint256 _amountUSDC,
        address _platformFeeRecipient,
        address _treasuryRecipient
    ) {
        usdcToken = IERC20(_usdcToken);
        factory = msg.sender;
        buyer = _buyer;
        seller = _seller;
        amountUSDC = _amountUSDC;
        platformFeeRecipient = _platformFeeRecipient;
        treasuryRecipient = _treasuryRecipient;
        state = VaultState.AwaitingDeposit;
    }

    /// @notice Buyer calls this to fund the vault with USDC
    function fundVault() external nonReentrant {
        require(state == VaultState.AwaitingDeposit, "EscrowVault: Invalid state");
        require(msg.sender == buyer, "EscrowVault: Only buyer can fund");

        state = VaultState.FundsLocked;
        require(
            usdcToken.transferFrom(msg.sender, address(this), amountUSDC),
            "EscrowVault: USDC transfer failed"
        );

        emit VaultFunded(amountUSDC);
    }

    /// @notice Releases funds according to fee splits upon completion
    function releaseFunds() external onlyFactoryOrBuyer nonReentrant {
        require(state == VaultState.FundsLocked, "EscrowVault: Funds not locked");

        state = VaultState.Released;

        uint256 sellerPayout = (amountUSDC * SELLER_BPS) / 10000;
        uint256 platformFee = (amountUSDC * PLATFORM_BPS) / 10000;
        uint256 treasuryFee = amountUSDC - sellerPayout - platformFee;

        require(usdcToken.transfer(seller, sellerPayout), "EscrowVault: Seller payout failed");
        require(usdcToken.transfer(platformFeeRecipient, platformFee), "EscrowVault: Platform fee failed");
        require(usdcToken.transfer(treasuryRecipient, treasuryFee), "EscrowVault: Treasury fee failed");

        emit VaultReleased(sellerPayout, platformFee, treasuryFee);
    }

    /// @notice Refunds buyer in case of dispute cancellation
    function refundBuyer() external onlyFactoryOrBuyer nonReentrant {
        require(state == VaultState.FundsLocked, "EscrowVault: Funds not locked");

        state = VaultState.Refunded;
        require(usdcToken.transfer(buyer, amountUSDC), "EscrowVault: Refund failed");

        emit VaultRefunded(amountUSDC);
    }
}
