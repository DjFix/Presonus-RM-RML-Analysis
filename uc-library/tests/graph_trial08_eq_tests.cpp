#include "presonus/mixer_dsp/EQControl.hpp"
#include <cstring>
#include <iostream>
namespace Presonus {
class BackgroundPainter {};
} // namespace Presonus
struct TracedParam : Core::Portable::NumericParam {
  mutable int reads = 0;
  using Core::Portable::NumericParam::NumericParam;
  Core::Portable::ParamValue getValue() const override {
    ++reads;
    return Core::Portable::NumericParam::getValue();
  }
};
struct Draw : presonus::dsp::EQControlDrawBoundary {
  int releases = 0, inits = 0;
  void releaseBuffer() override { ++releases; }
  void initBands(Presonus::EQControl &) override { ++inits; }
};
int main() {
  int target, index, count;
  while (std::cin >> target >> index >> count) {
    Presonus::EQControl eq(presonus::dsp::EQControlBiquadPortTag{});
    if (target == 7) {
      std::string text;
      std::getline(std::cin, text);
      if (!text.empty())
        text.erase(0, 1);
      std::cout << eq.parseType(Core::ConstString(text.c_str())) << '\n';
      continue;
    }
    if (target == 1 || target == 3) {
      float value;
      std::cin >> value;
      Core::LinearInterpolator normal(target == 1 ? 20.f : -12.f,
                                      target == 1 ? 20000.f : 12.f),
          pixel(target == 1 ? 10.f : 20.f, target == 1 ? 110.f : 220.f);
      eq.bindPortableInterpolators(normal, pixel, normal, pixel);
      std::cout << (target == 1 ? eq.freqToX(value) : eq.gainToY(value))
                << '\n';
      continue;
    }
    if (target == 6) {
      Presonus::BackgroundPainter painter;
      for (int i = 0; i < count; ++i)
        eq.addBackgroundPainter(painter);
      eq.addBackgroundPainter(painter);
      const auto &v = eq.portableBackgroundPainters();
      std::cout << v.count() << ' ' << (v.at(count) == &painter) << '\n';
      continue;
    }
    if (target >= 8 && target <= 10) {
      int present;
      std::cin >> present;
      Core::Portable::ParamInfo info{};
      info.type = Core::Portable::ParamInfo::kFloat;
      info.minValue = -100;
      info.maxValue = 100;
      info.defaultValue = 11.25f;
      TracedParam param(info);
      eq.portableParameterState().resize(count);
      for (auto &b : eq.portableParameterState())
        if (present)
          b.gain = b.q = b.frequency = &param;
      float result = target == 8
                         ? eq.getFrequency(index)
                         : (target == 9 ? eq.getGain(index) : eq.getQ(index));
      unsigned bits;
      std::memcpy(&bits, &result, 4);
      std::cout << bits << ' ' << param.reads << '\n';
      continue;
    }
    if (target == 4) {
      int valid;
      std::cin >> valid;
      Draw draw;
      eq.bindPortableDrawBoundary(draw);
      eq.setPortableBufferState(count, valid);
      eq.setBufferedDraw(index);
      std::cout << eq.portableBufferedDraw() << ' '
                << eq.portableBufferPresent() << ' ' << eq.portableBufferValid()
                << ' ' << draw.releases << ' ' << draw.inits << '\n';
      continue;
    }
    auto &bands = eq.portableBandState();
    bands.resize(count);
    for (auto &b : bands) {
      int on, enabled, dirty;
      std::cin >> on >> enabled >> dirty;
      b.on = on;
      b.enabled = enabled;
      b.dirty = dirty;
    }
    if (target == 2)
      eq.markBandDirty(index);
    std::cout << (target == 5 ? static_cast<int>(eq.isAnyBandOn()) : -1);
    for (auto &b : bands)
      std::cout << ' ' << static_cast<int>(b.dirty);
    std::cout << '\n';
  }
}
