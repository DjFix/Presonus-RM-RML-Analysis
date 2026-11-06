#include "core/public/corevector.h"
#include "presonus/DAWTimeInfo.hpp"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <stdexcept>
#include <utility>
#include <vector>

namespace {
int liveArrays = 0, allocations = 0, frees = 0;
bool failArray = false;
struct Probe {
  static int live;
  int value = 0;
  Probe() { ++live; }
  ~Probe() { --live; }
};
int Probe::live = 0;
void require(bool value) {
  if (!value)
    throw std::runtime_error("replay mismatch");
}
} // namespace
// Observe actual pinned provider allocations, destruction and allocation
// failure.
void *operator new[](std::size_t size) {
  if (failArray)
    throw std::bad_alloc();
  void *p = std::malloc(size ? size : 1);
  if (!p)
    throw std::bad_alloc();
  ++liveArrays;
  ++allocations;
  return p;
}
void operator delete[](void *p) noexcept {
  if (p) {
    --liveArrays;
    ++frees;
    std::free(p);
  }
}
void operator delete[](void *p, std::size_t) noexcept {
  ::operator delete[](p);
}
int main() {
  using S = Presonus::DAWTimeInfo::TimeSignatureMap;
  using T = Presonus::DAWTimeInfo::TempoMap;
  int cases = 0;
  for (int delta : {16, 64}) {
    {
      Core::Vector<Probe> v(delta, delta);
      require(v.count() == 0 && v.getCapacity() == delta &&
              v.getDelta() == delta);
      require(Probe::live == delta);
      require(v.resize(delta + 1));
      require(v.getCapacity() == delta * 2 && Probe::live == delta * 2);
      require(v.resize(0));
      require(Probe::live == 0 && v.count() == 0 && v.getCapacity() == 0);
    }
    require(Probe::live == 0);
    ++cases;
  }
  for (int n : {0, 1, 15, 16, 17, 63, 64, 65, 129}) {
    const int initialArrays = liveArrays;
    S sig;
    T tempo;
    require(liveArrays == initialArrays + 2);
    require(sig.itemCount() == 0 && sig.ownedCapacity() == 16 &&
            sig.allocationDelta() == 16);
    require(tempo.itemCount() == 0 && tempo.ownedCapacity() == 64 &&
            tempo.allocationDelta() == 64);
    require(sig.findItem(0) != nullptr && tempo.findItem(0) == nullptr &&
            tempo.secondsToPpq(2) == 4);
    std::vector<S::Item> si(n);
    std::vector<T::Item> ti(n);
    for (int i = 0; i < n; ++i) {
      si[i] = {double(i * 4), 3, 4, i};
      ti[i] = {double(i * 4), .5, double(i * 2)};
    }
    sig.replaceOwnedItems(si.data(), n);
    tempo.replaceOwnedItems(ti.data(), n);
    require(sig.itemCount() == n && tempo.itemCount() == n);
    require(sig.ownedCapacity() == (n ? ((n - 1) / 16 + 1) * 16 : 0));
    require(tempo.ownedCapacity() == (n ? ((n - 1) / 64 + 1) * 64 : 0));
    for (int i = 0; i < n; ++i) {
      require(sig.findItem(i * 4) == sig.findItemByBar(i));
      require(tempo.secondsToPpq(i * 2) == i * 4);
      ++cases;
    }
    S scopy = sig;
    T tcopy = tempo;
    const auto *sp = scopy.findItem(0), *tp = tcopy.findItem(0);
    sig.replaceOwnedItems(nullptr, 0);
    tempo.replaceOwnedItems(nullptr, 0);
    require(scopy.itemCount() == n && tcopy.itemCount() == n &&
            scopy.findItem(0) == sp && tcopy.findItem(0) == tp);
    {
      S moved = std::move(scopy);
      T tmoved = std::move(tcopy);
      require(moved.findItem(0) == sp && tmoved.findItem(0) == tp);
    }
    require(scopy.findItem(0) == sp && tcopy.findItem(0) == tp);
    S assigned(nullptr, 0);
    T ta(nullptr, 0);
    assigned = scopy;
    ta = tcopy;
    require(assigned.findItem(0) == sp && ta.findItem(0) == tp);
    for (int invalid : {-1, 1}) {
      try {
        sig.replaceOwnedItems(nullptr, invalid);
        require(false);
      } catch (const std::invalid_argument &) {
      }
      require(sig.itemCount() == 0);
    }
    try {
      sig.replaceOwnedItems(nullptr, 2147483647);
      require(false);
    } catch (const std::invalid_argument &) {
    }
    ++cases;
  }
  {
    S sig;
    T tempo;
    S::Item s{0, 4, 4, 0};
    T::Item t{0, .5, 0};
    sig.replaceOwnedItems(&s, 1);
    tempo.replaceOwnedItems(&t, 1);
    auto sp = sig.findItem(0), tp = tempo.findItem(0);
    int before = liveArrays;
    failArray = true;
    try {
      sig.replaceOwnedItems(&s, 1);
      require(false);
    } catch (const std::bad_alloc &) {
    }
    try {
      tempo.replaceOwnedItems(&t, 1);
      require(false);
    } catch (const std::bad_alloc &) {
    }
    try {
      S failed;
      require(false);
    } catch (const std::bad_alloc &) {
    }
    try {
      T failed;
      require(false);
    } catch (const std::bad_alloc &) {
    }
    failArray = false;
    require(liveArrays == before && sig.findItem(0) == sp &&
            tempo.findItem(0) == tp);
    ++cases;
  }
  {
    S map;
    S::Item item;
    try {
      map.replaceOwnedItems(&item, 2147483647);
      require(false);
    } catch (const std::length_error &) {
    }
    require(map.itemCount() == 0 && map.ownedCapacity() == 16);
  }
  require(liveArrays == 0 && allocations == frees);
  std::cout << "PASS " << cases
            << " provider/owned-map cases; array allocations=" << allocations
            << " frees=" << frees << "; no live arrays\n";
}
