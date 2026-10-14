// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {MonsterToken} from "../src/MonsterToken.sol";
import {MonsterBadge} from "../src/MonsterBadge.sol";

/// Deploys MonsterCoin and Monster Badges.
///
///   ADMIN   address that can grant/revoke roles (defaults to the deployer)
///   MINTER  the MonsterBroker backend's wallet (defaults to the deployer)
///   TOKEN_CAP  in whole tokens (default 100,000,000 MBK)
///
///   forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast --verify -vvvv
contract Deploy is Script {
    function run() external {
        address deployer = msg.sender;
        address admin = vm.envOr("ADMIN", deployer);
        address minter = vm.envOr("MINTER", deployer);
        uint256 cap = vm.envOr("TOKEN_CAP", uint256(100_000_000)) * 1 ether;

        vm.startBroadcast();
        MonsterToken token = new MonsterToken(admin, minter, cap);
        MonsterBadge badge = new MonsterBadge(admin, minter);
        vm.stopBroadcast();

        console.log("MonsterToken (MBK):", address(token));
        console.log("MonsterBadge:      ", address(badge));
        console.log("admin:", admin);
        console.log("minter:", minter);
    }
}
