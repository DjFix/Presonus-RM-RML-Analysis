#include "presonus/IFaderUnit.hpp"
#include <cstdio>
#include <cstdlib>
#include <new>
extern "C" void __real__ZdlPv(void *);
namespace {
void *watched;
int releases;
} // namespace
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == watched)
    ++releases;
  __real__ZdlPv(p);
}
int main() {
  for (int i = 0; i < 8; ++i) {
    auto *p = new Presonus::IFaderUnit(Presonus::IFaderUnit::SourcePortTag{});
    watched = p;
    releases = 0;
    delete p;
    if (releases != 1)
      return 1;
    std::printf("1\n");
  }
}
