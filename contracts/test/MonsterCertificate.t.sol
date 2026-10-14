// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC2981} from "@openzeppelin/contracts/interfaces/IERC2981.sol";
import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {MonsterCertificate} from "../src/MonsterCertificate.sol";

contract MonsterCertificateTest is Test {
    MonsterCertificate cert;
    address owner = makeAddr("owner");
    address treasury = makeAddr("treasury");
    address alice = makeAddr("alice");
    address bob = makeAddr("bob");
    bytes32 constant FUTURES = keccak256("futures-101");
    string constant URI = "https://monsterbroker.example/api/certificates/futures-101";
    uint256 constant PRICE = 0.01 ether;

    function setUp() public {
        cert = new MonsterCertificate(owner, treasury, 500); // 5% royalty
        vm.prank(owner);
        cert.setCourse(FUTURES, PRICE, URI, true);
        vm.deal(alice, 1 ether);
        vm.deal(bob, 1 ether);
    }

    function test_metadataAndRoyalty() public view {
        assertEq(cert.name(), "Monster Certificate");
        assertEq(cert.symbol(), "MBCERT");
        (address receiver, uint256 amount) = cert.royaltyInfo(1, 1 ether);
        assertEq(receiver, treasury);
        assertEq(amount, 0.05 ether);
        assertTrue(cert.supportsInterface(type(IERC2981).interfaceId));
        assertTrue(cert.supportsInterface(type(IERC721).interfaceId));
    }

    function test_buyMintsAndKeepsTheEth() public {
        vm.prank(alice);
        vm.expectEmit(true, true, true, true);
        emit MonsterCertificate.Certified(alice, 1, FUTURES, PRICE);
        uint256 id = cert.buy{value: PRICE}(FUTURES);
        assertEq(id, 1);
        assertEq(cert.ownerOf(1), alice);
        assertEq(cert.tokenURI(1), URI);
        assertEq(cert.courseOf(1), FUTURES);
        assertEq(address(cert).balance, PRICE);
        assertTrue(cert.certified(FUTURES, alice));
        (,,, uint256 minted) = cert.courses(FUTURES);
        assertEq(minted, 1);
        assertEq(cert.totalMinted(), 1);
    }

    function test_exactPriceRequired() public {
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(MonsterCertificate.WrongPrice.selector, PRICE - 1, PRICE));
        cert.buy{value: PRICE - 1}(FUTURES);
    }

    function test_oneCertificatePerCoursePerWallet() public {
        vm.startPrank(alice);
        cert.buy{value: PRICE}(FUTURES);
        vm.expectRevert(abi.encodeWithSelector(MonsterCertificate.AlreadyCertified.selector, alice, FUTURES));
        cert.buy{value: PRICE}(FUTURES);
        vm.stopPrank();
    }

    function test_unknownAndInactiveCourses() public {
        bytes32 nope = keccak256("nope");
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(MonsterCertificate.UnknownCourse.selector, nope));
        cert.buy{value: PRICE}(nope);

        vm.prank(owner);
        cert.setCourse(FUTURES, PRICE, URI, false);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(MonsterCertificate.CourseInactive.selector, FUTURES));
        cert.buy{value: PRICE}(FUTURES);
    }

    function test_grantIsFreeAndOwnerOnly() public {
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, alice));
        cert.grant(bob, FUTURES);

        vm.prank(owner);
        uint256 id = cert.grant(bob, FUTURES);
        assertEq(cert.ownerOf(id), bob);
        assertEq(address(cert).balance, 0);
    }

    function test_grantOnlyCourse() public {
        bytes32 glossary = keccak256("glossary");
        vm.prank(owner);
        cert.setCourse(glossary, 0, URI, true);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(MonsterCertificate.NotForSale.selector, glossary));
        cert.buy{value: 0}(glossary);
        vm.prank(owner);
        cert.grant(alice, glossary);
        assertEq(cert.balanceOf(alice), 1);
    }

    function test_certificatesAreTransferable() public {
        vm.prank(alice);
        cert.buy{value: PRICE}(FUTURES);
        vm.prank(alice);
        cert.transferFrom(alice, bob, 1);
        assertEq(cert.ownerOf(1), bob);
    }

    function test_withdraw() public {
        vm.prank(alice);
        cert.buy{value: PRICE}(FUTURES);

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, alice));
        cert.withdraw(payable(alice));

        vm.prank(owner);
        cert.withdraw(payable(treasury));
        assertEq(treasury.balance, PRICE);
        assertEq(address(cert).balance, 0);

        vm.prank(owner);
        vm.expectRevert(MonsterCertificate.NothingToWithdraw.selector);
        cert.withdraw(payable(treasury));
    }
}
