#include "presonus/dsp/OMAPTargetHandler.hpp"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <dlfcn.h>
#include <new>
#include <type_traits>
using Port = Presonus::Dsp::OMAPTargetHandler;
static_assert(std::is_trivially_destructible_v<Port>);
static void *watched;
static unsigned allocations, deletes, frees, matches;
extern "C" void __libc_free(void *) noexcept;
extern "C" void __real__ZdlPv(void *) noexcept;
// Observe the actual libstdc++ delete -> libc free path and forward to real
// glibc deallocation. This is instrumentation, never an invented free event.
extern "C" void free(void *p) noexcept {
  if (watched && p == watched)
    ++frees;
  __libc_free(p);
}
extern "C" void __wrap__ZdlPv(void *p) noexcept {
  if (!watched || p != watched)
    std::abort();
  ++deletes;
  ++matches;
  __real__ZdlPv(p);
}
extern "C" void *omap_allocate() {
  if (watched)
    std::abort();
  allocations = deletes = frees = matches = 0;
  watched = new Port(Port::SourcePortConstruction{});
  ++allocations;
  return watched;
}
extern "C" unsigned omap_delete(void *p) {
  if (!watched || p != watched)
    std::abort();
  // Oracle boundary calls the exported actual host operator delete; no
  // reconstructed release method is invoked in the native bridge build.
  ::operator delete(p);
  return frees;
}
extern "C" unsigned omap_count(unsigned selector) {
  switch (selector) {
  case 0:
    return allocations;
  case 1:
    return deletes;
  case 2:
    return frees;
  case 3:
    return matches;
  default:
    std::abort();
  }
}
extern "C" void omap_finish() {
  if (allocations != 1 || deletes != 1 || frees != 1 || matches != 1)
    std::abort();
  watched = nullptr;
}
extern "C" const char *omap_delete_provider() {
  Dl_info info{};
  if (!dladdr(reinterpret_cast<void *>(&__real__ZdlPv), &info))
    std::abort();
  return info.dli_fname;
}
extern "C" unsigned omap_port_size() { return sizeof(Port); }
#ifndef NATIVE_BRIDGE
int main() {
  unsigned cycles;
  while (std::scanf("%u", &cycles) == 1) {
    for (unsigned i = 0; i < cycles; ++i) {
      auto *p = static_cast<Port *>(omap_allocate());
      p->release();
      const unsigned a = omap_count(0), d = omap_count(1), f = omap_count(2),
                     m = omap_count(3);
      omap_finish();
      if (a != 1 || d != 1 || f != 1 || m != 1)
        return 1;
    }
    std::printf("%u %u %u %u %u\n", cycles, cycles, cycles, cycles, cycles);
  }
}
#endif
