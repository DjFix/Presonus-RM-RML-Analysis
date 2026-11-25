#include "presonus/panel/SharedMemoryComm.hpp"

#include <cassert>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <new>
#include <pthread.h>
#include <string_view>

using Presonus::Panel::SharedMemoryComm;

namespace {
pthread_mutex_t *created{};
pthread_mutex_t *destroyed{};
void *receiver{};
bool freed{};

struct Derived final : SharedMemoryComm {};

void verifyEndpoints(SharedMemoryComm &shared) {
  char value = 'q';
  assert(shared.enableHISpeed(false) == 1);
  assert(shared.open(nullptr) == 1);
  assert(shared.read(&value, 1) == 0 && value == 'q');
  assert(shared.write(&value, 1) == 0 && value == 'q');
  shared.close();
}
} // namespace

extern "C" int __real_pthread_mutex_init(pthread_mutex_t *,
                                         const pthread_mutexattr_t *);
extern "C" int __wrap_pthread_mutex_init(pthread_mutex_t *mutex,
                                         const pthread_mutexattr_t *attrs) {
  const int status = __real_pthread_mutex_init(mutex, attrs);
  if (receiver) {
    assert(status == 0);
    created = mutex;
  }
  return status;
}
extern "C" int __real_pthread_mutex_destroy(pthread_mutex_t *);
extern "C" int __wrap_pthread_mutex_destroy(pthread_mutex_t *mutex) {
  const int status = __real_pthread_mutex_destroy(mutex);
  if (receiver) {
    assert(status == 0 && mutex == created);
    destroyed = mutex;
  }
  return status;
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *ptr) {
  if (ptr == receiver) {
    assert(destroyed == created && destroyed);
    freed = true;
  }
  __real__ZdlPv(ptr);
}
extern "C" void __wrap__ZdlPvm(void *ptr, std::size_t size) {
  if (ptr == receiver) {
    assert(destroyed == created && destroyed);
    freed = true;
  }
  __real__ZdlPvm(ptr, size);
}

[[gnu::noinline]] void virtualDelete(SharedMemoryComm *ptr) { delete ptr; }

int main(int argc, char **argv) {
  assert(argc == 2);
  const std::string_view variant = argv[1];
  for (int i = 0; i < 4; ++i) {
    created = destroyed = nullptr;
    freed = false;
    alignas(Derived) std::byte storage[sizeof(Derived)];
    receiver = storage;
    if (variant == "D0") {
      void *allocation = ::operator new(sizeof(SharedMemoryComm));
      receiver = allocation;
      auto *object = new (allocation) SharedMemoryComm;
      assert(created && !destroyed);
      virtualDelete(object);
      assert(destroyed && freed);
      receiver = nullptr;
      std::cout << "lock_destroy delete\n";
    } else if (variant == "C2" || variant == "D2") {
      auto *object = new (storage) Derived;
      assert(created && !destroyed);
      verifyEndpoints(*object);
      object->~Derived();
      assert(destroyed && !freed);
      receiver = nullptr;
      std::cout << (variant == "C2" ? "lock_construct\n" : "lock_destroy\n");
    } else {
      assert(variant == "C1" || variant == "D1");
      auto *object = new (storage) SharedMemoryComm;
      assert(created && !destroyed);
      verifyEndpoints(*object);
      object->~SharedMemoryComm();
      assert(destroyed && !freed);
      receiver = nullptr;
      std::cout << (variant == "C1" ? "lock_construct\n" : "lock_destroy\n");
    }
  }
  SharedMemoryComm original, copy(original);
  copy = original;
  verifyEndpoints(copy);
}
