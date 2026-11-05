#pragma once
#include "presonus/dice/response_services.hpp"
#include "presonus/uc/DicePacketQueue.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <cstdint>
namespace presonus::noaa {
// Independent required borrowed state. All dependencies outlive use and the
// caller serializes access. No original layout, default setup or ownership
// claim.
struct UCNetHandlerState {
  Presonus::UC::DicePacketQueue &incoming;
  Presonus::UC::INetworkManager &network;
  presonus::dice::ResponseServices &clock;
  Presonus::UC::IConnection *connection;
  Presonus::UC::IDataChannel *channel;
  unsigned char observedByte8;
  std::uint32_t observedWord60;
  std::int64_t observedTicks70;
  // Separate native queue at +0x34; incoming receive queue is at +0xc.
  // Required for idleIO handshake; caller binds a distinct live queue.
  Presonus::UC::DicePacketQueue *outgoing = nullptr;
  std::uint64_t observedTicks68 = 0;
};
struct UCNetHandlerSetupTag {};
inline constexpr UCNetHandlerSetupTag ucNetHandlerSetupTag{};
} // namespace presonus::noaa
