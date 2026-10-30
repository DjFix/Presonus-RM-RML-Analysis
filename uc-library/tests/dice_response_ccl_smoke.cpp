#include "dice_fixture_receivers.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/noaa/sysex_receiver.hpp"
#include <iostream>
#include <stdexcept>

// Independent concrete fixture: the original base accepts slot stays pure.
class NoaaFixtureReceiver final : public Presonus::NOAA::SysexReceiver {
public:
  bool accepts(const Presonus::NOAA::SysexPacket &) override { return false; }
};

template <class Receiver> class Pump final : public presonus::dice::IdlePump {
public:
  Receiver *receiver = nullptr;
  unsigned int *word = nullptr;
  unsigned calls = 0;
  void onIdle(bool) override {
    ++calls;
    receiver->portableState().command = 255;
    *word = 0x80000000U;
  }
};
template <class Receiver> static void smoke() {
  Receiver receiver;
  unsigned int response = 0;
  Pump<Receiver> pump;
  pump.receiver = &receiver;
  pump.word = &response;
  presonus::dice::CclResponseServices services(pump);
  receiver.setPortableResponseServices(services);
  const auto before = services.clockRawTicks();
  if (receiver.waitAck(0x7fffffffffffffffLL) != 255 || pump.calls < 1 ||
      pump.calls > 2)
    throw std::runtime_error("actual CCL ack clock/sleep/pump");
  const auto after = services.clockRawTicks();
  if (after < before)
    throw std::runtime_error("source monotonic clock");
  const auto priorCalls = pump.calls;
  if (!receiver.waitResponseSet(response, 0x7fffffffffffffffLL) ||
      pump.calls <= priorCalls || pump.calls > priorCalls + 2 ||
      response != 0x80000000U)
    throw std::runtime_error("actual CCL response clock/sleep/pump");
  // Actual source diagnostics are exercised with exact legacy format strings.
  services.timeoutNotice(false, 0, 0);
  services.timeoutNotice(true, 0, 0xffffffffU);
}
int main() {
  try {
    smoke<presonus::dice::fixture::ConcreteReceiver>();
    smoke<NoaaFixtureReceiver>();
    std::cout << "PASS actual CCL clock/sleep/debug with both original "
                 "namespace classes; no device I/O\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
