// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";
import {MonsterToken} from "../src/MonsterToken.sol";

contract MonsterTokenTest is Test {
    MonsterToken token;
    address admin = makeAddr("admin");
    address minter = makeAddr("backend");
    address learner = makeAddr("learner");
    uint256 constant CAP = 1_000 ether;

    function setUp() public {
        token = new MonsterToken(admin, minter, CAP);
    }

    function test_metadata() public view {
        assertEq(token.name(), "MonsterCoin");
        assertEq(token.symbol(), "MBK");
        assertEq(token.decimals(), 18);
        assertEq(token.cap(), CAP);
        assertTrue(token.hasRole(token.MINTER_ROLE(), minter));
        assertTrue(token.hasRole(token.DEFAULT_ADMIN_ROLE(), admin));
    }

    function test_minterCanMint() public {
        vm.prank(minter);
        token.mint(learner, 10 ether);
        assertEq(token.balanceOf(learner), 10 ether);
        assertEq(token.totalSupply(), 10 ether);
    }

    function test_othersCannotMint() public {
        bytes32 role = token.MINTER_ROLE(); // read it first: an external call would eat the prank
        vm.prank(learner);
        vm.expectRevert(abi.encodeWithSelector(IAccessControl.AccessControlUnauthorizedAccount.selector, learner, role));
        token.mint(learner, 1 ether);
    }

    function test_capIsEnforced() public {
        vm.startPrank(minter);
        token.mint(learner, CAP);
        vm.expectRevert(abi.encodeWithSelector(MonsterToken.CapExceeded.selector, 1, 0));
        token.mint(learner, 1);
        vm.stopPrank();
    }

    function test_burnFreesCap() public {
        vm.prank(minter);
        token.mint(learner, CAP);
        vm.prank(learner);
        token.burn(400 ether);
        assertEq(token.totalSupply(), 600 ether);
        vm.prank(minter);
        token.mint(learner, 400 ether); // room again
        assertEq(token.totalSupply(), CAP);
    }

    function test_zeroCapRejected() public {
        vm.expectRevert(MonsterToken.ZeroCap.selector);
        new MonsterToken(admin, minter, 0);
    }

    function testFuzz_mintWithinCap(uint256 amount) public {
        amount = bound(amount, 0, CAP);
        vm.prank(minter);
        token.mint(learner, amount);
        assertEq(token.balanceOf(learner), amount);
    }
}
