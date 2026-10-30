#pragma once
#include "presonus/dice/packet_services.hpp"
#include <array>

namespace Presonus::NOAA {
// Independent portable seeded state, not the original ARM object layout or
// constructor. Ordinary return spellings remain unencoded in original symbols.
class SysexPacket {
public:
  SysexPacket() = default;
  SysexPacket(const unsigned char *data, unsigned char size);
  std::array<unsigned char, 256> bytes{};
  unsigned char length = 0;
  presonus::dice::PacketMetadata &portableMetadata() { return metadata_; }
  const presonus::dice::PacketMetadata &portableMetadata() const {
    return metadata_;
  }
  const char *getSysexCommandStr(unsigned char command) const;
  // CANDIDATE void: original return declaration is pending.
  void log() const;

private:
  presonus::dice::PacketMetadata metadata_;
};
} // namespace Presonus::NOAA
