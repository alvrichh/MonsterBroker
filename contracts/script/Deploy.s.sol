// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {MonsterToken} from "../src/MonsterToken.sol";
import {MonsterBadge} from "../src/MonsterBadge.sol";
import {MonsterCertificate} from "../src/MonsterCertificate.sol";

/// Deploys MonsterCoin, Monster Badges and Monster Certificates.
///
///   ADMIN        address that can grant/revoke roles and owns the certificates (defaults to the deployer)
///   MINTER       the MonsterBroker backend's wallet (defaults to the deployer)
///   TOKEN_CAP    in whole tokens (default 100,000,000 MBK)
///   TREASURY     where certificate royalties go (defaults to ADMIN)
///   ROYALTY_BPS  resale royalty in basis points (default 500 = 5%)
///
///   forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast --verify -vvvv
contract Deploy is Script {
    function run() external {
        address deployer = msg.sender;
        address admin = vm.envOr("ADMIN", deployer);
        address minter = vm.envOr("MINTER", deployer);
        uint256 cap = vm.envOr("TOKEN_CAP", uint256(100_000_000)) * 1 ether;
        address treasury = vm.envOr("TREASURY", admin);
        uint96 royaltyBps = uint96(vm.envOr("ROYALTY_BPS", uint256(500)));

        vm.startBroadcast();
        MonsterToken token = new MonsterToken(admin, minter, cap);
        MonsterBadge badge = new MonsterBadge(admin, minter);
        MonsterCertificate certificate = new MonsterCertificate(admin, treasury, royaltyBps);
        vm.stopBroadcast();

        console.log("MonsterToken (MBK):  ", address(token));
        console.log("MonsterBadge:        ", address(badge));
        console.log("MonsterCertificate:  ", address(certificate));
        console.log("admin:", admin);
        console.log("minter:", minter);
        console.log("treasury:", treasury);
    }
}
