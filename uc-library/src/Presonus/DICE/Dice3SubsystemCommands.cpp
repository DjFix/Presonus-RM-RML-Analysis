#include "../../portable/dice/ReceiverStateGuard.hpp"
#include "presonus/dice/codec.hpp"
#include "presonus/dice/sysex.hpp"
#include <cstring>
static_assert(sizeof(int) == 4);

namespace {
int integerWord(std::uint32_t word) {
  int value;
  std::memcpy(&value, &word, 4);
  return value;
}
} // namespace
namespace Presonus::DICE {
std::int32_t Dice3Subsystem::uiSetCmd(int rate, int clock) {
  if (static_cast<std::uint32_t>(rate) > 3U)
    return -5;
  const unsigned char data[] = {0xf0, 0x11, static_cast<unsigned char>(rate),
                                static_cast<unsigned char>(clock), 0xf7};
  SysexPacket packet(data, 5);
  services_->post(packet);
  if (services_->waitAck(*this, 500) == 0)
    return -11;
  return snapshotPortableState().status == 1 ? 0 : -4;
}
std::int32_t Dice3Subsystem::setRate(Dice3SampleRate rate) {
  const auto word = static_cast<std::uint32_t>(rate);
  std::uint32_t clock;
  {
    presonus::dice::ReceiverStateGuard guard(portableStateLock_);
    if (state_.rateWord == word)
      return 0;
    state_.rateWord = word;
    clock = state_.clockWord;
  }
  return uiSetCmd(integerWord(word), integerWord(clock));
}
std::int32_t Dice3Subsystem::setClockSource(Dice3ClockSource clock) {
  const auto word = static_cast<std::uint32_t>(clock);
  std::uint32_t rate;
  {
    presonus::dice::ReceiverStateGuard guard(portableStateLock_);
    if (state_.clockWord == word)
      return 0;
    state_.clockWord = word;
    rate = state_.rateWord;
  }
  return uiSetCmd(integerWord(rate), integerWord(word));
}
std::int32_t Dice3Subsystem::setRoute(Dice3AudioSinkDevice sinkDevice,
                                      Dice3AudioSink sink,
                                      Dice3AudioSourceDevice sourceDevice,
                                      Dice3AudioSource source) {
  const unsigned char data[] = {0xf0,
                                0x16,
                                static_cast<unsigned char>(sinkDevice),
                                static_cast<unsigned char>(sink),
                                static_cast<unsigned char>(sourceDevice),
                                static_cast<unsigned char>(source),
                                0xf7};
  SysexPacket packet(data, 7);
  services_->post(packet);
  if (services_->waitAck(*this, 500) == 0)
    return -11;
  return snapshotPortableState().status == 1 ? 0 : -4;
}
void Dice3Subsystem::receive(const SysexPacket &packet) {
  const auto command = packet.length > 1 ? packet.bytes[1] : 0;
  const auto status = packet.bytes[2];
  const bool hasInfo = packet.length > 1 && packet.bytes[1] == 1;
  std::array<std::uint32_t, 3> info{};
  if (hasInfo) {
    info[0] = unpack32(packet.bytes.data() + 3);
    info[1] = unpack32(packet.bytes.data() + 8);
    info[2] = unpack32(packet.bytes.data() + 13);
  }
  presonus::dice::ReceiverStateGuard guard(portableStateLock_);
  state_.command = static_cast<unsigned char>(command);
  state_.status = status;
  if (hasInfo)
    state_.infoWords = info;
}

} // namespace Presonus::DICE
