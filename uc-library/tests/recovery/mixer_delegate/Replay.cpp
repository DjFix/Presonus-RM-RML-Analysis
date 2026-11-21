#include "presonus/mixer/MixerComponentBaseDelegate.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
namespace {
// Address tokens for the list fixture. These cases do not dispatch callbacks.
class DelegateIdentity final
    : public Presonus::Mixer::MixerComponentBase::Delegate {
public:
  void clientsChanged() override {}
  void notifyStoring(bool) override {}
  void faderLocateDirty(Presonus::Mixer::ChannelComponent *) override {}
};
bool failNext = false;
} // namespace
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
    std::array<DelegateIdentity, 3> tokens;
    DelegateIdentity extra;
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
      if (p == &extra) {
        std::cout << " 99";
        continue;
      }
      const auto match =
          std::find_if(tokens.begin(), tokens.end(),
                       [p](const auto &token) { return p == &token; });
      assert(match != tokens.end());
      std::cout << ' ' << (match - tokens.begin());
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
