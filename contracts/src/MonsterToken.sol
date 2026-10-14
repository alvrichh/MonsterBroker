// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title MonsterCoin (MBK)
/// @notice The learning token of MonsterBroker. It is earned by completing
/// lessons and challenges and spent on unlocking content; it is not sold.
/// Only addresses with MINTER_ROLE (the MonsterBroker backend) can mint, and
/// never past the cap. Anyone can burn their own tokens.
contract MonsterToken is ERC20, ERC20Permit, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    /// @notice Hard ceiling on total supply, fixed at deployment.
    uint256 public immutable cap;

    error CapExceeded(uint256 requested, uint256 available);
    error ZeroCap();

    constructor(address admin, address minter, uint256 cap_)
        ERC20("MonsterCoin", "MBK")
        ERC20Permit("MonsterCoin")
    {
        if (cap_ == 0) revert ZeroCap();
        cap = cap_;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, minter);
    }

    /// @notice Mint rewards to a learner. Reverts past the cap.
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        uint256 available = cap - totalSupply();
        if (amount > available) revert CapExceeded(amount, available);
        _mint(to, amount);
    }

    /// @notice Burn your own tokens (e.g. to redeem a reward off-chain).
    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }
}
