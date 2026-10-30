#include "presonus/uc/DicePacketQueue.hpp"

namespace Presonus::UC {
Packet::~Packet() {}
template <int Capacity> DataPacket<Capacity>::~DataPacket() {}

void PacketFactory::releasePacket(Packet *packet) { delete packet; }

template <int Capacity>
DataPacketFactory<Capacity> &DataPacketFactory<Capacity>::instance() {
  static DataPacketFactory theFactory{PacketStorageTag{}};
  return theFactory;
}
template <int Capacity> DataPacketFactory<Capacity>::~DataPacketFactory() {
  while (auto *packet = pool_.removeFirst())
    delete packet;
}
template <int Capacity>
int DataPacketFactory<Capacity>::getMaxPacketSize() const {
  return Capacity;
}
template <int Capacity> Packet *DataPacketFactory<Capacity>::createPacket() {
  Core::Threads::ScopedLock guard(lock_);
  if (auto *packet = pool_.removeFirst())
    return packet;
  return new DataPacket<Capacity>(PacketStorageTag{});
}
template <int Capacity>
void DataPacketFactory<Capacity>::releasePacket(Packet *packet) {
  // Original valid domain requires a nonnull factory-owned/live packet.
  Core::Threads::ScopedLock guard(lock_);
  if (packet->reusable)
    pool_.append(packet);
  else
    delete packet;
}

PacketQueue::PacketQueue(PacketFactory &factory) : factory_(factory) {}
PacketQueue::~PacketQueue() { flush(); }
void PacketQueue::flush() {
  Core::Threads::ScopedLock guard(lock_);
  while (auto *packet = packets_.removeFirst())
    factory_.releasePacket(packet);
}

DicePacketQueue::DicePacketQueue() : PacketQueue(getFactory()) {}
PacketFactory &DicePacketQueue::getFactory() {
  return DataPacketFactory<200>::instance();
}
bool DicePacketQueue::peakMIDI(unsigned char *midi, unsigned char &length) {
  Core::Threads::ScopedLock guard(lock_);
  length = 0;
  auto *packet = packets_.getFirst();
  return packet ? toMIDI(*packet, midi, length) : false;
}
bool DicePacketQueue::readMIDI(unsigned char *midi, unsigned char &length) {
  Core::Threads::ScopedLock guard(lock_);
  length = 0;
  auto *packet = packets_.removeFirst();
  if (!packet)
    return false;
  const bool success = toMIDI(*packet, midi, length);
  factory_.releasePacket(packet);
  return success;
}
bool DicePacketQueue::writeMIDI(const unsigned char *midi) {
  Core::Threads::ScopedLock guard(lock_);
  if (midi[0] != 0xf0 || midi[1] != 0x40)
    return false;
  auto *packet = factory_.createPacket();
  if (!fromMIDI(*packet, midi)) {
    factory_.releasePacket(packet);
    return false;
  }
  packets_.append(packet);
  return true;
}

template class DataPacket<200>;
template class DataPacketFactory<200>;
} // namespace Presonus::UC
