#pragma once
#include "presonus/dice/response_services.hpp"
#include "presonus/uc/DiceEndPoint.hpp"
#include "presonus/uc/DicePacketQueue.hpp"
#include "presonus/uc/connection_interfaces.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <cstdint>
#include <memory>
#include <optional>
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
// Independent interface adapter: the current DataChannel port is not an
// IDataChannel subclass. Capacity-based granularity and no-error status below
// are source-port choices, not recovered original declarations or semantics.
class UCNetEndpointChannel final : public Presonus::UC::IDataChannel {
public:
  UCNetEndpointChannel(Presonus::UC::DiceEndPoint &endpoint,
                       Presonus::UC::DicePacketQueue &incoming)
      : endpoint_(endpoint), incoming_(incoming) {}
  bool isReadable(int n) override { return endpoint_.isReadable(n) != 0; }
  int getBytesAvailable() override {
    return static_cast<int>(incoming_.getTotalBytes());
  }
  int read(void *p, int n) override {
    return static_cast<int>(endpoint_.read(p, n));
  }
  bool isWritable(int n) override { return endpoint_.isWritable(n) != 0; }
  int getGranularity() override { return incoming_.getMaxPacketSize(); }
  int write(const void *p, int n) override {
    return static_cast<int>(endpoint_.write(p, n));
  }
  bool hasErrors(int) override { return false; }

private:
  Presonus::UC::DiceEndPoint &endpoint_;
  Presonus::UC::DicePacketQueue &incoming_;
};
// Independent owning source model, not the original ARM fields. Declaration
// order is intentional: endpoint borrows both queues and dies before outgoing,
// which dies before incoming. The state view never owns its channel pointer.
struct UCNetHandlerOwnedState {
  Presonus::UC::DicePacketQueue incoming;
  Presonus::UC::DicePacketQueue outgoing;
  std::unique_ptr<Presonus::UC::DiceEndPoint> endpoint;
  std::optional<UCNetEndpointChannel> channel;
  UCNetHandlerState view;
  UCNetHandlerOwnedState(Presonus::UC::INetworkManager &network,
                         presonus::dice::ResponseServices &clock,
                         bool createEndpoint);
};
struct UCNetHandlerOwnedSetupTag {};
inline constexpr UCNetHandlerOwnedSetupTag ucNetHandlerOwnedSetupTag{};
struct UCNetHandlerSetupTag {};
inline constexpr UCNetHandlerSetupTag ucNetHandlerSetupTag{};
} // namespace presonus::noaa
