#include "core/system/coredebug.h"
#include "presonus/dice/sysex.hpp"
#include "presonus/noaa/sysex_packet.hpp"
#include <cstdarg>
#include <cstdio>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {
std::string emitted;
std::int64_t ticks = 0;
unsigned clocks = 0;
std::string hex(const unsigned char *bytes, unsigned count) {
  constexpr char digits[] = "0123456789abcdef";
  std::string text;
  for (unsigned i = 0; i < count; ++i) {
    text += digits[bytes[i] >> 4];
    text += digits[bytes[i] & 15];
  }
  return text;
}
std::string hex(const std::string &text) {
  return hex(reinterpret_cast<const unsigned char *>(text.data()), text.size());
}
template <class Packet> int run(bool commands) {
  Packet packet;
  if (commands) {
    const auto *error = packet.getSysexCommandStr(0);
    for (unsigned command = 0; command < 256; ++command) {
      const auto *result = packet.getSysexCommandStr(command);
      std::cout << command << ':' << hex(std::string(result)) << ':'
                << (result == error);
      if (result == error)
        std::cout << ':'
                  << hex(reinterpret_cast<const unsigned char *>(result), 32);
      std::cout << '\n';
    }
    return 0;
  }
#ifdef PRESONUS_CAPTURE_LOGGING
  unsigned total;
  std::cin >> ticks >> total;
  for (unsigned index = 0; index < total; ++index) {
    std::string name, payload;
    unsigned length;
    std::cin >> name >> payload >> length;
    if (payload.size() != 48 || length > 255)
      return 2;
    for (unsigned i = 0; i < 24; ++i)
      packet.bytes[i] = std::stoul(payload.substr(i * 2, 2), nullptr, 16);
    packet.length = length;
    for (auto &word : packet.portableMetadata().trailingWords)
      std::cin >> word;
    emitted.clear();
    packet.log();
    std::cout << name << ' ' << hex(emitted) << ':' << clocks << '\n';
  }
#else
  packet.bytes[0] = 0xf0;
  packet.bytes[1] = 1;
  packet.bytes[2] = 0xf7;
  packet.length = 0;
  packet.log();
  std::cout << "PASS actual CCL DebugPrintf/monotonic clock source provider\n";
#endif
  return 0;
}
} // namespace

#ifdef PRESONUS_CAPTURE_LOGGING
// Test-only boundary capture. Production helper binds actual CCL DebugPrintf;
// the separate non-capture smoke executable verifies that provider.
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(Core::CStringPtr format,
                                                  ...) {
  char buffer[4096];
  va_list arguments;
  va_start(arguments, format);
  const int length = std::vsnprintf(buffer, sizeof(buffer), format, arguments);
  va_end(arguments);
  if (length < 0 || length >= int(sizeof(buffer)))
    throw std::runtime_error("capture formatter capacity");
  emitted.append(buffer, length);
}
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  ++clocks;
  return ticks;
}
} // namespace presonus::dice
#endif

int main(int argc, char **argv) {
  const bool commands = argc > 2 && std::string(argv[2]) == "commands";
  return argc > 1 && std::string(argv[1]) == "server"
             ? run<Presonus::NOAA::SysexPacket>(commands)
             : run<Presonus::DICE::SysexPacket>(commands);
}
