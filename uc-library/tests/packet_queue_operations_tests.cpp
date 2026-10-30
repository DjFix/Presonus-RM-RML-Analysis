#include "presonus/uc/DicePacketQueue.hpp"
#include <array>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <pthread.h>
#include <stdexcept>
#include <string>

namespace queue_test {
using namespace Presonus::UC;
void require(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}
class Probe : public PacketQueue {
public:
  explicit Probe(PacketFactory &factory) : PacketQueue(factory) {}
  void probeMutex() {
    lock_.lock();
    lock_.unlock();
  }
};
struct Allocation {
  void *pointer = nullptr;
  unsigned identity = 0;
};
std::array<Allocation, 4096> live{};
unsigned nextIdentity = 0, allocations = 0, deallocations = 0;
bool accounting = false, capture = false;
char probing = 0;
pthread_mutex_t *queueMutex = nullptr, *factoryMutex = nullptr;
std::array<const char *, 4096> events{};
unsigned eventCount = 0;
void event(const char *name) {
  if (capture) {
    if (eventCount == events.size())
      std::abort();
    events[eventCount++] = name;
  }
}
unsigned identity(const void *p) {
  for (const auto &slot : live)
    if (slot.pointer == p && p)
      return slot.identity;
  require(p == nullptr, "unknown packet identity");
  return 0;
}
void recordFree(void *p) {
  for (auto &slot : live)
    if (slot.pointer == p && p) {
      slot.pointer = nullptr;
      ++deallocations;
      event("free");
      return;
    }
}
unsigned byte(const std::string &hex, unsigned index) {
  return unsigned(std::stoul(hex.substr(index * 2, 2), nullptr, 16));
}
std::string trace() {
  std::string result;
  for (unsigned i = 0; i < eventCount; ++i) {
    if (i)
      result += ',';
    result += events[i];
  }
  return result.empty() ? "-" : result;
}
} // namespace queue_test
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" int __real_pthread_mutex_lock(pthread_mutex_t *);
extern "C" int __real_pthread_mutex_unlock(pthread_mutex_t *);
extern "C" void *__wrap__Znwm(std::size_t size) {
  using namespace queue_test;
  auto *pointer = __real__Znwm(size);
  if (accounting && size == sizeof(Presonus::UC::DataPacket<200>)) {
    bool found = false;
    for (auto &slot : live)
      if (!slot.pointer) {
        slot = {pointer, ++nextIdentity};
        found = true;
        break;
      }
    if (!found)
      std::abort();
    ++allocations;
    event("allocate");
  }
  return pointer;
}
extern "C" void __wrap__ZdlPv(void *p) {
  queue_test::recordFree(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  queue_test::recordFree(p);
  __real__ZdlPvm(p, size);
}
extern "C" int __wrap_pthread_mutex_lock(pthread_mutex_t *mutex) {
  using namespace queue_test;
  const int result = __real_pthread_mutex_lock(mutex);
  if (result != 0)
    std::abort();
  if (probing == 'Q')
    queueMutex = mutex;
  if (probing == 'F')
    factoryMutex = mutex;
  if (mutex == queueMutex)
    event("Q+");
  else if (mutex == factoryMutex)
    event("F+");
  return result;
}
extern "C" int __wrap_pthread_mutex_unlock(pthread_mutex_t *mutex) {
  using namespace queue_test;
  const int result = __real_pthread_mutex_unlock(mutex);
  if (result != 0)
    std::abort();
  if (mutex == queueMutex)
    event("Q-");
  else if (mutex == factoryMutex)
    event("F-");
  return result;
}
int main(int argc, char **argv) {
  using namespace queue_test;
  using namespace Presonus::UC;
  try {
    require(argc == 2, "fixture path required");
    std::ifstream input(argv[1]);
    require(bool(input), "fixture unavailable");
    std::unique_ptr<DataPacketFactory<200>> factory;
    std::unique_ptr<Probe> queue;
    Packet *borrowed = nullptr;
    unsigned cases = 0, operations = 0, allocationStart = 0, freeStart = 0;
    char op;
    while (input >> op) {
      if (op == 'Q') {
        unsigned caseId;
        input >> caseId;
        factory = std::make_unique<DataPacketFactory<200>>(PacketStorageTag{});
        queue = std::make_unique<Probe>(*factory);
        capture = false;
        probing = 'Q';
        queue->probeMutex();
        probing = 'F';
        accounting = true;
        auto *probePacket = factory->createPacket();
        factory->releasePacket(probePacket);
        accounting = false;
        probing = 0;
        require(queueMutex && factoryMutex && queueMutex != factoryMutex,
                "real queue/factory mutex probes failed");
        nextIdentity = 0;
        allocationStart = allocations;
        freeStart = deallocations;
        continue;
      }
      eventCount = 0;
      capture = accounting = true;
      if (op == 'E') {
        unsigned cleanupAllocations, expectedAllocations;
        std::string expectedTrace;
        input >> cleanupAllocations >> expectedAllocations >> expectedTrace;
        if (borrowed) {
          queue->releasePacket(borrowed);
          borrowed = nullptr;
        }
        queue.reset();
        factory.reset();
        capture = accounting = false;
        require(cleanupAllocations == 0 &&
                    allocations - allocationStart == expectedAllocations &&
                    deallocations - freeStart == expectedAllocations,
                "actual allocation/free balance mismatch");
        require(trace() == expectedTrace,
                "destruction lock/free order mismatch");
        for (const auto &slot : live)
          require(slot.pointer == nullptr, "owned packet leaked");
        ++cases;
        queueMutex = factoryMutex = nullptr;
        continue;
      }
      // Parse fixture strings with accounting disabled: only target allocations
      // belong to the packet ownership trace.
      capture = accounting = false;
      if (op == 'W') {
        int size, expectedReturn;
        unsigned seed;
        input >> size >> seed >> expectedReturn;
        std::array<char, 1024> data{};
        for (unsigned i = 0; i < data.size(); ++i)
          data[i] = static_cast<char>((seed + i * 17) & 255);
        capture = accounting = true;
        require(queue->write(data.data(), size) == expectedReturn,
                "write return mismatch");
      } else if (op == 'R' || op == 'P') {
        int size, expectedReturn;
        unsigned seed;
        std::string expected;
        input >> size >> seed >> expectedReturn >> expected;
        std::array<unsigned char, 2048> data{};
        for (unsigned i = 0; i < data.size(); ++i)
          data[i] = static_cast<unsigned char>((seed + i * 13) & 255);
        capture = accounting = true;
        const int actual =
            op == 'R'
                ? queue->read(reinterpret_cast<char *>(data.data()), size)
                : queue->peek(reinterpret_cast<char *>(data.data()), size);
        require(actual == expectedReturn, "copy return mismatch");
        capture = accounting = false;
        require(expectedReturn >= 0, "invalid fixture result");
        for (unsigned i = 0; i < data.size(); ++i)
          require(data[i] == (i < unsigned(expectedReturn)
                                  ? byte(expected, i)
                                  : ((seed + i * 13) & 255)),
                  "copy bytes or untouched suffix mismatch");
        capture = accounting = true;
      } else if (op == 'T') {
        unsigned expectedIdentity, knownBytes;
        int expectedLength;
        std::string expected;
        input >> expectedIdentity >> expectedLength >> knownBytes >> expected;
        require(!borrowed, "caller already owns a packet");
        capture = accounting = true;
        borrowed = queue->retrievePacket();
        capture = accounting = false;
        require(identity(borrowed) == expectedIdentity,
                "retrieve FIFO identity mismatch");
        if (borrowed) {
          require(borrowed->length == expectedLength,
                  "retrieve logical length mismatch");
          for (unsigned i = 0; i < knownBytes; ++i)
            require(borrowed->bytes[i] == byte(expected, i),
                    "initialized packet data/tail changed");
        }
        capture = accounting = true;
      } else if (op == 'U' || op == 'L') {
        unsigned expectedIdentity;
        input >> expectedIdentity;
        require(borrowed && identity(borrowed) == expectedIdentity,
                "caller ownership identity mismatch");
        capture = accounting = true;
        if (op == 'U')
          queue->prependPacket(borrowed);
        else
          queue->releasePacket(borrowed);
        borrowed = nullptr;
      } else if (op == 'M') {
        int length;
        unsigned seed, reusable, expectedIdentity;
        input >> length >> seed >> reusable >> expectedIdentity;
        require(!borrowed, "caller already owns a packet");
        capture = accounting = true;
        borrowed = factory->createPacket();
        require(identity(borrowed) == expectedIdentity,
                "factory packet identity mismatch");
        for (unsigned i = 0; i < borrowed->bytes.size(); ++i)
          borrowed->bytes[i] =
              static_cast<unsigned char>((seed + i * 19) & 255);
        borrowed->length = length;
        borrowed->reusable = reusable != 0;
      } else if (op == 'F') {
        capture = accounting = true;
        queue->flush();
      } else if (op == 'G') {
        int expected;
        input >> expected;
        capture = accounting = true;
        require(queue->getMaxPacketSize() == expected, "capacity mismatch");
      } else {
        require(false, "unknown fixture operation");
      }
      const auto total = queue->getTotalBytes();
      const auto empty = queue->isEmpty();
      capture = accounting = false;
      std::uint32_t expectedTotal;
      unsigned expectedEmpty;
      std::string expectedTrace;
      input >> expectedTotal >> expectedEmpty >> expectedTrace;
      require(bool(input), "truncated fixture");
      require(total == expectedTotal && empty == bool(expectedEmpty),
              "mod32 total or empty state mismatch");
      if (trace() != expectedTrace) {
        std::cerr << "operation " << op << " actual=" << trace()
                  << " expected=" << expectedTrace << '\n';
        require(false, "actual mutex/allocation/free ordering mismatch");
      }
      ++operations;
    }
    require(cases == 80, "missing cases");
    std::cout << "PASS cases=" << cases << " operations=" << operations
              << " actual_packet_allocations=" << allocations
              << " actual_forwarded_frees=" << deallocations
              << " actual_mutex_order=matched\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
