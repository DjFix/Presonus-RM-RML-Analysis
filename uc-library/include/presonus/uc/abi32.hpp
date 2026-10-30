#pragma once
#include <cstddef>
#include <cstdint>

namespace presonus::uc::recovered::abi32 {
// Observed data offsets in RM/RML 13731. For binary inspection only.
// The meaning of offset 4 is unknown; these are not complete original class
// definitions. No host pointer, vtable, allocation, ownership or original
// calling ABI is asserted.
struct EventImage {
  std::uint32_t type;
  std::uint32_t unknown_04;
  std::uint32_t route_a;
  std::uint32_t route_b;
};
// ParamValueEventClass::write: path +0x10, index +0x90, float bits +0x94.
struct ParamValueEventImage {
  EventImage event;
  char path[128];
  std::uint16_t index;
  std::uint8_t padding_92[2];
  std::uint32_t value_bits;
};
static_assert(sizeof(EventImage) == 0x10);
static_assert(offsetof(ParamValueEventImage, path) == 0x10);
static_assert(offsetof(ParamValueEventImage, index) == 0x90);
static_assert(offsetof(ParamValueEventImage, value_bits) == 0x94);
static_assert(sizeof(ParamValueEventImage) == 0x98);
} // namespace presonus::uc::recovered::abi32
