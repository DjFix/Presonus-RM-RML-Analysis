#include "presonus/noaa/router.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cxxabi.h>
#include <fstream>
#include <new>
#include <pthread.h>
#include <sstream>
#include <string>
#include <typeinfo>
#include <vector>

using Presonus::NOAA::ISysexReceiver;
using presonus::noaa::RouterLifecycleAccess;
using presonus::noaa::SpiServiceAccess;
using Presonus::NOAA::SysexReceiver;
using Presonus::NOAA::TCardRouter;
using Presonus::NOAA::TCardSPI;
using Presonus::Panel::InputPin;

struct OwnedSpi {
  void *pointer = nullptr;
  void *mutex = nullptr;
  std::array<void *, 2> pins{};
  std::array<bool, 2> pinFreed{};
  unsigned pinCount = 0, mutexDestroyed = 0;
  bool freed = false;
};
struct ArrayAllocation {
  void *pointer = nullptr;
  bool freed = false;
};
static std::array<OwnedSpi, 2048> owned;
static std::array<ArrayAllocation, 8192> arrays;
static unsigned ownedCount = 0, arrayCount = 0;
static unsigned rootsAllocated = 0, rootsFreed = 0, rootLocks = 0,
                rootLockDestroys = 0, registrations = 0, unregistrations = 0,
                actualCppDeleteExpressions = 0,
                actualBoundCclResponseChecks = 0, actualRttiChecks = 0,
                corpusCases = 0;

struct Capture {
  TCardRouter *root = nullptr;
  std::size_t rootSize = sizeof(TCardRouter);
  void *rootMutex = nullptr;
  TCardSPI *operationSpi = nullptr;
  unsigned constructingSpi = 0, created = 0, rootDestroys = 0, rootFrees = 0;
  bool active = false, expectRoot = false, ctor = false,
       cppDeleteExpression = false;
  std::array<char, 8192> trace{};
  std::size_t used = 0;
};
static Capture capture;

static bool within(void *pointer, void *object, std::size_t size) {
  const auto p = reinterpret_cast<std::uintptr_t>(pointer);
  const auto start = reinterpret_cast<std::uintptr_t>(object);
  return object && p >= start && p < start + size;
}
static void event(const char *name, int value = -1) {
  assert(capture.active);
  const int n = value < 0 ? std::snprintf(capture.trace.data() + capture.used,
                                          capture.trace.size() - capture.used,
                                          "%s;", name)
                          : std::snprintf(capture.trace.data() + capture.used,
                                          capture.trace.size() - capture.used,
                                          "%s:%d;", name, value);
  assert(n > 0 &&
         static_cast<std::size_t>(n) < capture.trace.size() - capture.used);
  capture.used += static_cast<std::size_t>(n);
}

extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  void *p = __real__Znwm(size);
  if (!capture.active)
    return p;
  if (capture.expectRoot) {
    assert(size == capture.rootSize);
    capture.root = static_cast<TCardRouter *>(p);
    capture.expectRoot = false;
    ++rootsAllocated;
  } else if (size == sizeof(TCardSPI)) {
    assert(!capture.constructingSpi && ownedCount < owned.size());
    owned[ownedCount].pointer = p;
    capture.constructingSpi = ++ownedCount;
    ++capture.created;
    event("spi_new");
  } else if (capture.constructingSpi && size == sizeof(InputPin)) {
    auto &owner = owned[capture.constructingSpi - 1];
    assert(owner.pinCount < 2);
    owner.pins[owner.pinCount++] = p;
    event("pin_new", static_cast<int>(owner.pinCount));
  }
  return p;
}

extern "C" void *__real__Znam(std::size_t);
extern "C" void *__wrap__Znam(std::size_t size) {
  void *p = __real__Znam(size);
  if (capture.active) {
    assert(arrayCount < arrays.size());
    arrays[arrayCount++] = {p, false};
  }
  return p;
}
static void deletingArray(void *p) {
  for (unsigned i = arrayCount; i > 0; --i)
    if (arrays[i - 1].pointer == p && !arrays[i - 1].freed) {
      arrays[i - 1].freed = true;
      return;
    }
}
extern "C" void __real__ZdaPv(void *);
extern "C" void __real__ZdaPvm(void *, std::size_t);
extern "C" void __wrap__ZdaPv(void *p) {
  deletingArray(p);
  __real__ZdaPv(p);
}
extern "C" void __wrap__ZdaPvm(void *p, std::size_t n) {
  deletingArray(p);
  __real__ZdaPvm(p, n);
}

static void deleting(void *p) {
  if (capture.active && p == capture.root) {
    assert(capture.rootDestroys == 1);
    ++capture.rootFrees;
    ++rootsFreed;
    return;
  }
  for (unsigned i = 0; i < ownedCount; ++i) {
    auto &owner = owned[i];
    for (unsigned j = 0; j < owner.pinCount; ++j)
      if (owner.pins[j] == p) {
        assert(!owner.pinFreed[j]);
        owner.pinFreed[j] = true;
        return;
      }
    if (owner.pointer == p) {
      assert(!owner.freed && owner.pinCount == 2 && owner.pinFreed[0] &&
             owner.pinFreed[1] && owner.mutexDestroyed == 1);
      owner.freed = true;
      return;
    }
  }
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  deleting(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  deleting(p);
  __real__ZdlPvm(p, n);
}

extern "C" int __real_pthread_mutex_init(pthread_mutex_t *,
                                         const pthread_mutexattr_t *);
extern "C" int __wrap_pthread_mutex_init(pthread_mutex_t *mutex,
                                         const pthread_mutexattr_t *attr) {
  const int result = __real_pthread_mutex_init(mutex, attr);
  if (capture.active && within(mutex, capture.root, capture.rootSize)) {
    assert(result == 0 && capture.ctor && !capture.rootMutex);
    capture.rootMutex = mutex;
    ++rootLocks;
    event("router_lock_ctor");
  } else if (capture.active && capture.constructingSpi) {
    auto &owner = owned[capture.constructingSpi - 1];
    if (within(mutex, owner.pointer, sizeof(TCardSPI))) {
      assert(result == 0 && !owner.mutex);
      owner.mutex = mutex;
      event("spi_lock_ctor");
    }
  }
  return result;
}
extern "C" int __real_pthread_mutex_destroy(pthread_mutex_t *);
extern "C" int __wrap_pthread_mutex_destroy(pthread_mutex_t *mutex) {
  const int result = __real_pthread_mutex_destroy(mutex);
  if (capture.active && mutex == capture.rootMutex) {
    assert(result == 0 && !capture.ctor && capture.rootDestroys == 0);
    ++capture.rootDestroys;
    ++rootLockDestroys;
    event("router_lock_dtor");
  }
  for (unsigned i = 0; i < ownedCount; ++i)
    if (mutex == owned[i].mutex) {
      assert(result == 0 && !owned[i].freed);
      ++owned[i].mutexDestroyed;
    }
  return result;
}

extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *lock) {
  __real__ZN4Core8Platform9PosixLock4lockEv(lock);
  if (capture.active && capture.operationSpi) {
    assert(lock == static_cast<void *>(
                       &SpiServiceAccess::state(*capture.operationSpi).lock));
    event("spi_lock");
  }
}
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(void *lock) {
  if (capture.active && capture.operationSpi) {
    assert(lock == static_cast<void *>(
                       &SpiServiceAccess::state(*capture.operationSpi).lock));
    event("spi_unlock");
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(lock);
}

extern "C" const void *routerVtable[] asm("_ZTVN8Presonus4NOAA11TCardRouterE");
static void rtti(ISysexReceiver *receiver) {
  assert(receiver == static_cast<ISysexReceiver *>(capture.root));
  assert(dynamic_cast<TCardRouter *>(receiver) == capture.root);
  assert(typeid(*receiver) == typeid(TCardRouter));
  assert(*reinterpret_cast<const void ***>(receiver) == routerVtable + 2);
  const auto *root = dynamic_cast<const __cxxabiv1::__si_class_type_info *>(
      &typeid(TCardRouter));
  const auto *base = dynamic_cast<const __cxxabiv1::__si_class_type_info *>(
      &typeid(SysexReceiver));
  assert(root && base && root->__base_type == &typeid(SysexReceiver) &&
         base->__base_type == &typeid(ISysexReceiver));
  assert(std::strcmp(typeid(TCardRouter).name(),
                     "N8Presonus4NOAA11TCardRouterE") == 0);
  ++actualRttiChecks;
}

extern "C" void
__real__ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *, ISysexReceiver *);
extern "C" void
__wrap__ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *spi, ISysexReceiver *receiver) {
  if (!capture.active) {
    __real__ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE(
        spi, receiver);
    return;
  }
  assert(capture.ctor && !capture.operationSpi);
  rtti(receiver);
  auto &state = RouterLifecycleAccess::state(*capture.root);
  assert(RouterLifecycleAccess::ownsState(*capture.root) && !state.slotTables &&
         !state.ownedSlotTables);
  assert(capture.root->portableState().command == 0 &&
         capture.root->portableState().status == 0 &&
         capture.root->portableState().infoWords[0] == 0);
  for (unsigned i = 256; i < state.applicationBytes.size(); ++i)
    assert(state.applicationBytes[i] == 0);
  // Actual CCL response clock executes; command already set means no GPIO poll.
  capture.root->portableState().command = 1;
  assert(capture.root->waitAck(0) == 1);
  capture.root->portableState().command = 0;
  ++actualBoundCclResponseChecks;
  capture.operationSpi = spi;
  ++registrations;
  event("register");
  __real__ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE(
      spi, receiver);
  capture.operationSpi = nullptr;
}
extern "C" void
__real__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *, ISysexReceiver *);
extern "C" void
__wrap__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE(
    TCardSPI *spi, ISysexReceiver *receiver) {
  if (!capture.active) {
    __real__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE(
        spi, receiver);
    return;
  }
  assert(!capture.ctor && !capture.operationSpi);
  rtti(receiver);
  capture.operationSpi = spi;
  ++unregistrations;
  event("unregister");
  __real__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE(
      spi, receiver);
  capture.operationSpi = nullptr;
}

extern "C" void __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *);
extern "C" void __wrap__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *object) {
  if (capture.active && capture.constructingSpi &&
      object == owned[capture.constructingSpi - 1].pointer) {
    auto &owner = owned[capture.constructingSpi - 1];
    assert(owner.pinCount == 2 && owner.mutex &&
           dynamic_cast<TCardSPI *>(object) == owner.pointer &&
           SpiServiceAccess::singleton() == owner.pointer);
    assert(std::strcmp(typeid(*object).name(),
                       "ZN4Core8Portable9SingletonIN8Presonus4NOAA8TCardSPIEE8i"
                       "nstanceEvE9TInstance") == 0);
    event("registry_add");
    capture.constructingSpi = 0;
  }
  __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(object);
}

struct FailingPins final : presonus::surface_panel_port::InputPinIO {
  std::FILE *open(const char *path, const char *mode) override {
    assert(capture.active && capture.constructingSpi &&
           std::strcmp(path, "/sys/class/gpio/export") == 0 &&
           std::strcmp(mode, "a") == 0);
    const auto &owner = owned[capture.constructingSpi - 1];
    assert(owner.pinCount >= 1 && owner.pinCount <= 2);
    const auto *pin = static_cast<InputPin *>(owner.pins[owner.pinCount - 1]);
    const auto number =
        presonus::surface_panel_port::InputPinAccess::number(*pin);
    assert(number == (owner.pinCount == 1 ? 34 : 137));
    event("gpio_open_error", number);
    return nullptr; // Explicit unavailable-GPIO import error, never success.
  }
  void log(const char *text) override {
    assert(std::strcmp(text, "can't open gpio export\n") == 0);
    event("gpio_log");
  }
  int printPin(std::FILE *, const char *, int) override { std::abort(); }
  int close(std::FILE *) override { std::abort(); }
  void formatPath(char *, std::size_t, const char *, int) override {
    std::abort();
  }
  std::size_t write(const void *, std::size_t, std::size_t,
                    std::FILE *) override {
    std::abort();
  }
  int buffering(std::FILE *, char *, int, std::size_t) override {
    std::abort();
  }
  void rewind(std::FILE *) override { std::abort(); }
  int flush(std::FILE *) override { std::abort(); }
  int get(std::FILE *) override { std::abort(); }
  void notify(Presonus::Panel::PinStateObserver *, int, int) override {
    std::abort();
  }
};
struct NoSpiCalls final : presonus::noaa::SpiServiceIO {
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const presonus::noaa::SpiTransfer &) override {
    std::abort();
  }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
};
static FailingPins pins;
static NoSpiCalls io;
struct Dummy final : ISysexReceiver {
  void receive(const Presonus::NOAA::SysexPacket &) override { std::abort(); }
  bool accepts(const Presonus::NOAA::SysexPacket &) override { std::abort(); }
};
static std::array<Dummy, 16> dummy;

extern "C" void ctorC1(TCardRouter *) asm("_ZN8Presonus4NOAA11TCardRouterC1Ev");
extern "C" void ctorC2(TCardRouter *) asm("_ZN8Presonus4NOAA11TCardRouterC2Ev");
extern "C" void dtorD1(TCardRouter *) asm("_ZN8Presonus4NOAA11TCardRouterD1Ev");
extern "C" void dtorD2(TCardRouter *) asm("_ZN8Presonus4NOAA11TCardRouterD2Ev");

static std::string unhex(const std::string &hex) {
  std::string text;
  for (unsigned i = 0; i < hex.size(); i += 2)
    text.push_back(
        static_cast<char>(std::stoul(hex.substr(i, 2), nullptr, 16)));
  return text;
}
static std::vector<unsigned> receiverLabels(TCardSPI &spi) {
  std::vector<unsigned> result;
  const auto &items = SpiServiceAccess::state(spi).receivers;
  for (int i = 0; i < items.count(); ++i) {
    auto *p = items.at(i);
    if (p == static_cast<ISysexReceiver *>(capture.root)) {
      result.push_back(1);
      continue;
    }
    bool found = false;
    for (unsigned j = 0; j < dummy.size(); ++j)
      if (p == &dummy[j]) {
        result.push_back(j + 2);
        found = true;
        break;
      }
    assert(found);
  }
  return result;
}

static void afterActualCoreRegistryCleanup() {
  assert(!capture.active && rootsAllocated == rootsFreed &&
         rootLocks == rootLockDestroys && registrations == unregistrations);
  unsigned pinsFreed = 0;
  for (unsigned i = 0; i < ownedCount; ++i) {
    const auto &owner = owned[i];
    assert(owner.freed && owner.mutexDestroyed == 1 && owner.pinCount == 2 &&
           owner.pinFreed[0] && owner.pinFreed[1]);
    pinsFreed += 2;
  }
  for (unsigned i = 0; i < arrayCount; ++i)
    assert(arrays[i].freed);
  std::printf(
      "{\"passed\":true,\"lifecycle_cases\":%u,\"actual_root_allocations\":%u,"
      "\"actual_root_frees\":%u,\"actual_root_mutex_init\":%u,\"actual_root_"
      "mutex_destroy\":%u,\"actual_cpp_delete_expressions\":%u,\"actual_bound_"
      "ccl_response_checks\":%u,\"actual_rtti_checks\":%u,\"actual_registry_"
      "owned_spi_frees\":%u,\"actual_pin_frees\":%u,\"actual_cpp_array_"
      "allocations_and_frees\":%u,\"hardware_operations\":0}\n",
      corpusCases, rootsAllocated, rootsFreed, rootLocks, rootLockDestroys,
      actualCppDeleteExpressions, actualBoundCclResponseChecks,
      actualRttiChecks, ownedCount, pinsFreed, arrayCount);
}

struct Derived final : TCardRouter {
  unsigned marker = 0x12345678;
  ~Derived() noexcept(false) = default;
};

extern "C" void *makeBorrowedSpiFixture();
extern "C" TCardSPI *borrowedSpiFixture(void *);
extern "C" presonus::noaa::SpiPacketState *borrowedSpiState(void *);
extern "C" void destroyBorrowedSpiFixture(void *);

int main(int argc, char **argv) {
  static_assert(sizeof(TCardRouter) != sizeof(TCardSPI) &&
                sizeof(TCardSPI) != sizeof(InputPin));
  assert(argc == 2);
  std::atexit(
      afterActualCoreRegistryCleanup); // Registered before actual CCL list.
  presonus::surface_panel_port::setInputPinConstructionIO(&pins);
  presonus::noaa::setSpiServiceConstructionIO(&io);
  std::ifstream input(argv[1]);
  assert(input);
  std::string line;
  while (std::getline(input, line)) {
    std::istringstream in(line);
    std::string ctor, dtor, protocolHex;
    unsigned existing, clear, seed, patternCount, expectedCreated, beforeCount,
        afterCount;
    in >> ctor >> dtor >> existing >> clear >> seed >> patternCount;
    std::vector<unsigned> pattern(patternCount);
    for (auto &label : pattern)
      in >> label;
    in >> expectedCreated >> beforeCount;
    std::vector<unsigned> before(beforeCount);
    for (auto &label : before)
      in >> label;
    in >> afterCount;
    std::vector<unsigned> after(afterCount);
    for (auto &label : after)
      in >> label;
    in >> protocolHex;
    assert(in && existing <= 1 && clear <= 1 && seed <= 255);
    void *fixture = makeBorrowedSpiFixture();
    auto &state = *borrowedSpiState(fixture);
    auto &borrowed = *borrowedSpiFixture(fixture);
    capture = {};
    capture.active = capture.expectRoot = capture.ctor = true;
    void *storage = ::operator new(sizeof(TCardRouter));
    std::memset(storage, seed, sizeof(TCardRouter));
    auto *root = static_cast<TCardRouter *>(storage);
    capture.active = false;
    for (auto label : pattern)
      state.receivers.add(label == 1
                              ? reinterpret_cast<ISysexReceiver *>(storage)
                              : &dummy.at(label - 2));
    SpiServiceAccess::singleton(existing ? &borrowed : nullptr);
    capture.active = true;
    if (ctor == "C1")
      ctorC1(root);
    else {
      assert(ctor == "C2");
      ctorC2(root);
    }
    assert(!capture.constructingSpi &&
           RouterLifecycleAccess::registered(*root));
    capture.active = false;
    assert(receiverLabels(TCardSPI::instance()) == before);
    auto &app = RouterLifecycleAccess::state(*root);
    app.slotTables = &presonus::noaa::rm13731GambitRouterSlots();
    app.ownedSlotTables.emplace(*app.slotTables);
    app.applicationBytes[256] = 1;
    app.applicationBytes[260] = 3;
    if (clear)
      SpiServiceAccess::singleton(nullptr);
    capture.active = true;
    capture.ctor = false;
    if (dtor == "D1")
      dtorD1(root);
    else {
      assert(dtor == "D2");
      dtorD2(root);
    }
    assert(capture.rootDestroys == 1 && capture.rootFrees == 0 &&
           capture.created == expectedCreated);
    assert(std::string(capture.trace.data(), capture.used) ==
           unhex(protocolHex));
    capture.active = false;
    assert(receiverLabels(TCardSPI::instance()) == after);
    capture.active = true;
    ::operator delete(
        storage); // Actual caller cleanup, never a RouterD0 claim.
    assert(capture.rootFrees == 1);
    capture.active = false;
    capture.root = nullptr;
    SpiServiceAccess::singleton(nullptr);
    ++corpusCases;
    destroyBorrowedSpiFixture(fixture);
  }
  assert(corpusCases == 448);
  // Genuine language-level complete/base lifecycles and actual delete
  // expressions.
  for (bool derived : {false, true}) {
    void *fixture = makeBorrowedSpiFixture();
    auto &state = *borrowedSpiState(fixture);
    auto &borrowed = *borrowedSpiFixture(fixture);
    SpiServiceAccess::singleton(&borrowed);
    capture = {};
    capture.rootSize = derived ? sizeof(Derived) : sizeof(TCardRouter);
    capture.active = capture.expectRoot = capture.ctor = true;
    if (derived) {
      auto *object = new Derived;
      assert(object->marker == 0x12345678 &&
             dynamic_cast<Derived *>(static_cast<ISysexReceiver *>(object)) ==
                 object);
      capture.ctor = false;
      delete object;
    } else {
      auto *object = new TCardRouter;
      capture.ctor = false;
      delete object;
    }
    assert(capture.rootDestroys == 1 && capture.rootFrees == 1);
    ++actualCppDeleteExpressions;
    capture.active = false;
    capture.root = nullptr;
    SpiServiceAccess::singleton(nullptr);
    destroyBorrowedSpiFixture(fixture);
  }
  return 0; // Pinned actual CCL registry tears down every owned SPI before
            // receipt.
}
