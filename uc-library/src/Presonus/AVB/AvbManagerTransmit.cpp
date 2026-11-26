#include "presonus/avb/manager_transport.hpp"
#include "presonus/avb/receive_services.hpp"
#include "presonus/noaa/sysex_packet.hpp"
#include <array>
#include <stdexcept>

namespace presonus::avb {
ManagerTransport::ManagerTransport(Presonus::AVB::AvbManagerBase &manager,
                                   Presonus::AVB::AvbManagerBase::Role role,
                                   dice::IdlePump &pump)
    : manager_(manager), services_(pump), role_(role) {}
ManagerTransport::~ManagerTransport() {
  if (manager_.transport_ == this)
    manager_.transport_ = nullptr;
}
void ManagerTransport::receivePacket(
    const Presonus::DICE::SysexPacket &packet) {
  manager_.receive(packet);
}
void ManagerTransport::receivePacket(
    const Presonus::NOAA::SysexPacket &packet) {
  manager_.receive(packet);
}
auto ManagerTransport::responseState() const -> ResponseState {
  if (!manager_.receiveContext_)
    throw std::logic_error("AVB transport requires receive context");
  return {manager_.receiveContext_->command, manager_.receiveContext_->status};
}
int ManagerTransport::transact(unsigned char *bytes, unsigned char length) {
  if (!manager_.receiveContext_)
    throw std::logic_error("AVB transport requires receive context");
  manager_.receiveContext_->command = 0;
  manager_.receiveContext_->status = 0;
  return postAndWait(bytes, length);
}
} // namespace presonus::avb
namespace Presonus::AVB {
void AvbManagerBase::bindTransport(presonus::avb::ManagerTransport &transport) {
  if (&transport.manager_ != this)
    throw std::logic_error("AVB adapter belongs to a different manager");
  const auto expected =
      streamCapacity() == 16 ? Role::Cs18Client : Role::RmServer;
  if (transport.role() != expected)
    throw std::logic_error("AVB role/transport mismatch");
  transport_ = &transport;
}
bool AvbManagerBase::accepts(const NOAA::SysexPacket &packet) {
  if (packet.length <= 1)
    return false;
  const auto command = packet.bytes[1];
  return command >= 0x23 && command <= 0x2f &&
         (0x1dbfU & (1U << (command - 0x23U))) != 0;
}
int AvbManagerBase::sendAvbSysex(unsigned char command, unsigned char *payload,
                                 int length) {
  if (length < 0)
    throw std::invalid_argument(
        "AVB negative payload length is outside defined source-port domain");
  if (length > 30)
    return -1;
  if (!transport_)
    throw std::logic_error("AVB send requires real initialized role transport");
  if ((streamCapacity() == 16 ? Role::Cs18Client : Role::RmServer) !=
      transport_->role())
    throw std::logic_error("AVB role binding changed");
  if (length && !payload)
    throw std::invalid_argument("AVB payload is null");
  std::array<unsigned char, 64> bytes{};
  bytes[0] = 0xf0;
  bytes[1] = command;
  char2Nibble(payload, bytes.data() + 2, length);
  bytes[2 + 2 * length] = 0xf7;
  return transport_->transact(bytes.data(),
                              static_cast<unsigned char>(3 + 2 * length));
}
int AvbManagerBase::resizeListener(unsigned char identifier,
                                   unsigned char channels) {
  unsigned char data[]{identifier, channels, channels};
  return sendAvbSysex(0x26, data, 3);
}
int AvbManagerBase::resizeTalker(unsigned char identifier,
                                 unsigned char channels) {
  unsigned char data[]{identifier, lookupNextTalkerIndex(), channels};
  return sendAvbSysex(0x24, data, 3);
}
int AvbManagerBase::publish(unsigned char identifier, bool enabled) {
  unsigned char data[]{identifier, static_cast<unsigned char>(enabled)};
  return sendAvbSysex(0x25, data, 2);
}
int AvbManagerBase::subscribe(unsigned char identifier,
                              unsigned long long streamKey) {
  unsigned char data[9]{identifier};
  for (int i = 0; i < 8; ++i)
    data[i + 1] = static_cast<unsigned char>(streamKey >> (56 - 8 * i));
  return sendAvbSysex(0x27, data, 9);
}
int AvbManagerBase::setAudioClockToListener(AvbListener *listener) {
  unsigned char data = listener
                           ? static_cast<unsigned char>(
                                 listener->inspectState().identifierByte + 8)
                           : 0x18;
  return sendAvbSysex(0x28, &data, 1);
}
int AvbManagerBase::startAvb(unsigned char first, unsigned char second,
                             bool enabled) {
  if (!receiveContext_)
    throw std::logic_error("AVB requires receive context");
  if (receiveContext_->processingWord > 0)
    return -1;
  unsigned char data[]{first, second, static_cast<unsigned char>(enabled)};
  const auto result = sendAvbSysex(0x23, data, 3);
  receiveContext_->processingWord = 2;
  return result;
}
void AvbManagerBase::stopAvb() {
  if (!receiveContext_)
    throw std::logic_error("AVB requires receive context");
  if (receiveContext_->processingWord <= 0)
    return;
  sendAvbSysex(0x2d, nullptr, 0);
  receiveContext_->processingWord = 0;
}
int AvbManagerBase::configureMasterFirewireRecording(bool enabled) {
  unsigned char data = enabled ? 1 : 0;
  return sendAvbSysex(0x31, &data, 1);
}
} // namespace Presonus::AVB
