// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC2981} from "@openzeppelin/contracts/token/common/ERC2981.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Monster Certificates
/// @notice Course certificates as transferable ERC-721s. A course has a price
/// in ETH; anyone can buy its certificate (once per wallet), and the owner
/// (the MonsterBroker backend) can grant one for free to a learner who
/// finished the course. Unique, non-fractional NFTs stay outside MiCA's
/// scope; resale royalties follow EIP-2981. This is the project's first
/// path to real income, so it is deliberately simple and auditable.
contract MonsterCertificate is ERC721, ERC2981, Ownable {
    struct Course {
        uint256 price; // wei; 0 = not for sale, grant only
        string uri; // metadata shared by every certificate of this course
        bool active;
        uint256 minted;
    }

    mapping(bytes32 courseId => Course) public courses;
    mapping(uint256 tokenId => bytes32 courseId) public courseOf;
    mapping(bytes32 courseId => mapping(address holder => bool)) public certified;
    uint256 private _nextId = 1;

    event CourseSet(bytes32 indexed courseId, uint256 price, string uri, bool active);
    event Certified(address indexed to, uint256 indexed tokenId, bytes32 indexed courseId, uint256 paid);
    event Withdrawn(address indexed to, uint256 amount);

    error UnknownCourse(bytes32 courseId);
    error CourseInactive(bytes32 courseId);
    error NotForSale(bytes32 courseId);
    error WrongPrice(uint256 sent, uint256 price);
    error AlreadyCertified(address to, bytes32 courseId);
    error NothingToWithdraw();
    error WithdrawFailed();

    constructor(address owner_, address royaltyReceiver, uint96 royaltyBps)
        ERC721("Monster Certificate", "MBCERT")
        Ownable(owner_)
    {
        _setDefaultRoyalty(royaltyReceiver, royaltyBps);
    }

    // ------------------------------------------------------------ owner

    /// @notice Create or update a course. `uri` must not be empty.
    function setCourse(bytes32 courseId, uint256 price, string calldata uri, bool active) external onlyOwner {
        Course storage course = courses[courseId];
        course.price = price;
        course.uri = uri;
        course.active = active;
        emit CourseSet(courseId, price, uri, active);
    }

    function setRoyalty(address receiver, uint96 bps) external onlyOwner {
        _setDefaultRoyalty(receiver, bps);
    }

    /// @notice Certify a learner for free (they finished the course in the app).
    function grant(address to, bytes32 courseId) external onlyOwner returns (uint256) {
        _activeCourse(courseId);
        return _certify(to, courseId, 0);
    }

    function withdraw(address payable to) external onlyOwner {
        uint256 amount = address(this).balance;
        if (amount == 0) revert NothingToWithdraw();
        (bool ok,) = to.call{value: amount}("");
        if (!ok) revert WithdrawFailed();
        emit Withdrawn(to, amount);
    }

    // ----------------------------------------------------------- public

    /// @notice Buy the certificate of a course at exactly its price.
    function buy(bytes32 courseId) external payable returns (uint256) {
        Course storage course = _activeCourse(courseId);
        if (course.price == 0) revert NotForSale(courseId);
        if (msg.value != course.price) revert WrongPrice(msg.value, course.price);
        return _certify(msg.sender, courseId, msg.value);
    }

    function totalMinted() external view returns (uint256) {
        return _nextId - 1;
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        return courses[courseOf[tokenId]].uri;
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC2981) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    // ---------------------------------------------------------- private

    function _activeCourse(bytes32 courseId) private view returns (Course storage course) {
        course = courses[courseId];
        if (bytes(course.uri).length == 0) revert UnknownCourse(courseId);
        if (!course.active) revert CourseInactive(courseId);
    }

    /// @dev State first, then the mint: _safeMint calls back into a receiver contract.
    function _certify(address to, bytes32 courseId, uint256 paid) private returns (uint256 tokenId) {
        if (certified[courseId][to]) revert AlreadyCertified(to, courseId);
        certified[courseId][to] = true;
        courses[courseId].minted += 1;
        tokenId = _nextId++;
        courseOf[tokenId] = courseId;
        _safeMint(to, tokenId);
        emit Certified(to, tokenId, courseId, paid);
    }
}
