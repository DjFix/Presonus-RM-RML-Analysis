#include "presonus/dice/codec.hpp"
#include "presonus/dice/subsystem_runtime.hpp"
#include "presonus/dice/sysex.hpp"
#include <stdexcept>
namespace Presonus::DICE {
void Dice3Subsystem::resetDice3() {
  if (!runtime_)
    throw std::logic_error("Dice3Subsystem runtime is required for reset");
  auto pin = runtime_->makeResetPin();
  if (!pin)
    throw std::logic_error("Dice3Subsystem reset provider returned no pin");
  pin->set(0);
  runtime_->sleepMilliseconds(1);
  pin->set(1);
}
std::int32_t Dice3Subsystem::programSerialData(unsigned int serial,
                                               unsigned char unit) {
  if (!runtime_ || !services_)
    throw std::logic_error(
        "Dice3Subsystem runtime is required for serial programming");
  unsigned char data[] = {0xf0, 9, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xf7};
  pack32(serial, data + 2);
  pack32(serial, data + 7);
  data[12] = unit;
  SysexPacket packet(data, 14);
  services_->post(packet);
  runtime_->sleepMilliseconds(2000);
  if (services_->waitAck(*this, 500) == 0)
    return -11;
  return snapshotPortableState().status == 1 ? 0 : -4;
}
} // namespace Presonus::DICE
