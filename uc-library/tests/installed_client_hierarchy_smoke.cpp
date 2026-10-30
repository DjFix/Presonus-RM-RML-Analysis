#include "dice_fixture_receivers.hpp"
#include "presonus/dice/sysex.hpp"
#include "smoke_common.hpp"
#include <iostream>

class ClientPump final : public presonus::dice::IdlePump {
public:
  Presonus::DICE::SysexReceiver &receiver;
  unsigned int &response;
  unsigned calls = 0;
  ClientPump(Presonus::DICE::SysexReceiver &r, unsigned int &word)
      : receiver(r), response(word) {}
  void onIdle(bool force) override {
    require(!force, "DICE has no forced SPI pump");
    ++calls;
    receiver.portableState().command = 0xff;
    response = 0x80000000U;
  }
};
int main() {
  try {
    commonSmoke();
    const unsigned char bytes[] = {0xf0, 1, 0xf7};
    Presonus::DICE::SysexPacket packet(bytes, 3);
    require(packet.length == 3 && packet.bytes[1] == 1,
            "actual DICE constructor/clock gateway");
    presonus::dice::fixture::ConcreteReceiver receiver;
    unsigned int response = 0;
    ClientPump pump(receiver, response);
    presonus::dice::CclResponseServices services(pump);
    receiver.setPortableResponseServices(services);
    require(receiver.waitAck(0x7fffffffffffffffLL) == 0xff && pump.calls,
            "DICE role wait with actual Core clock/sleep");
    require(receiver.waitResponseSet(response, 0x7fffffffffffffffLL) &&
                response == 0x80000000U,
            "DICE response wait");
    std::cout << "PASS real CS18 component archive and shared UC/AVB/CCL\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
