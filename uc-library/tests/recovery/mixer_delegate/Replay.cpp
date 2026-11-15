#include "presonus/mixer/MixerComponentBase.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
// Test-only identity tokens: production only borrows opaque Delegate addresses.
// No original Delegate layout or virtual behavior is modeled.
namespace Presonus::Mixer {
class MixerComponentBase::Delegate {};
} // namespace Presonus::Mixer
namespace {
bool failNext = false;
}
void *operator new[](std::size_t n) {
  if (failNext) {
    failNext = false;
    throw std::bad_alloc();
  }
  if (void *p = std::malloc(n ? n : 1))
    return p;
  throw std::bad_alloc();
}
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
int main() {
  using Presonus::Mixer::MixerComponentBase;
  int n, capacity, fail, duplicate;
  while (std::cin >> n >> capacity >> fail >> duplicate) {
    MixerComponentBase owner;
    MixerComponentBase::Delegate tokens[3], extra;
    owner.delegates.setDelta(1);
    assert(owner.delegates.resize(capacity));
    for (int i = 0; i < n; ++i)
      assert(owner.delegates.add(&tokens[i]));
    failNext = fail && n == capacity;
    owner.addDelegate(duplicate ? tokens[0] : extra);
    failNext = false;
    std::cout << owner.delegates.count();
    for (int i = 0; i < owner.delegates.count(); ++i) {
      auto *p = owner.delegates.at(i);
      std::cout << ' ' << (p == &extra ? 99 : int(p - tokens));
    }
    std::cout << '\n';
    if (owner.delegates.count()) {
      auto *first = owner.delegates.at(0);
      int before = owner.delegates.count();
      owner.removeDelegate(*first);
      assert(owner.delegates.count() == before - 1);
    }
  }
}
