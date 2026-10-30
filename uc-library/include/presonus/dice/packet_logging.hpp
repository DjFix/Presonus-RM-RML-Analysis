#pragma once
#include <array>
#include <cstdint>

namespace presonus::dice {
using PacketCommandName = const char *(*)(const void *, unsigned char);
// Independent shared helper; original namespaces retain their own methods and
// function-local started values. All 24 payload bytes must be initialized.
void logPacket(const unsigned char *bytes,
               const std::array<std::uint32_t, 4> &timestamps,
               std::int64_t started, const void *context,
               PacketCommandName commandName);
} // namespace presonus::dice
