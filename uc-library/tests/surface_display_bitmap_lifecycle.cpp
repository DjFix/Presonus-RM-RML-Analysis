#include "presonus/surface_panel/BitmapDrawing.hpp"
#include <cstdlib>
#include <iostream>
#include <new>
#include <pthread.h>
#include <stdexcept>
using B = Presonus::Panel::BitmapDisplay;
using Access = presonus::surface_panel_port::BitmapDrawingAccess;
struct SingletonAccess : Core::Portable::Singleton<B> {
  static B *&storage() { return theInstance; }
};
static void *watched = nullptr;
static unsigned deallocations = 0, mutexInitializations = 0,
                mutexDestructions = 0;
extern "C" int __real_pthread_mutex_init(pthread_mutex_t *,
                                         const pthread_mutexattr_t *);
extern "C" int __real_pthread_mutex_destroy(pthread_mutex_t *);
extern "C" int __wrap_pthread_mutex_init(pthread_mutex_t *p,
                                         const pthread_mutexattr_t *a) {
  int result = __real_pthread_mutex_init(p, a);
  if (result == 0)
    ++mutexInitializations;
  return result;
}
extern "C" int __wrap_pthread_mutex_destroy(pthread_mutex_t *p) {
  int result = __real_pthread_mutex_destroy(p);
  if (result == 0)
    ++mutexDestructions;
  return result;
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == watched)
    ++deallocations;
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == watched)
    ++deallocations;
  __real__ZdlPvm(p, n);
}
extern "C" void C1(B *) asm("_ZN8Presonus5Panel13BitmapDisplayC1Ev");
extern "C" void C2(B *) asm("_ZN8Presonus5Panel13BitmapDisplayC2Ev");
extern "C" void D1(B *) asm("_ZN8Presonus5Panel13BitmapDisplayD1Ev");
extern "C" void D2(B *) asm("_ZN8Presonus5Panel13BitmapDisplayD2Ev");
extern "C" void D0(B *) asm("_ZN8Presonus5Panel13BitmapDisplayD0Ev");
int main() {
  unsigned cases = 0;
  for (int ctor = 0; ctor != 2; ++ctor)
    for (int variant = 0; variant != 5; ++variant)
      for (int relation = 0; relation != 3; ++relation) {
        B other;
        SingletonAccess::storage() = relation == 2 ? &other : nullptr;
        void *allocation = ::operator new(sizeof(B));
        auto *p = static_cast<B *>(allocation);
        unsigned initialized = mutexInitializations;
        if (ctor)
          C2(p);
        else
          C1(p);
        if (mutexInitializations - initialized != 1)
          throw std::runtime_error("genuine lock construction count");
        auto state = Access::state(*p);
        for (int v : state)
          if (v)
            throw std::runtime_error("initial fields");
        if (!Access::textDirty(*p) || Access::port(*p) != nullptr)
          throw std::runtime_error("initial dirty/port");
        for (unsigned i = 0; i < 1540; ++i)
          if (Access::bitmap(*p)[i] != 0 || Access::lastSent(*p)[i] != 255)
            throw std::runtime_error("initial current/cache");
        if (SingletonAccess::storage() != (relation == 2 ? &other : nullptr))
          throw std::runtime_error("ctor altered singleton");
        SingletonAccess::storage() = relation == 0   ? nullptr
                                     : relation == 1 ? p
                                                     : &other;
        auto *base = static_cast<Core::Portable::Deletable *>(p);
        if (dynamic_cast<B *>(base) != p ||
            static_cast<Presonus::Panel::IDisplay *>(p)->getScreenWidth() !=
                192)
          throw std::runtime_error("real bases");
        watched = p;
        deallocations = 0;
        unsigned destroyed = mutexDestructions;
        if (variant == 0)
          D1(p);
        else if (variant == 1)
          D2(p);
        else if (variant == 2)
          D0(p);
        else if (variant == 3)
          base->~Deletable();
        else
          delete base;
        if (mutexDestructions - destroyed != 1)
          throw std::runtime_error("genuine lock cleanup count");
        if (deallocations != unsigned(variant == 2 || variant == 4))
          throw std::runtime_error("real delete count");
        if (SingletonAccess::storage() != (relation == 2 ? &other : nullptr))
          throw std::runtime_error("real CCL singleton cleanup");
        watched = nullptr;
        if (variant != 2 && variant != 4)
          ::operator delete(allocation);
        SingletonAccess::storage() = nullptr;
        ++cases;
      }
  std::cout << "{\"passed\":true,\"cases\":" << cases
            << ",\"real_CCL_lock_and_singleton\":true,\"actual_deallocation\":"
               "true,\"secondary_base_dispatch\":true}\n";
}
