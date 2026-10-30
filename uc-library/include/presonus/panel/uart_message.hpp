#pragma once
#include <array>
#include <cstdint>

// Original GLOBAL tag identity; portable byte view only. The observed codec
// addresses offsets0..3 (LE16 at2). Original union/member names, full sizeof,
// alignment and original C declarations are not established by these bytes.
struct Uart_Msg_Type {
  std::array<std::uint8_t, 4> bytes;
};

// Exact C symbol names, portable parameter/return choices; original prototypes
// remain declaration-pending. Input/output aliasing is outside the proof
// domain. Decoder caller must provide readable prefix2 bytes as well as length
// bytes; original length0 and short-K paths read before the nominal input
// pointer.
extern "C" std::uint32_t utils_Ascii2Int(const char *, int);
extern "C" std::uint32_t utils_ConvertInt2Hex(std::uint32_t, std::uint32_t,
                                              char *, std::uint32_t);
extern "C" int uart_protocol_encode(const Uart_Msg_Type *, char *);
extern "C" int uart_protocol_decode(const char *, unsigned, Uart_Msg_Type *);
