#pragma once
#include "core/public/coreintrusivelist.h"
#include "core/system/corethread.h"
#include <array>
#include <cstdint>

namespace Presonus::UC {
// Independent source-port storage. The genuine Core intrusive-link hierarchy
// is retained, but this does not claim the original ARM32 fields or ABI.
struct Packet : public Core::IntrusiveLink<Packet> {
  virtual ~Packet();
  std::array<unsigned char, 200> bytes{};
  std::int32_t length = 0;
  bool reusable = false;
};

struct PacketStorageTag {};
template <int Capacity> class DataPacket : public Packet {
  static_assert(Capacity == 200, "Only the evidenced 200-byte specialization");

public:
  explicit DataPacket(PacketStorageTag) {}
  ~DataPacket() override;
};

// Exact original slot order: two pure operations and concrete release.
// No original virtual destructor slots exist. Unencoded return declarations
// below remain source-port choices pending independent type evidence.
class PacketFactory {
public:
  virtual int getMaxPacketSize() const = 0;
  virtual Packet *createPacket() = 0;
  virtual void releasePacket(Packet *packet);

protected:
  ~PacketFactory() = default;
};

template <int Capacity> class DataPacketFactory : public PacketFactory {
  static_assert(Capacity == 200, "Only the evidenced 200-byte specialization");

public:
  explicit DataPacketFactory(PacketStorageTag) {}
  static DataPacketFactory &instance();
  ~DataPacketFactory();
  int getMaxPacketSize() const override;
  Packet *createPacket() override;
  void releasePacket(Packet *packet) override;

private:
  Core::Threads::Lock lock_;
  Core::IntrusiveLinkedList<Packet> pool_;
};

class PacketQueue {
public:
  explicit PacketQueue(PacketFactory &factory);
  ~PacketQueue();
  void flush();
  // Ordinary return declarations remain explicit source-port choices pending
  // independent original type evidence. Byte buffers must be disjoint and
  // valid.
  int read(char *data, int size);
  int peek(char *data, int size);
  int write(const char *data, int size);
  void prependPacket(Packet *packet);
  Packet *retrievePacket();
  void releasePacket(Packet *packet);
  std::uint32_t getTotalBytes();
  int getMaxPacketSize() const;
  bool isEmpty();

protected:
  Core::Threads::Lock lock_;
  PacketFactory &factory_;
  Core::IntrusiveLinkedList<Packet> packets_;
};

class DicePacketQueue : public PacketQueue {
public:
  DicePacketQueue();
  bool peakMIDI(unsigned char *midi, unsigned char &length);
  bool readMIDI(unsigned char *midi, unsigned char &length);
  bool writeMIDI(const unsigned char *midi);
  static PacketFactory &getFactory();
  // Original static register calling shape independently established; buffers
  // provide 255 valid bytes. Malformed-input behavior is retained.
  static bool fromMIDI(Packet &packet, const unsigned char *midi);
  static bool toMIDI(const Packet &packet, unsigned char *midi,
                     unsigned char &length);
};
} // namespace Presonus::UC
