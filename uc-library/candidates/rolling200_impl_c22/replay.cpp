#include "core/system/coredebug.h"
#include <cstdint>
#define private public
#define protected public
#include "presonus/link/Messenger.hpp"
#undef private
#undef protected
#include <cassert>
#include <cstddef>
#include <dlfcn.h>
#include <iostream>
#include <new>
#include <pthread.h>
static unsigned initCount, destroyCount, deleteCount;
static void *watchedDelete;
extern "C" int __real_pthread_mutex_init(pthread_mutex_t *,
                                         const pthread_mutexattr_t *);
extern "C" int __real_pthread_mutex_destroy(pthread_mutex_t *);
extern "C" int pthread_mutex_init(pthread_mutex_t *p,
                                  const pthread_mutexattr_t *a) {
  auto real =
      reinterpret_cast<int (*)(pthread_mutex_t *, const pthread_mutexattr_t *)>(
          dlsym(RTLD_NEXT, "pthread_mutex_init"));
  int result = real(p, a);
  assert(result == 0);
  ++initCount;
  return result;
}
extern "C" int pthread_mutex_destroy(pthread_mutex_t *p) {
  auto real = reinterpret_cast<int (*)(pthread_mutex_t *)>(
      dlsym(RTLD_NEXT, "pthread_mutex_destroy"));
  int result = real(p);
  assert(result == 0);
  ++destroyCount;
  return result;
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  if (p == watchedDelete) {
    ++deleteCount;
    assert(destroyCount > 0);
  }
  __real__ZdlPvm(p, size);
}
using Presonus::Link::Messenger;
int main() {
  Core::DebugPrintf("warm provider lock\n");
  using S = Core::Portable::Singleton<Messenger>;
  const auto initialInit = initCount, initialDestroy = destroyCount;
  {
    Messenger a;
    assert(initCount == initialInit + 1);
    assert(!a.releaseRequested());
    assert(a.nativeWord8_ == 0 && a.nativeWord12_ == 0);
    a.lock_.lock();
    assert(a.lock_.tryLock());
    a.lock_.unlock();
    a.lock_.unlock();
    a.release();
    a.release();
    assert(a.releaseRequested());
    auto *p = new Messenger;
    watchedDelete = p;
    S::theInstance = p;
    delete p;
    assert(deleteCount == 1 && destroyCount == initialDestroy + 1);
    assert(S::theInstance == nullptr);
    p = new Messenger;
    watchedDelete = p;
    S::theInstance = &a;
    delete p;
    assert(deleteCount == 2 && destroyCount == initialDestroy + 2);
    assert(S::theInstance == &a);
    S::theInstance = nullptr;
  }
  assert(initCount == initialInit + 3 && destroyCount == initialDestroy + 3);
  std::cout
      << "CCL mutex init/destroy 3/3; recursive acquisition; actual forwarded "
         "deleting destructor deallocations 2; matching/nonmatching singleton "
         "cleanup; release idempotence passed\n";
}
