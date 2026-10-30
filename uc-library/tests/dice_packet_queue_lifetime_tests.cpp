#include "presonus/uc/DicePacketQueue.hpp"
#include <array>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
using namespace Presonus::UC;
namespace {
std::array<void *, 4096> live{};
unsigned allocations = 0, frees = 0;
std::array<void *, 128> registeredObjects{};
unsigned registrationCount = 0;

void require(bool b) {
  if (!b)
    throw std::runtime_error("native/original queue ownership mismatch");
}
void recordFree(void *p) {
  for (auto &slot : live)
    if (slot == p && p) {
      slot = nullptr;
      ++frees;
      break;
    }
}
std::array<unsigned char, 255> unhex(const std::string &s) {
  require(s.size() == 510);
  std::array<unsigned char, 255> a{};
  for (unsigned i = 0; i < a.size(); ++i)
    a[i] =
        static_cast<unsigned char>(std::stoul(s.substr(i * 2, 2), nullptr, 16));
  return a;
}
} // namespace
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  auto *p = __real__Znwm(size);
  if (size == sizeof(DataPacket<200>)) {
    bool found = false;
    for (auto &slot : live)
      if (!slot) {
        slot = p;
        found = true;
        break;
      }
    if (!found)
      std::abort();
    ++allocations;
  }
  return p;
}
extern "C" void __wrap__ZdlPv(void *p) {
  recordFree(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  recordFree(p);
  __real__ZdlPvm(p, n);
}
extern "C" int __real___cxa_atexit(void (*)(void *), void *, void *);
extern "C" int __wrap___cxa_atexit(void (*callback)(void *), void *object,
                                   void *dso) {
  if (registrationCount == registeredObjects.size())
    std::abort();
  registeredObjects[registrationCount++] = object;
  return __real___cxa_atexit(callback, object, dso);
}
int main(int argc, char **argv) {
  try {
    require(argc == 2);
    std::ifstream input(argv[1]);
    require(bool(input));
    char op;
    std::unique_ptr<DicePacketQueue> queue;
    unsigned startAlloc = 0, startFree = 0, cases = 0, operations = 0;
    while (input >> op) {
      if (op == 'Q') {
        unsigned id;
        input >> id;
        startAlloc = allocations;
        startFree = frees;
        queue = std::make_unique<DicePacketQueue>();
        require(&DicePacketQueue::getFactory() ==
                &DataPacketFactory<200>::instance());
      } else if (op == 'W') {
        std::string hex;
        unsigned expected;
        input >> hex >> expected;
        const auto midi = unhex(hex);
        require(queue->writeMIDI(midi.data()) == bool(expected));
        ++operations;
      } else if (op == 'P' || op == 'R') {
        std::string seed, expected;
        unsigned result, size;
        input >> seed >> result >> size >> expected;
        auto midi = unhex(seed);
        unsigned char length = 0x9a;
        const bool actual = op == 'P' ? queue->peakMIDI(midi.data(), length)
                                      : queue->readMIDI(midi.data(), length);
        require(actual == bool(result) && length == size &&
                midi == unhex(expected));
        ++operations;
      } else if (op == 'F') {
        queue->flush();
        ++operations;
      } else if (op == 'E') {
        unsigned expectedAlloc, expectedFree;
        input >> expectedAlloc >> expectedFree;
        queue.reset();
        require(allocations - startAlloc == expectedAlloc &&
                frees - startFree == expectedFree);
        ++cases;
      } else if (op == 'B') {
        std::string flags;
        unsigned expectedAlloc, expectedFree;
        input >> flags >> expectedAlloc >> expectedFree;
        startAlloc = allocations;
        startFree = frees;
        {
          DataPacketFactory<200> factory{PacketStorageTag{}};
          require(factory.getMaxPacketSize() == 200);
          std::array<Packet *, 4> pointers{};
          for (auto &p : pointers)
            p = factory.createPacket();
          for (unsigned i = 0; i < 4; ++i) {
            pointers[i]->reusable = flags[i] == '1';
            factory.releasePacket(pointers[i]);
          }
          for (unsigned i = 0; i < 4; ++i)
            if (flags[i] == '1') {
              auto *p = factory.createPacket();
              require(p == pointers[i]);
              factory.releasePacket(p);
            }
        }
        require(allocations - startAlloc == expectedAlloc &&
                frees - startFree == expectedFree);
        ++cases;
      } else {
        require(false);
      }
      require(bool(input));
    }
    unsigned supplementalCases = 0;
    for (unsigned i = 0; i < 32; ++i) {
      auto &factory = DataPacketFactory<200>::instance();
      require(&DicePacketQueue::getFactory() == &factory &&
              &DataPacketFactory<200>::instance() == &factory &&
              factory.getMaxPacketSize() == 200);
      ++supplementalCases;
    }
    for (int flag : {-1, 0, 1, 2, 255})
      for (unsigned i = 0; i < 8; ++i) {
        auto &factory = DataPacketFactory<200>::instance();
        Packet *packet = flag < 0 ? nullptr : factory.createPacket();
        if (packet)
          packet->reusable = flag != 0;
        const auto previousFrees = frees;
        factory.PacketFactory::releasePacket(packet);
        require(frees == previousFrees + (packet ? 1u : 0u));
        ++supplementalCases;
      }
    for (unsigned i = 0; i < 2; ++i) {
      PacketQueue baseQueue(DataPacketFactory<200>::instance());
      ++supplementalCases;
    }
    {
      auto *packet = new Packet;
      delete packet;
      ++supplementalCases;
    }
    {
      DataPacket<200> packet{PacketStorageTag{}};
      Packet *base = &packet;
      require(dynamic_cast<DataPacket<200> *>(base) == &packet);
      auto *link = static_cast<Core::IntrusiveLink<Packet> *>(base);
      require(link != nullptr);
      ++supplementalCases;
    }
    require(supplementalCases == 76);
    const void *singleton = &DataPacketFactory<200>::instance();
    unsigned factoryRegistrations = 0;
    for (unsigned i = 0; i < registrationCount; ++i)
      if (registeredObjects[i] == singleton)
        ++factoryRegistrations;
    require(factoryRegistrations == 1);

    require(cases == 112 && operations == 1920);
    for (auto *p : live)
      require(p == nullptr);
    std::cout << "PASS cases=" << cases << " operations=" << operations
              << " supplemental_cases=" << supplementalCases
              << " actual_factory_cleanup_registrations="
              << factoryRegistrations
              << " actual_packet_allocations=" << allocations
              << " actual_forwarded_frees=" << frees << '\n';
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
