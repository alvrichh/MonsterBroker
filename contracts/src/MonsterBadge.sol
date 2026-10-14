// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC721URIStorage} from "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Monster Badges
/// @notice Soulbound ERC-721 achievement badges: proof of what a learner did
/// (first bot tick, futures glossary, a week of reading the radar...). Minted
/// only by MINTER_ROLE, one badge of each kind per wallet, never transferable;
/// the owner may burn it.
contract MonsterBadge is ERC721, ERC721URIStorage, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    uint256 private _nextId = 1;

    /// @notice kind => wallet => already awarded. Burning does not reset it:
    /// a badge is earned once.
    mapping(bytes32 kind => mapping(address wallet => bool)) public awarded;

    event BadgeAwarded(address indexed to, uint256 indexed tokenId, bytes32 indexed kind, string uri);

    error Soulbound();
    error AlreadyAwarded(address to, bytes32 kind);
    error NotOwner(uint256 tokenId, address caller);

    constructor(address admin, address minter) ERC721("Monster Badges", "MBADGE") {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, minter);
    }

    /// @notice Award a badge of `kind` (e.g. keccak256("first_tick")) with its metadata URI.
    function award(address to, bytes32 kind, string calldata uri)
        external
        onlyRole(MINTER_ROLE)
        returns (uint256 tokenId)
    {
        if (awarded[kind][to]) revert AlreadyAwarded(to, kind);
        awarded[kind][to] = true;
        tokenId = _nextId++;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, uri);
        emit BadgeAwarded(to, tokenId, kind, uri);
    }

    /// @notice Owners may renounce a badge.
    function burn(uint256 tokenId) external {
        if (ownerOf(tokenId) != msg.sender) revert NotOwner(tokenId, msg.sender);
        _burn(tokenId);
    }

    /// @notice How many badges have been minted so far.
    function totalMinted() external view returns (uint256) {
        return _nextId - 1;
    }

    /// @dev Soulbound: only minting (from == 0) and burning (to == 0) may move a token.
    function _update(address to, uint256 tokenId, address auth) internal override returns (address) {
        address from = _ownerOf(tokenId);
        if (from != address(0) && to != address(0)) revert Soulbound();
        return super._update(to, tokenId, auth);
    }

    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
