#include "fixtures.hpp"
#include "presonus/VUMeterControl.hpp"
#include <cassert>
#include <cmath>
#include <cstring>
#include <iostream>
using namespace Core;
using namespace Core::Portable;
static std::uint64_t ticks = 100000000000ULL;
extern "C" std::uint64_t
capturedClock() asm("__wrap__ZN8presonus4dice19packetClockRawTicksEv");
extern "C" std::uint64_t capturedClock() { return ticks; }
extern "C" BitmapReference noResource(const Attributes &, const char *) asm(
    "__wrap__ZN4Core8Portable14ViewAttributes9getBitmapERKNS0_"
    "10AttributesEPKc");
extern "C" BitmapReference noResource(const Attributes &, const char *) {
  return BitmapReference();
}
class Meter final : public Presonus::VUMeterControl {
public:
  Meter() : VUMeterControl(Rect(0, 0, 8, 8)) {}
  int invalidations = 0;
  using VUMeterControl::invalidate;
  void invalidate(RectRef) override { ++invalidations; }
};
int main() {
  unsigned attrsCases = 0, idleCount = 0;
  for (const auto &c : attributeCases) {
    Meter m;
    float initial[] = {.2f, .4f};
    m.portableBindThresholds(initial, 2);
    m.portableBindDrawState(0, 0, 7, c.base);
    DefaultAllocatedAttributes a;
    a.set("options", c.parsed ? "reverse" : "");
    if (c.text)
      a.set("dbtable", c.text, true);
    m.setAttributes(a);
    assert((m.portableState().options & 0x400000) == (c.base | c.parsed));
    assert(m.portableThresholdCount() == c.count);
    for (int i = 0; i < c.count; ++i) {
      float f = m.portableThreshold(i);
      std::uint32_t bits;
      std::memcpy(&bits, &f, 4);
      assert(bits == c.bits[i] ||
             (std::isnan(f) && (c.bits[i] & 0x7fffffff) > 0x7f800000));
    }
    ++attrsCases;
  }
  for (const auto &c : idleCases) {
    Meter m;
    m.portableBindFrameState(0, 7, 0, c.dirty);
    m.portableBindTimer({0, 40, c.elapsed ? 40 : 39, .025f, false});
    m.onIdle();
    assert(m.portableDirty() == c.after);
    assert(m.invalidations == int(c.invalidate));
    if (c.elapsed) {
      auto t = m.portableTimer();
      assert(t.executing && t.start == 100000 && t.elapsed == 0 &&
             t.duration == 40);
      int n = m.invalidations;
      m.onIdle();
      assert(m.invalidations == n);
    }
    ++idleCount;
  }
  std::cout << "{\"passed\":true,\"attribute_cases\":" << attrsCases
            << ",\"idle_cases\":" << idleCount << "}\n";
}
