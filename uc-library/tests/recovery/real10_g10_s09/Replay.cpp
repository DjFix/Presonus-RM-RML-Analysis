#include "presonus/MeterScaleControl.hpp"
#include <cstdio>
#include <new>
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdaPv(void *);
namespace {
void *owned[8];
int n, released, arrays;
} // namespace
extern "C" void __wrap__ZdlPv(void *p) {
  for (int i = 0; i < n; ++i)
    if (p == owned[i])
      ++released;
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdaPv(void *p) {
  if (p)
    ++arrays;
  __real__ZdaPv(p);
}
int main() {
  for (int count : {0, 1, 3, 8}) {
    n = count;
    released = arrays = 0;
    {
      Presonus::MeterScaleControl::Ranges r(
          Presonus::MeterScaleControl::Ranges::SourcePortTag{});
      for (int i = 0; i < n; ++i) {
        owned[i] = ::operator new(16);
        if (!r.adoptRawAllocation(owned[i]))
          return 2;
      }
      // Observe only destruction, excluding capacity-growth cleanup.
      arrays = 0;
    }
    if (released != n || arrays != (n ? 1 : 0))
      return 3;
    std::printf("%d %d\n", released, arrays);
  }
}
