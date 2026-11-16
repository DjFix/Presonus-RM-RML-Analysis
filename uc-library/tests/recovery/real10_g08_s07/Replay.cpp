#include "presonus/panel/Fat24FrontPanelComponent.hpp"
#include "presonus/panel/RogueFrontPanelComponent.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
// Linker allocator observation only; production allocation/deallocation is
// real.
static void *allocated[4096];
static unsigned count, released, selfReleased;
static void *receiver;
static bool recording;
static void *coreAllocated[4096];
static unsigned coreCount, coreReleased;
extern "C" void *__real_core_malloc(unsigned);
extern "C" void *__real_core_realloc(void *, unsigned);
extern "C" void __real_core_free(void *);
static void coreObserve(void *p) {
  for (unsigned i = 0; i < coreCount; ++i)
    if (p && coreAllocated[i] == p) {
      coreAllocated[i] = nullptr;
      ++coreReleased;
      break;
    }
}
extern "C" void *__wrap_core_malloc(unsigned n) {
  void *p = __real_core_malloc(n);
  if (recording && p) {
    if (coreCount == 4096)
      std::abort();
    coreAllocated[coreCount++] = p;
  }
  return p;
}
extern "C" void *__wrap_core_realloc(void *p, unsigned n) {
  void *q = __real_core_realloc(p, n);
  if (q || n == 0)
    coreObserve(p);
  if (recording && q) {
    if (coreCount == 4096)
      std::abort();
    coreAllocated[coreCount++] = q;
  }
  return q;
}
extern "C" void __wrap_core_free(void *p) {
  coreObserve(p);
  __real_core_free(p);
}

extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void *__wrap__Znwm(std::size_t n) {
  void *p = __real__Znwm(n);
  if (recording) {
    if (count == 4096)
      std::abort();
    allocated[count++] = p;
  }
  return p;
}
static void observe(void *p) {
  if (!p)
    return;
  if (p == receiver)
    ++selfReleased;
  for (unsigned i = 0; i < count; ++i)
    if (allocated[i] == p) {
      allocated[i] = nullptr;
      ++released;
      break;
    }
}
extern "C" void __wrap__ZdlPv(void *p) {
  observe(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  observe(p);
  __real__ZdlPvm(p, n);
}
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  int n = std::atoi(argv[3]);
  using namespace Presonus::Panel;
  recording = true;
  FrontPanelComponent *p = nullptr;
  if (!std::strcmp(argv[1], "fat"))
    p = new Fat24FrontPanelComponent(
        Fat24FrontPanelComponent::SourcePortConstruction{});
  else if (!std::strcmp(argv[1], "rogue"))
    p = new RogueFrontPanelComponent(
        RogueFrontPanelComponent::SourcePortConstruction{});
  else if (!std::strcmp(argv[1], "base"))
    p = new FrontPanelComponent(FrontPanelComponent::SourcePortConstruction{});
  else
    return 3;
  receiver = p;
  for (int i = 0; i < n; ++i) {
    p->portableFrontState().channels.add(nullptr);
    p->portableFrontState().pasteSelections.add(nullptr);
  }
  // Borrowed pointer must never be released; native outer body only calls base.
  int borrowed = 42;
  p->portableState().registrar = reinterpret_cast<PanelRegistrar *>(&borrowed);
  recording = false;
  const unsigned total = count;
  if (!std::strcmp(argv[2], "D1")) {
    if (!std::strcmp(argv[1], "fat"))
      static_cast<Fat24FrontPanelComponent *>(p)->~Fat24FrontPanelComponent();
    else if (!std::strcmp(argv[1], "rogue"))
      static_cast<RogueFrontPanelComponent *>(p)->~RogueFrontPanelComponent();
    else
      p->~FrontPanelComponent();
    if (selfReleased)
      return 4;
  } else
    delete p;
  unsigned live = 0;
  for (unsigned i = 0; i < count; ++i)
    if (allocated[i])
      ++live;
  if (borrowed != 42)
    return 5;
  unsigned coreLive = 0;
  for (unsigned i = 0; i < coreCount; ++i)
    if (coreAllocated[i])
      ++coreLive;
  if (coreLive)
    return 6;
  std::printf("{\"owned_allocations\":%u,\"released\":%u,\"live\":%u,\"self_"
              "deallocated\":%u,\"core_released\":%u,\"core_live\":%u,"
              "\"borrowed\":%d}\n",
              total - 1, released - selfReleased, live - selfReleased * 0,
              selfReleased, coreReleased, coreLive, borrowed);
  if (!std::strcmp(argv[2], "D1")) {
    receiver = nullptr;
    ::operator delete(p);
  }
}
