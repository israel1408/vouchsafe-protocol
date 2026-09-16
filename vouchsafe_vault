// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract EscrowVault is ReentrancyGuard {
    enum State { Created, Funded, Released, Refunded, Disputed }

    address public immutable factory;
    address public immutable buyer;
    address public immutable seller;
    address public immutable serverOwner;
    address public immutable protocolWallet;
    address public immutable tokenAddress; // address(0) for Native ETH

    uint256 public immutable amount;
    uint256 public immutable createdAt;
    uint256 public immutable timelockDuration;
    State public currentState;

    uint256 public constant PROTOCOL_FEE_BPS = 160; // 1.6%
    uint256 public constant SERVER_FEE_BPS = 40;   // 0.4%
    uint256 public constant BPS_DENOMINATOR = 10000;

    event VaultFunded(uint256 amount);
    event VaultReleased(uint256 sellerAmount, uint256 protocolFee, uint256 serverFee);
    event VaultRefunded();

    modifier onlyFactory() {
        require(msg.sender == factory, "Unauthorized: Only Factory");
        _;
    }

    constructor(
        address _buyer,
        address _seller,
        address _serverOwner,
        address _protocolWallet,
        address _tokenAddress,
        uint256 _amount,
        uint256 _timelockDuration
    ) {
        factory = msg.sender;
        buyer = _buyer;
        seller = _seller;
        serverOwner = _serverOwner;
        protocolWallet = _protocolWallet;
        tokenAddress = _tokenAddress;
        amount = _amount;
        timelockDuration = _timelockDuration;
        createdAt = block.timestamp;
        currentState = State.Created;
    }

    function deposit() external payable nonReentrant {
        require(currentState == State.Created, "Invalid State");
        require(msg.sender == buyer, "Only Buyer");

        if (tokenAddress == address(0)) {
            require(msg.value == amount, "Incorrect ETH Amount");
        } else {
            require(msg.value == 0, "ETH Not Accepted");
            IERC20(tokenAddress).transferFrom(msg.sender, address(this), amount);
        }

        currentState = State.Funded;
        emit VaultFunded(amount);
    }

    function release() external onlyFactory nonReentrant {
        require(currentState == State.Funded, "Funds Not Locked");

        uint256 protocolFee = (amount * PROTOCOL_FEE_BPS) / BPS_DENOMINATOR;
        uint256 serverFee = (amount * SERVER_FEE_BPS) / BPS_DENOMINATOR;
        uint256 sellerPayout = amount - protocolFee - serverFee;

        currentState = State.Released;

        if (tokenAddress == address(0)) {
            payable(seller).transfer(sellerPayout);
            payable(protocolWallet).transfer(protocolFee);
            payable(serverOwner).transfer(serverFee);
        } else {
            IERC20(tokenAddress).transfer(seller, sellerPayout);
            IERC20(tokenAddress).transfer(protocolWallet, protocolFee);
            IERC20(tokenAddress).transfer(serverOwner, serverFee);
        }

        emit VaultReleased(sellerPayout, protocolFee, serverFee);
    }

    function refund() external nonReentrant {
        require(currentState == State.Funded, "Funds Not Locked");
        require(block.timestamp >= createdAt + timelockDuration, "Timelock Active");

        currentState = State.Refunded;

        if (tokenAddress == address(0)) {
            payable(buyer).transfer(amount);
        } else {
            IERC20(tokenAddress).transfer(buyer, amount);
        }

        emit VaultRefunded();
    }
}
