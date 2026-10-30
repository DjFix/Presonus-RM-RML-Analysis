#include "../../portable/dice/ProgrammerBuffers.hpp"
#include "presonus/dice/programmer.hpp"
#include <cassert>

namespace Presonus::DICE {
std::int32_t Dice3Programmer::performTransaction(mp25Transaction transaction) {
  assert(services_ != nullptr);
  const presonus::dice::ProgrammerTransfer transfer{
      transaction.portableTransmit, transaction.portableTransmitLength,
      transaction.portableReceive, transaction.portableReceiveLength};
  return services_->transfer(state_.descriptor, transfer) < 0 ? -3 : 0;
}

std::int32_t Dice3Programmer::writeEnable() {
  const unsigned char command = 0x06;
  return performTransaction(
      {&command, 1, presonus::dice::detail::programmerBuffers().receive.data(),
       0});
}

std::int32_t Dice3Programmer::readJedecId() {
  const unsigned char command = 0x9f;
  const auto result = performTransaction(
      {&command, 1, presonus::dice::detail::programmerBuffers().receive.data(),
       3});
  return result != 0
             ? 0xffff
             : (static_cast<std::int32_t>(
                    presonus::dice::detail::programmerBuffers().receive[2])
                << 8) |
                   presonus::dice::detail::programmerBuffers().receive[3];
}

std::int32_t Dice3Programmer::busyWait(int timeout) {
  assert(services_ != nullptr);
  auto now = services_->clockRawTicks() / 1000000;
  // Raw signed64 ticks divided by1e6 plus int32 timeout cannot overflow int64.
  const std::int64_t deadline = now + timeout;
  while (now < deadline) {
    const unsigned char command = 0x05;
    const auto result = performTransaction(
        {&command, 1,
         presonus::dice::detail::programmerBuffers().receive.data(), 1});
    if (result != 0)
      return result;
    if ((presonus::dice::detail::programmerBuffers().receive[1] & 1) == 0)
      return 0;
    services_->sleepMilliseconds(1);
    now = services_->clockRawTicks() / 1000000;
  }
  return -2;
}
} // namespace Presonus::DICE
