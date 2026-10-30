#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/message_queue.hpp"
#include <array>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <new>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
using Core::Threads::Lock;
using Presonus::UC::MessageAttributes;
using Presonus::UC::MessageQueue;
using Access = presonus::uc::MessageQueuePortAccess;
namespace test {
thread_local unsigned lockDepth = 0, providerDepth = 0;
bool capture = false, tracking = true;
MessageQueue *queue = nullptr;
Core::Platform::PosixLock *platformLock = nullptr;
std::map<void *, int> payloads;
std::set<void *> nodes;
std::vector<std::string> events;
unsigned realNodeAllocations = 0, realNodeFrees = 0, realPayloadFrees = 0,
         cleanupNodeFrees = 0, lockTeardowns = 0;
void require(bool b, const char *m) {
  if (!b)
    throw std::runtime_error(m);
}
struct Guard {
  Guard() { ++providerDepth; }
  ~Guard() { --providerDepth; }
};
void event(std::string s) {
  if (capture && !providerDepth) {
    Guard g;
    events.push_back(s);
  }
}
std::string trace() {
  std::string s;
  for (auto &e : events) {
    if (!s.empty())
      s += ',';
    s += e;
  }
  return s;
}
void release(void *p) {
  if (providerDepth || !tracking)
    return;
  auto payload = payloads.find(p);
  if (payload != payloads.end()) {
    require(lockDepth == 0, "payload actually deleted while queue lock held");
    event("delete:" + std::to_string(payload->second));
    payloads.erase(payload);
    ++realPayloadFrees;
  } else if (nodes.erase(p)) {
    if (capture) {
      event(lockDepth ? "node_delete" : "cleanup_node");
      if (!lockDepth)
        ++cleanupNodeFrees;
    }
    ++realNodeFrees;
  }
}
} // namespace test
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void *__wrap__Znwm(std::size_t n) {
  void *p = __real__Znwm(n);
  if (test::capture && !test::providerDepth && test::lockDepth) {
    test::require(n == sizeof(Core::ListLink<MessageAttributes *>),
                  "unexpected allocation under queue lock");
    test::event("new");
    test::Guard g;
    test::nodes.insert(p);
    ++test::realNodeAllocations;
  }
  return p;
}
extern "C" void __wrap__ZdlPv(void *p) {
  test::release(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  test::release(p);
  __real__ZdlPvm(p, n);
}
extern "C" void
__real__ZN4Core8Platform9PosixLock4lockEv(Core::Platform::PosixLock *);
extern "C" void
__wrap__ZN4Core8Platform9PosixLock4lockEv(Core::Platform::PosixLock *self) {
  if (test::capture) {
    test::require((!test::platformLock || self == test::platformLock) &&
                      test::lockDepth == 0,
                  "unexpected lock receiver/depth");
    test::platformLock = self;
    test::event("lock");
  }
  {
    test::Guard g;
    __real__ZN4Core8Platform9PosixLock4lockEv(self);
  }
  ++test::lockDepth;
}
extern "C" void
__real__ZN4Core8Platform9PosixLock6unlockEv(Core::Platform::PosixLock *);
extern "C" void
__wrap__ZN4Core8Platform9PosixLock6unlockEv(Core::Platform::PosixLock *self) {
  test::require(test::lockDepth == 1, "unbalanced unlock");
  --test::lockDepth;
  if (test::capture) {
    test::require(self == test::platformLock, "unexpected unlock receiver");
    test::event("unlock");
  }
  test::Guard g;
  __real__ZN4Core8Platform9PosixLock6unlockEv(self);
}
extern "C" void
__real__ZN4Core8Platform9PosixLockD1Ev(Core::Platform::PosixLock *);
extern "C" void
__real__ZN4Core8Platform9PosixLockD2Ev(Core::Platform::PosixLock *);
extern "C" void
__wrap__ZN4Core8Platform9PosixLockD1Ev(Core::Platform::PosixLock *self) {
  if (test::capture) {
    test::require(test::lockDepth == 0, "lock torn down while held");
    test::event("lock_cleanup");
    ++test::lockTeardowns;
  }
  test::Guard g;
  __real__ZN4Core8Platform9PosixLockD1Ev(self);
}
extern "C" void
__wrap__ZN4Core8Platform9PosixLockD2Ev(Core::Platform::PosixLock *self) {
  if (test::capture) {
    test::require(test::lockDepth == 0, "lock torn down while held");
    test::event("lock_cleanup");
    ++test::lockTeardowns;
  }
  test::Guard g;
  __real__ZN4Core8Platform9PosixLockD2Ev(self);
}
std::vector<int> sequence(const std::string &s) {
  std::vector<int> out;
  if (s == "-")
    return out;
  std::istringstream in(s);
  std::string n;
  while (std::getline(in, n, ','))
    out.push_back(std::stoi(n));
  return out;
}
MessageAttributes *payload(int id) {
  if (!id)
    return nullptr;
  auto *p = new MessageAttributes("owned");
  test::payloads[p] = id;
  return p;
}
int main(int argc, char **argv) {
  try {
    test::require(argc == 2, "fixture path missing");
    std::ifstream file(argv[1]);
    test::require(bool(file), "fixture unreadable");
    std::string line;
    unsigned cases = 0;
    while (std::getline(file, line)) {
      std::istringstream row(line);
      std::string role, action, input, remaining, initialTrace, expected;
      int result;
      row >> role >> action >> input >> remaining >> result >> initialTrace >>
          expected;
      test::require(bool(row), "fixture invalid");
      auto ids = sequence(input);
      auto rest = sequence(remaining);
      alignas(MessageQueue) unsigned char storage[sizeof(MessageQueue)];
      auto *q = new (storage) MessageQueue(presonus::uc::MessageQueuePortTag{});
      test::queue = q;
      test::platformLock = nullptr;
      std::map<int, MessageAttributes *> items;
      for (int id : ids)
        if (id)
          items[id] = payload(id);
      test::events.clear();
      test::capture = true;
      for (int id : ids)
        q->add(id ? items[id] : nullptr);
      test::capture = false;
      test::require(test::lockDepth == 0, "add leaked lock");
      test::require(test::trace() == (initialTrace == "-" ? "" : initialTrace),
                    "add trace mismatch");
      test::events.clear();
      auto priorCleanup = test::cleanupNodeFrees;
      auto priorTeardown = test::lockTeardowns;
      test::capture = true;
      MessageAttributes *retrieved = nullptr;
      if (action == "retrieve")
        retrieved = q->retrieve();
      else if (action == "removeAll")
        q->removeAll();
      else
        q->~MessageQueue();
      test::capture = false;
      if (action == "D1" || action == "D2") {
        auto marker = expected.find(",list_cleanup,lock_cleanup");
        test::require(marker != std::string::npos,
                      "destructor witness missing teardown");
        std::string native = expected.substr(0, marker);
        for (std::size_t i = 0; i < rest.size(); ++i)
          native += ",cleanup_node";
        native += ",lock_cleanup";
        test::require(test::trace() == native,
                      ("destructor trace mismatch: " + test::trace() +
                       " expected " + native)
                          .c_str());
        test::require(test::cleanupNodeFrees == priorCleanup + rest.size() &&
                          test::lockTeardowns == priorTeardown + 1,
                      "actual remaining-node/lock teardown mismatch");
        // A null sentinel terminates payload draining. The actual CCL list
        // destructor releases later nodes while leaving their payload ownership
        // with this test.
        for (int id : rest)
          if (id)
            test::require(test::payloads.count(items[id]) == 1,
                          "payload after sentinel wrongly deleted");
      } else {
        test::require(test::trace() == expected,
                      ("operation trace mismatch: " + test::trace() +
                       " expected " + expected)
                          .c_str());
        if (action == "retrieve")
          test::require(retrieved == (result ? items[result] : nullptr),
                        "FIFO/null result changed");
        for (int id : rest) {
          auto *p = q->retrieve();
          test::require(p == (id ? items[id] : nullptr),
                        "remaining FIFO changed");
          if (p)
            delete p;
        }
        if (retrieved)
          delete retrieved;
        q->~MessageQueue();
      }
      for (auto item : items)
        if (test::payloads.count(item.second))
          delete item.second;
      test::require(test::nodes.empty() && test::payloads.empty() &&
                        test::lockDepth == 0,
                    "actual storage/lock leak");
      ++cases;
    }
    test::require(test::realNodeAllocations == test::realNodeFrees,
                  "node allocation/free counts differ");
    // Source-provider concurrent add/drain with actual pinned lock, no capture
    // globals touched by worker threads. Per-producer order must survive
    // interleave.
    test::tracking = false;
    MessageQueue threaded(presonus::uc::MessageQueuePortTag{});
    constexpr unsigned producers = 4, perProducer = 32;
    std::array<std::array<MessageAttributes *, perProducer>, producers>
        values{};
    for (unsigned p = 0; p < producers; ++p)
      for (unsigned i = 0; i < perProducer; ++i)
        values[p][i] = new MessageAttributes("thread-owned");
    std::vector<std::thread> threads;
    for (unsigned p = 0; p < producers; ++p)
      threads.emplace_back([&, p] {
        for (auto *value : values[p])
          threaded.add(value);
      });
    for (auto &t : threads)
      t.join();
    std::array<unsigned, producers> next{};
    unsigned delivered = 0;
    while (auto *value = threaded.retrieve()) {
      bool found = false;
      for (unsigned p = 0; p < producers; ++p)
        if (next[p] < perProducer && values[p][next[p]] == value) {
          ++next[p];
          found = true;
          break;
        }
      test::require(found, "per-producer FIFO lost");
      delete value;
      ++delivered;
    }
    test::require(delivered == producers * perProducer,
                  "concurrent delivery count wrong");
    std::cout << "PASS original_app_cases=" << cases
              << " actual_node_allocations=" << test::realNodeAllocations
              << " actual_node_frees=" << test::realNodeFrees
              << " actual_payload_frees=" << test::realPayloadFrees
              << " actual_sentinel_cleanup_nodes=" << test::cleanupNodeFrees
              << " actual_lock_teardowns=" << test::lockTeardowns
              << " concurrent_payloads=" << delivered << "\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
