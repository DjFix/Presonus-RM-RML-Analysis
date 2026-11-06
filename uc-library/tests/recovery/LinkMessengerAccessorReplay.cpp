#include "presonus/link/Messenger.hpp"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>

namespace {
struct SingletonWatch : Presonus::Link::Messenger {
  static Messenger *peek() { return theInstance; }
};
int constructed, destroyed, registered, allocations, deletes;
bool failAllocation, failConstruction;
void *allocated;
void *messengerLock;
void finalCheck() {
  if (constructed != 1 || destroyed != 1 || registered != 1 ||
      SingletonWatch::peek() != nullptr || deletes != allocations)
    std::_Exit(91);
  std::puts(
      "process-exit: one real lock destruction, one registered singleton");
}
} // namespace
extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t n) {
  if (failAllocation) {
    failAllocation = false;
    throw std::bad_alloc();
  }
  void *p = __real__Znwm(n);
  if (n == sizeof(Presonus::Link::Messenger)) {
    allocated = p;
    ++allocations;
  }
  return p;
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == allocated)
    ++deletes;
  __real__ZdlPv(p);
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == allocated)
    ++deletes;
  __real__ZdlPvm(p, n);
}
extern "C" void __real__ZN4Core8Platform9PosixLockC1Ev(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLockC1Ev(void *p) {
  if (failConstruction) {
    failConstruction = false;
    throw 123;
  }
  __real__ZN4Core8Platform9PosixLockC1Ev(p);
  if (reinterpret_cast<std::uintptr_t>(p) >=
          reinterpret_cast<std::uintptr_t>(allocated) &&
      reinterpret_cast<std::uintptr_t>(p) <
          reinterpret_cast<std::uintptr_t>(allocated) +
              sizeof(Presonus::Link::Messenger)) {
    messengerLock = p;
    ++constructed;
  }
}
extern "C" void __real__ZN4Core8Platform9PosixLockD1Ev(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLockD1Ev(void *p) {
  __real__ZN4Core8Platform9PosixLockD1Ev(p);
  if (p == messengerLock)
    ++destroyed;
}
extern "C" void __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *);
extern "C" void __wrap__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *p) {
  if (constructed != 1 || destroyed != 0)
    std::abort();
  if (p !=
      static_cast<Core::Portable::Deletable *>(Presonus::Link::getMessenger()))
    std::abort();
  ++registered;
  __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(p);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::atexit(
      finalCheck); // before actual provider registers its exit destructor
  if (std::strcmp(argv[1], "allocation-failure") == 0) {
    failAllocation = true;
    try {
      Presonus::Link::getMessenger();
      return 3;
    } catch (const std::bad_alloc &) {
    }
    if (registered || constructed || allocations)
      return 4;
  } else if (std::strcmp(argv[1], "construction-failure") == 0) {
    failConstruction = true;
    try {
      Presonus::Link::getMessenger();
      return 5;
    } catch (int value) {
      if (value != 123)
        return 6;
    }
    if (registered || constructed || allocations != 1 || deletes != 1)
      return 7;
  } else if (std::strcmp(argv[1], "normal") != 0)
    return 8;
  auto *first = Presonus::Link::getMessenger();
  if (!first || first->releaseRequested())
    return 9;
  first->release();
  for (int i = 0; i != 100; ++i)
    if (Presonus::Link::getMessenger() != first || !first->releaseRequested())
      return 10;
  if (constructed != 1 || registered != 1 || destroyed)
    return 11;
  std::puts("first/repeated: stable identity, one real construction and "
            "registration");
}
