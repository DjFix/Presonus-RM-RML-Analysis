#include "presonus/dice/manager.hpp"
#include "presonus/dice/manager_lifetime.hpp"
#include "presonus/dice/programmer_device_services.hpp"
#include "presonus/dice/uart_assembly.hpp"
#include "presonus/panel/uart_comm.hpp"
#include <atomic>
#include <cassert>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <memory>
#include <pthread.h>
#include <stdexcept>
#include <thread>
#include <vector>
using namespace presonus::dice;
using Presonus::DICE::Dice3Manager;
extern "C" __attribute__((noinline)) void
manager_delete_primary(Core::Threads::Thread *p) {
  delete p;
}
extern "C" __attribute__((noinline)) void
manager_delete_secondary(Core::Portable::Singleton<Dice3Manager> *p) {
  delete p;
}
static std::atomic<int> joins{0}, creates{0}, completed{0};
static bool failCreate = false;
static void *expectedDelete = nullptr;
static int observedDeletes = 0, providerDestroyed = 0, providerCloses = 0;
static void *deletedPointers[16]{};
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == expectedDelete) {
    deletedPointers[observedDeletes++] = p;
    expectedDelete = nullptr;
  }
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == expectedDelete) {
    deletedPointers[observedDeletes++] = p;
    expectedDelete = nullptr;
  }
  __real__ZdlPvm(p, n);
}
static void shutdownReport() {
  assert(joins == 1);
  assert(providerDestroyed == 1);
  assert(providerCloses == 1);
  assert(observedDeletes == 1);
  std::printf("Observed CCL registry Manager delete target=%p\n",
              deletedPointers[0]);
  std::puts("{\"passed\":true,\"shutdown_registry_order\":true,\"actual_"
            "pthread_joins\":1,\"actual_manager_deallocation\":true}");
}

extern "C" int __real_pthread_create(pthread_t *, const pthread_attr_t *,
                                     void *(*)(void *), void *);
extern "C" int __real_pthread_join(pthread_t, void **);
extern "C" int __wrap_pthread_create(pthread_t *t, const pthread_attr_t *a,
                                     void *(*f)(void *), void *p) {
  ++creates;
  if (failCreate)
    return EAGAIN;
  return __real_pthread_create(t, a, f, p);
}
extern "C" int __wrap_pthread_join(pthread_t t, void **p) {
  int r = __real_pthread_join(t, p);
  assert(r == 0);
  ++joins;
  ++completed;
  return r;
}
struct Pin final : ProgrammerOutputPin {
  static int alive;
  Pin() { ++alive; }
  ~Pin() { --alive; }
  void set(int) override {}
};
int Pin::alive = 0;
struct Device final : ProgrammerDeviceServices {
  bool fail = false;
  int openDevice(const char *, int) override { std::abort(); }
  int modeIoctl(int, unsigned, std::uint32_t &) override { std::abort(); }
  int closeDevice(int) override { std::abort(); }
  std::unique_ptr<ProgrammerOutputPin> makeOutputPin(int n) override {
    assert(n == 100);
    if (fail)
      throw std::runtime_error("pin failure");
    return std::make_unique<Pin>();
  }
};
struct Uart final : presonus::panel::UartServices {
  ~Uart() { ++providerDestroyed; }
  std::atomic<int> opens{0}, reads{0}, closes{0};
  bool fail = false;
  int openFile(const char *p, int) override {
    assert(std::strcmp(p, "/dev/ttyS0") == 0);
    ++opens;
    return fail ? -1 : 71;
  }
  int closeFile(int d) override {
    assert(d == 71);
    ++closes;
    ++providerCloses;
    return 0;
  }
  int readFile(int, void *, std::uint32_t) override {
    ++reads;
    return 0;
  }
  int writeFile(int, const void *, std::uint32_t n) override { return n; }
  int exclusive(int, unsigned long) override { return 0; }
  int getAttributes(int, termios &t) override {
    t = {};
    return 0;
  }
  void makeRaw(termios &) override {}
  int setSpeed(termios &, speed_t) override { return 0; }
  int setAttributes(int, int, const termios &) override { return 0; }
  int setFlags(int, int, int) override { return 0; }
  void printError(const char *) override {}
  std::int64_t rawTicks() override { return 0; }
};
static int count() {
  auto &u = Presonus::DICE::Dice3Uart::instance();
  auto &s = UartLifetimeAccess::state(u);
  Core::Threads::ScopedLock g(s.lock);
  return s.receivers.count();
}
int main(int argc, char **) {
  auto dev = std::make_shared<Device>();
  auto uart = std::make_shared<Uart>();
  auto cfg =
      std::make_shared<CclManagerLifetimeConfiguration>(nullptr, dev, uart);
  {
    bool threw = false;
    try {
      Dice3Manager m;
    } catch (const std::logic_error &) {
      threw = true;
    }
    assert(threw);
  }
  if (argc > 1) {
    std::atexit(shutdownReport);
    ScopedManagerLifetimeConfiguration scope(cfg);
    auto &m = Dice3Manager::instance();
    expectedDelete = &m;
    assert(count() == 1);
    return 0;
  }
  int base = count(), cases = 1;
  for (int mode = 0; mode < 3; ++mode) {
    ScopedManagerLifetimeConfiguration scope(cfg);
    int before = joins;
    auto *m = new Dice3Manager;
    expectedDelete = m;
    int freesBefore = observedDeletes;
    assert(count() == base + 1);
    assert(Pin::alive == 0);
    assert(m->portableWorkerMayDispatch());
    if (mode == 0)
      delete m;
    else if (mode == 1) {
      Core::Threads::Thread *b = m;
      manager_delete_primary(b);
    } else {
      Core::Portable::Singleton<Dice3Manager> *b = m;
      manager_delete_secondary(b);
    }
    assert(count() == base);
    assert(observedDeletes == freesBefore + 1);
    assert(Pin::alive == 0);
    assert(joins == before + 1);
    ++cases;
  }
  {
    ScopedManagerLifetimeConfiguration scope(cfg);
    dev->fail = true;
    bool threw = false;
    int before = joins;
    try {
      Dice3Manager m;
    } catch (const std::runtime_error &) {
      threw = true;
    }
    dev->fail = false;
    assert(threw && count() == base && Pin::alive == 0 && joins == before + 1);
    ++cases;
  }
  {
    ScopedManagerLifetimeConfiguration scope(cfg);
    failCreate = true;
    int before = joins;
    {
      Dice3Manager m;
      assert(count() == base + 1);
    }
    failCreate = false;
    assert(joins == before && count() == base);
    ++cases;
  }
  {
    ScopedManagerLifetimeConfiguration scope(cfg);
    uart->fail = true;
    {
      Dice3Manager m;
      assert(count() == base + 1);
    }
    uart->fail = false;
    assert(count() == base);
    ++cases;
  }
  {
    ScopedManagerLifetimeConfiguration scope(cfg);
    Dice3Manager m;
    std::atomic<bool> rejected{false};
    std::thread t([&] {
      ScopedManagerLifetimeConfiguration local(cfg);
      try {
        Dice3Manager other;
      } catch (const std::logic_error &) {
        rejected = true;
      }
    });
    t.join();
    assert(rejected);
    ++cases;
  }
  std::weak_ptr<Uart> weak = uart;
  cfg.reset();
  uart.reset();
  assert(!weak.expired());
  auto replacement = std::make_shared<Uart>();
  auto cfg2 = std::make_shared<CclManagerLifetimeConfiguration>(nullptr, dev,
                                                                replacement);
  {
    ScopedManagerLifetimeConfiguration scope(cfg2);
    Dice3Manager m;
    assert(weak.expired());
    assert(count() == base + 1);
  }
  assert(count() == base);
  ++cases;
  assert(Pin::alive == 0 && creates > 0 && completed > 0);
  for (int i = 0; i < observedDeletes; ++i)
    std::printf("Observed Manager delete target[%d]=%p\n", i,
                deletedPointers[i]);
  std::printf("{\"passed\":true,\"cases\":%d,\"actual_pthread_joins\":%d,"
              "\"physical_device_operations\":0}\n",
              cases, int(joins));
}
