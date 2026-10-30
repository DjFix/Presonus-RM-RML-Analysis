#pragma once

#include "presonus/core_uc/buffer.hpp"
#include <array>
#include <cstdint>

namespace Presonus::UC {
// Explicitly portable storage. Field names, composition, constructors, original
// inheritance, class sizes and ARM object/vtable ABI are not claimed recovered.
// Original ARM common data is observed at type +0, reserved +4, routes +8/+12.
struct Event {
  std::uint32_t type = 0;
  std::uint32_t reserved04 = 0;
  std::uint32_t routeA = 0;
  std::uint32_t routeB = 0;
};

struct ParamValueEvent {
  Event header;
  std::array<char, 128> path{};
  unsigned short index = 0;
  std::array<unsigned char, 2> reserved92{};
  std::uint32_t valueBits = 0;
};

struct ParamStringEvent {
  Event header;
  std::array<char, 128> path{};
  unsigned short index = 0;
  std::array<char, 256> text{};
};

// Observed returns are 0/1; original non-template C++ return spelling is not
// encoded. These bool declarations preserve the tested portable return
// contract. Virtual EventItem dispatch and the original inheritance/vtable are
// pending.
class EventClass {
public:
  bool write(BufferWriter &writer, const Event &event) const;
  // Reader MUST already point after the tag consumed by EventFactory. This
  // reads only LE16 routeA and routeB; it never reads/validates event.type.
  bool read(Event &event, BufferReader &reader) const;
};

class ParamValueEventClass {
public:
  // Payload-only operations: path/NUL, LE16 index, four raw value bytes.
  // On failure preserve all mutations already made to the path/index/cursor.
  bool write(BufferWriter &writer, const ParamValueEvent &event) const;
  bool read(ParamValueEvent &event, BufferReader &reader) const;
};

class ParamStringEventClass {
public:
  // Payload-only: path/NUL, LE16 index, text/NUL. Bytes are not assumed UTF-8.
  bool write(BufferWriter &writer, const ParamStringEvent &event) const;
  bool read(ParamStringEvent &event, BufferReader &reader) const;
};
} // namespace Presonus::UC
