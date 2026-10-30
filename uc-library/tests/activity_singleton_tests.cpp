#include "presonus/uc/activity_singleton.hpp"
#include <cassert>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <pthread.h>

namespace {
bool tracking = false;
unsigned arrays = 0, deletedArrays = 0, locks = 0, destroyedLocks = 0;
unsigned sequence = 0, lastArrayDelete = 0, lockDestroy = 0;
unsigned depth = 0, lockCalls = 0, unlockCalls = 0;
void *firstArray = nullptr;
void *secondArray = nullptr;
void verifyExit() {
  assert(tracking && locks == 1 && destroyedLocks == 1 && depth == 0);
  assert(arrays == 2 && deletedArrays == 2 && lastArrayDelete < lockDestroy);
  assert(lockCalls == 6 && unlockCalls == 6);
  std::puts("PASS activity_singleton_once=1 projection_bytes=136 "
            "actual_arrays=2 actual_deletes=2 mutex_destroy=1 "
            "vector_delete_before_mutex=true");
}
void deleted(void *value) {
  if (!tracking || !value)
    return;
  assert(value == firstArray || value == secondArray);
  ++deletedArrays;
  lastArrayDelete = ++sequence;
}
} // namespace

extern "C" void *__real__Znam(std::size_t);
extern "C" void *__wrap__Znam(std::size_t size) {
  void *value = __real__Znam(size);
  if (tracking) {
    assert(value && arrays < 2);
    assert(size == (arrays == 0 ? 5U : 10U) * sizeof(void *));
    (arrays++ == 0 ? firstArray : secondArray) = value;
  }
  return value;
}
extern "C" void __real__ZdaPv(void *);
extern "C" void __wrap__ZdaPv(void *value) {
  deleted(value);
  __real__ZdaPv(value);
}
extern "C" void __real__ZdaPvm(void *, std::size_t);
extern "C" void __wrap__ZdaPvm(void *value, std::size_t size) {
  deleted(value);
  __real__ZdaPvm(value, size);
}
extern "C" int __real_pthread_mutex_init(pthread_mutex_t *,
                                         const pthread_mutexattr_t *);
extern "C" int __wrap_pthread_mutex_init(pthread_mutex_t *mutex,
                                         const pthread_mutexattr_t *attr) {
  int status = __real_pthread_mutex_init(mutex, attr);
  if (tracking) {
    assert(status == 0);
    ++locks;
  }
  return status;
}
extern "C" int __real_pthread_mutex_destroy(pthread_mutex_t *);
extern "C" int __wrap_pthread_mutex_destroy(pthread_mutex_t *mutex) {
  int status = __real_pthread_mutex_destroy(mutex);
  if (tracking) {
    assert(status == 0 && depth == 0);
    ++destroyedLocks;
    lockDestroy = ++sequence;
  }
  return status;
}
extern "C" int __real_pthread_mutex_lock(pthread_mutex_t *);
extern "C" int __wrap_pthread_mutex_lock(pthread_mutex_t *mutex) {
  int status = __real_pthread_mutex_lock(mutex);
  if (tracking) {
    assert(status == 0 && depth == 0);
    ++depth;
    ++lockCalls;
  }
  return status;
}
extern "C" int __real_pthread_mutex_unlock(pthread_mutex_t *);
extern "C" int __wrap_pthread_mutex_unlock(pthread_mutex_t *mutex) {
  if (tracking) {
    assert(depth == 1);
    --depth;
    ++unlockCalls;
  }
  return __real_pthread_mutex_unlock(mutex);
}

int main() {
  assert(std::atexit(verifyExit) == 0);
  tracking = true;
  using Access = presonus::uc::NetworkActivityPortAccess;
  auto &manager = presonus::uc::sourceActivitySingleton();
  const auto &bytes = manager.getActivityInfo().bytes;
  assert(bytes[0] == 136);
  for (unsigned i = 1; i < bytes.size(); ++i)
    assert(bytes[i] == 0);
  assert(Access::listeners(manager).getCapacity() == 0);
  assert(Access::listeners(manager).getDelta() == 5);
  assert(locks == 1 && arrays == 0);
  for (unsigned i = 0; i < 100; ++i)
    assert(&presonus::uc::sourceActivitySingleton() == &manager);
  // nullptr is stored as a pointer value only; no fake listener class or
  // dereference/provider callback is introduced. The recovered add method
  // performs no null filtering, and actual CCL containers own only the array.
  for (unsigned i = 0; i < 6; ++i)
    manager.addListener(nullptr);
  assert(Access::listeners(manager).count() == 6);
  assert(Access::listeners(manager).getCapacity() == 10);
  assert(arrays == 2 && deletedArrays == 1 && destroyedLocks == 0);
  auto &projection = Access::activity(manager).bytes;
  projection[8] = 0x5a;
  projection.back() = 0xa5;
  manager.resetActivity();
  assert(projection[0] == 136 && projection[8] == 0 && projection.back() == 0);
  return 0;
}
