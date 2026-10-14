// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";
import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {MonsterBadge} from "../src/MonsterBadge.sol";

contract MonsterBadgeTest is Test {
    MonsterBadge badge;
    address admin = makeAddr("admin");
    address minter = makeAddr("backend");
    address learner = makeAddr("learner");
    address other = makeAddr("other");
    bytes32 constant FIRST_TICK = keccak256("first_tick");
    string constant URI = "ipfs://bafy.../first_tick.json";

    function setUp() public {
        badge = new MonsterBadge(admin, minter);
    }

    function test_awardMintsWithUriAndEvent() public {
        vm.prank(minter);
        vm.expectEmit(true, true, true, true);
        emit MonsterBadge.BadgeAwarded(learner, 1, FIRST_TICK, URI);
        uint256 id = badge.award(learner, FIRST_TICK, URI);
        assertEq(id, 1);
        assertEq(badge.ownerOf(1), learner);
        assertEq(badge.tokenURI(1), URI);
        assertEq(badge.totalMinted(), 1);
        assertTrue(badge.awarded(FIRST_TICK, learner));
    }

    function test_oneBadgeOfEachKindPerWallet() public {
        vm.startPrank(minter);
        badge.award(learner, FIRST_TICK, URI);
        vm.expectRevert(abi.encodeWithSelector(MonsterBadge.AlreadyAwarded.selector, learner, FIRST_TICK));
        badge.award(learner, FIRST_TICK, URI);
        badge.award(learner, keccak256("glossary"), URI); // a different kind is fine
        vm.stopPrank();
        assertEq(badge.balanceOf(learner), 2);
    }

    function test_othersCannotAward() public {
        bytes32 role = badge.MINTER_ROLE(); // read it first: an external call would eat the prank
        vm.prank(other);
        vm.expectRevert(abi.encodeWithSelector(IAccessControl.AccessControlUnauthorizedAccount.selector, other, role));
        badge.award(learner, FIRST_TICK, URI);
    }

    function test_soulbound() public {
        vm.prank(minter);
        badge.award(learner, FIRST_TICK, URI);
        vm.startPrank(learner);
        vm.expectRevert(MonsterBadge.Soulbound.selector);
        badge.transferFrom(learner, other, 1);
        vm.expectRevert(MonsterBadge.Soulbound.selector);
        badge.safeTransferFrom(learner, other, 1);
        vm.stopPrank();
    }

    function test_ownerCanBurnButNotReearn() public {
        vm.prank(minter);
        badge.award(learner, FIRST_TICK, URI);
        vm.prank(other);
        vm.expectRevert(abi.encodeWithSelector(MonsterBadge.NotOwner.selector, 1, other));
        badge.burn(1);
        vm.prank(learner);
        badge.burn(1);
        assertEq(badge.balanceOf(learner), 0);
        vm.prank(minter);
        vm.expectRevert(abi.encodeWithSelector(MonsterBadge.AlreadyAwarded.selector, learner, FIRST_TICK));
        badge.award(learner, FIRST_TICK, URI);
    }

    function test_supportsInterfaces() public view {
        assertTrue(badge.supportsInterface(type(IERC721).interfaceId));
        assertTrue(badge.supportsInterface(type(IAccessControl).interfaceId));
    }
}
