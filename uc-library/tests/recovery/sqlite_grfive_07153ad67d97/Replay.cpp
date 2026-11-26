#include "core/portable/coreparams.h"
#include "presonus/GRMeterMaid.hpp"
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
namespace presonus::meter {
struct MeterStateAccess {
  static auto &state(Presonus::MeterBallistics &m) { return m.state_; }
  static auto *table(Presonus::MeterBallistics &m) { return m.decayTable_; }
  static bool empty(Presonus::MeterMaid &m) {
    return !m.meter_ && !m.peak_ && !m.signal_ && !m.clip_;
  }
};
} // namespace presonus::meter
extern "C" void c1(void *) asm("_ZN8Presonus11GRMeterMaidC1Ev");
extern "C" void c2(void *) asm("_ZN8Presonus11GRMeterMaidC2Ev");
extern "C" void d1(void *) asm("_ZN8Presonus11GRMeterMaidD1Ev");
extern "C" void d0(void *) asm("_ZN8Presonus11GRMeterMaidD0Ev");
namespace {
void *expected = nullptr;
unsigned deleted = 0;
} // namespace
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == expected) {
    if (!p || deleted)
      std::abort();
    ++deleted;
    expected = nullptr;
  }
  __real__ZdlPv(p);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 1;
  std::string variant = argv[1];
  using namespace Presonus;
  using presonus::meter::MeterStateAccess;
  unsigned seed, bound;
  while (std::cin >> seed >> bound) {
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = 0;
    info.maxValue = 1;
    info.defaultValue = .25f;
    Core::Portable::NumericParam param(info);
    alignas(GRMeterMaid) unsigned char store[sizeof(GRMeterMaid)];
    void *storage =
        variant == "D0" ? ::operator new(sizeof(GRMeterMaid)) : store;
    auto *m = reinterpret_cast<GRMeterMaid *>(storage);
    if (variant == "C2")
      c2(storage);
    else
      c1(storage);
    if (MeterStateAccess::table(*m) || !MeterStateAccess::empty(*m))
      return 2;
    if (variant[0] == 'C') {
      const auto &s = MeterStateAccess::state(*m);
      std::cout << s.mode << ' ' << std::bit_cast<unsigned>(s.scale) << ' '
                << std::bit_cast<unsigned>(s.decayRate) << ' ' << s.active
                << ' ' << std::bit_cast<unsigned>(s.amplitude) << ' '
                << std::bit_cast<unsigned>(s.peakHold);
      for (auto v : s.auxiliary)
        std::cout << ' ' << v;
      std::cout << " 0 0 0 0";
      MeterStateAccess::state(*m).amplitude = .5f;
      MeterStateAccess::state(*m).peakHold = .5f;
      std::cout << ' ' << std::bit_cast<unsigned>(m->getDecayDelta()) << ' '
                << std::bit_cast<unsigned>(m->getPeakDecayDelta()) << '\n';
      d1(storage);
    } else {
      if (bound) {
        m->bindParameters(&param, &param);
        m->bindIndicatorParameters(&param, &param);
      }
      MeterStateAccess::state(*m).auxiliary.fill(seed);
      deleted = 0;
      expected = variant == "D0" ? m : nullptr;
      if (variant == "D0")
        d0(m);
      else
        d1(m);
      if (deleted != unsigned(variant == "D0") || expected ||
          param.getValue() != .25f)
        return 3;
      std::cout << deleted << ' ' << bound << " 1\n";
    }
  }
}
