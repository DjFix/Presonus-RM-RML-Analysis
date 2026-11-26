#include "core/portable/coreparams.h"
#include "presonus/GRMeterMaid.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace presonus::meter {
struct MeterStateAccess {
  static auto &state(Presonus::MeterBallistics &m) { return m.state_; }
  static auto &table(Presonus::MeterBallistics &m) { return m.decayTable_; }
};
} // namespace presonus::meter
namespace {
using Core::Portable::NumericParam;
using Core::Portable::ParamInfo;
using Core::Portable::ParamValue;
using presonus::meter::MeterStateAccess;
unsigned bits(float x) { return std::bit_cast<unsigned>(x); }
float fl(unsigned x) { return std::bit_cast<float>(x); }
struct Event {
  unsigned tag, value;
};
std::vector<Event> traceEffects, calls;
class Param final : public NumericParam {
public:
  Param(const ParamInfo &i, unsigned slot) : NumericParam(i), slot(slot) {}
  void setValue(ParamValue v, bool edit) override {
    if (edit)
      std::abort();
    calls.push_back({slot, bits(v)});
    NumericParam::setValue(v, edit);
  }
  ParamValue getValue() const override {
    auto v = NumericParam::getValue();
    calls.push_back({slot + 4, bits(v)});
    return v;
  }
  float peek() const { return NumericParam::getValue(); }
  unsigned slot;
};
class Meter final : public Presonus::GRMeterMaid {
public:
  bool isClipped() const override {
    traceEffects.push_back({0, 0});
    return MeterMaid::isClipped();
  }
  void setClipped(bool v) override {
    traceEffects.push_back({1, static_cast<unsigned>(v)});
    MeterMaid::setClipped(v);
  }
  void setSignal(bool v) override {
    traceEffects.push_back({2, static_cast<unsigned>(v)});
    MeterMaid::setSignal(v);
  }
  void setMeter(float v) override {
    traceEffects.push_back({3, bits(v)});
    MeterMaid::setMeter(v);
  }
  void setPeak(float v) override {
    traceEffects.push_back({4, bits(v)});
    MeterMaid::setPeak(v);
  }
};
} // namespace
int main(int argc, char **argv) {
  if (argc != 2)
    return 1;
  if (std::string(argv[1]) == "direct") {
    Presonus::MeterBallistics base;
    Presonus::MeterMaid maid;
    Presonus::GRMeterMaid gr;
    if (!MeterStateAccess::table(base) || !MeterStateAccess::table(maid) ||
        MeterStateAccess::table(gr))
      return 3;
    base.setMeter(.25f);
    base.setPeak(.75f);
    base.setSignal(true);
    base.setClipped(true);
    if (base.effects().meter != .25f || base.effects().peak != .75f ||
        !base.effects().signal || !base.isClipped())
      return 4;
    base.setClipped(false);
    if (base.setLevel(.5f) != .5f || base.effects().meter != .5f ||
        base.effects().peak != .5f || base.isClipped() ||
        !base.effects().signal)
      return 5;
    base.reset();
    if (base.getPeakHold() != 0.f || !MeterStateAccess::table(base) ||
        !MeterStateAccess::table(maid))
      return 6;
    std::cout << "direct base compatibility: concrete effects, default table, "
                 "reset passed\n";
    return 0;
  }
  std::string method = argv[1];
  std::array<unsigned, 12> p;
  while (std::cin >> p[0]) {
    for (unsigned i = 1; i < p.size(); ++i)
      if (!(std::cin >> p[i]))
        return 2;
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.minValue = -100.f;
    info.maxValue = 100.f;
    info.defaultValue = fl(p[11]);
    Param meter(info, 0), peak(info, 1), signal(info, 2), clip(info, 3);
    Meter m;
    if (p[1]) {
      static Presonus::MeterBallistics base;
      MeterStateAccess::table(m) = MeterStateAccess::table(base);
    }
    m.bindParameters(p[0] ? &meter : nullptr, p[0] ? &peak : nullptr);
    m.bindIndicatorParameters(p[0] ? &signal : nullptr, p[0] ? &clip : nullptr);
    auto &s = MeterStateAccess::state(m);
    s.active = p[2];
    s.amplitude = fl(p[3]);
    s.peakHold = fl(p[4]);
    for (unsigned i = 0; i < 4; ++i)
      s.auxiliary[i] = p[5 + i];
    s.decayRate = fl(p[9]);
    traceEffects.clear();
    calls.clear();
    float result = method == "idle" ? m.idleSetLevel(fl(p[10]))
                   : method == "base"
                       ? m.Presonus::MeterBallistics::setLevel(fl(p[10]))
                       : m.setLevel(fl(p[10]));
    std::cout << bits(result) << ' ' << bits(s.amplitude) << ' '
              << bits(s.peakHold);
    for (auto v : s.auxiliary)
      std::cout << ' ' << v;
    for (auto *v : {&meter, &peak, &signal, &clip})
      std::cout << ' ' << bits(v->peek());
    std::cout << ' ' << traceEffects.size();
    for (auto e : traceEffects)
      std::cout << ' ' << e.tag << ' ' << e.value;
    std::cout << ' ' << calls.size();
    for (auto e : calls)
      std::cout << ' ' << e.tag << ' ' << e.value;
    std::cout << '\n';
  }
}
