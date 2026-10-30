#pragma once

// These are original GLOBAL helper symbols used by DICE. Do not relocate them
// into Presonus::DICE. Widths/return spellings are portable choices preserving
// observed numeric output; no ARM calling-ABI claim is made.
unsigned int unpack32(const unsigned char *bytes);
unsigned short unpack16(const unsigned char *bytes);

// Compiled output-only ports. Original void-versus-value return declarations
// are unresolved, so these packers remain declaration-pending, NOT READY.
void pack32(unsigned int value, unsigned char *bytes);
void pack16(unsigned short value, unsigned char *bytes);
