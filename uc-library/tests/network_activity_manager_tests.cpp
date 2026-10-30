#include "presonus/uc/network_activity_manager.hpp"
#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using Core::Platform::PosixLock;
using Presonus::UC::ILowLevelNetworkListener;
using Presonus::UC::INetworkActivityManager;
using Presonus::UC::NetworkActivityManager;
using Access = presonus::uc::NetworkActivityPortAccess;
namespace test {
bool tracking = false, capture = false;
unsigned lockDepth = 0;
NetworkActivityManager *manager = nullptr;
PosixLock *lock = nullptr;
std::vector<std::string> events;
std::map<void *, std::size_t> arrays;
unsigned allocations = 0, frees = 0, teardowns = 0;
void require(bool b, const char *m) {
  if (!b)
    throw std::runtime_error(m);
}
void event(std::string s) {
  if (capture)
    events.push_back(s);
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
} // namespace test
extern "C" void *__real__Znam(std::size_t);
extern "C" void __real__ZdaPv(void *);
extern "C" void __real__ZdaPvm(void *, std::size_t);
extern "C" void *__wrap__Znam(std::size_t n) {
  auto *p = __real__Znam(n);
  if (test::tracking) {
    test::arrays[p] = n;
    ++test::allocations;
    if (test::capture) {
      test::require(test::lockDepth == 1,
                    "vector growth without listener lock");
      test::event(
          "resize:" +
          std::to_string(Access::listeners(*test::manager).count() + 1));
    }
  }
  return p;
}
void arrayRelease(void *p) {
  if (test::tracking && test::arrays.erase(p)) {
    ++test::frees;
    if (test::capture && !test::lockDepth)
      test::event("vector_storage_free");
  }
}
extern "C" void __wrap__ZdaPv(void *p) {
  arrayRelease(p);
  __real__ZdaPv(p);
}
extern "C" void __wrap__ZdaPvm(void *p, std::size_t n) {
  arrayRelease(p);
  __real__ZdaPvm(p, n);
}
extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(PosixLock *);
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(PosixLock *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(PosixLock *self) {
  if (test::capture) {
    test::require(!test::lockDepth && (!test::lock || test::lock == self),
                  "unexpected listener lock");
    test::lock = self;
    test::event("lock");
  }
  __real__ZN4Core8Platform9PosixLock4lockEv(self);
  ++test::lockDepth;
}
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(PosixLock *self) {
  test::require(test::lockDepth == 1, "unlock depth wrong");
  --test::lockDepth;
  if (test::capture) {
    test::require(test::lock == self, "unlock receiver wrong");
    test::event("unlock");
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(self);
}
extern "C" void __real__ZN4Core8Platform9PosixLockD1Ev(PosixLock *);
extern "C" void __real__ZN4Core8Platform9PosixLockD2Ev(PosixLock *);
extern "C" void __wrap__ZN4Core8Platform9PosixLockD1Ev(PosixLock *self) {
  if (test::capture) {
    test::require(test::lockDepth == 0, "lock destroyed whileheld");
    test::event("lock_cleanup");
    ++test::teardowns;
  }
  __real__ZN4Core8Platform9PosixLockD1Ev(self);
}
extern "C" void __wrap__ZN4Core8Platform9PosixLockD2Ev(PosixLock *self) {
  if (test::capture) {
    test::require(test::lockDepth == 0, "lock destroyed whileheld");
    test::event("lock_cleanup");
    ++test::teardowns;
  }
  __real__ZN4Core8Platform9PosixLockD2Ev(self);
}
std::vector<int> ids(const std::string &s) {
  std::vector<int> out;
  if (s == "-")
    return out;
  std::istringstream in(s);
  std::string n;
  while (std::getline(in, n, ','))
    out.push_back(std::stoi(n));
  return out;
}
int main(int argc, char **argv) {
  try {
    test::require(argc == 2, "fixture missing");
    std::ifstream file(argv[1]);
    test::require(bool(file), "fixture unreadable");
    std::string line;
    unsigned cases = 0, excluded = 0, resetCases = 0, getterCases = 0;
    std::array<unsigned, 8> tokens{};
    for (unsigned i = 0; i < tokens.size(); ++i)
      tokens[i] = 0x12340000 + i;
    const auto originals = tokens;
    auto listener = [&](int id) {
      return id ? reinterpret_cast<ILowLevelNetworkListener *>(&tokens.at(id))
                : nullptr;
    };
    while (std::getline(file, line)) {
      std::istringstream row(line);
      std::string role, action, input, expectedIds, expectedTrace;
      int capacity, which, status, pattern;
      row >> role >> action >> capacity >> input >> which >> status >>
          pattern >> expectedIds >> expectedTrace;
      test::require(bool(row), "fixture invalid");
      auto before = ids(input), after = ids(expectedIds);
      // Current upstream's throwing new[] cannot produce the original
      // booleanfalse resize dependency result. Preserve these72 original-only
      // witnesses; do not weaken/inject unsafe allocation behavior or claim
      // their native equivalence.
      if (action == "add" && before.size() == unsigned(capacity) && !status) {
        ++excluded;
        continue;
      }
      presonus::uc::NetworkActivityProjection initial;
      for (unsigned i = 0; i < initial.bytes.size(); ++i)
        initial.bytes[i] = static_cast<unsigned char>(pattern + i);
      test::tracking = true;
      alignas(NetworkActivityManager) unsigned char
          storage[sizeof(NetworkActivityManager)];
      auto *object = new (storage) NetworkActivityManager(
          presonus::uc::NetworkActivityPortTag{}, initial, capacity);
      test::manager = object;
      test::lock = nullptr;
      for (int id : before)
        object->addListener(listener(id));
      test::events.clear();
      test::capture = true;
      INetworkActivityManager *interface = object;
      bool destroyed = false;
      if (action == "get") {
        test::require(&interface->getActivityInfo() ==
                          &Access::activity(*object),
                      "getter does not reference projected state");
        ++getterCases;
      } else if (action == "reset") {
        interface->resetActivity();
        ++resetCases;
      } else if (action == "add")
        interface->addListener(listener(which));
      else if (action == "remove")
        interface->removeListener(listener(which));
      else {
        object->~NetworkActivityManager();
        destroyed = true;
      }
      test::capture = false;
      if (destroyed) {
        std::string expected =
            capacity ? "vector_storage_free,lock_cleanup" : "lock_cleanup";
        test::require(
            test::trace() == expected,
            ("actual Vector/lock teardown mismatch: " + test::trace()).c_str());
      } else {
        test::require(
            test::trace() == (expectedTrace == "-" ? "" : expectedTrace),
            ("trace mismatch: " + test::trace() + " expected " + expectedTrace)
                .c_str());
        const auto &activity = Access::activity(*object).bytes;
        if (action == "reset") {
          test::require(std::equal(activity.begin(), activity.begin() + 8,
                                   initial.bytes.begin()),
                        "reset clobbered untouched getterprefix");
          test::require(std::all_of(activity.begin() + 8, activity.end(),
                                    [](auto b) { return b == 0; }),
                        "reset missed opaque payload byte");
        } else
          test::require(activity == initial.bytes, "nonreset changed activity");
        auto &values = Access::listeners(*object);
        test::require(values.count() == int(after.size()),
                      "listener count differs");
        for (unsigned i = 0; i < after.size(); ++i)
          test::require(values.at(i) == listener(after[i]),
                        "duplicate/null/list order changed");
        if (action == "remove" &&
            std::find(before.begin(), before.end(), which) != before.end()) {
          auto *raw = values.getItems();
          test::require(raw[after.size()] == nullptr,
                        "removed tail not reset to actual error value");
        }
        object->~NetworkActivityManager();
      }
      test::tracking = false;
      test::require(test::arrays.empty() && test::lockDepth == 0,
                    "actual array/lock leak");
      test::require(tokens == originals, "borrowed listener storage modified");
      ++cases;
    }
    test::require(cases == 1368 && excluded == 72 &&
                      test::allocations == test::frees,
                  "case/actualfree count mismatch");
    std::cout << "PASS original_app_cases=" << cases
              << " original_only_resize_false=" << excluded
              << " actual_array_allocations=" << test::allocations
              << " actual_forwarded_array_frees=" << test::frees
              << " actual_captured_lock_teardowns=" << test::teardowns
              << " preserved_prefix_resets=" << resetCases
              << " borrowed_getter_views=" << getterCases
              << " borrowed_listeners_unchanged=true\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
