#include "presonus/mixer_dsp/EQControl.hpp"
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
struct TraceParam : Core::Portable::NumericParam {
  std::vector<std::string> &calls;
  int id;
  TraceParam(const Core::Portable::ParamInfo &info,
             std::vector<std::string> &calls, int id)
      : NumericParam(info), calls(calls), id(id) {}
  bool hasObserver(Core::Portable::IParamObserver *p) const {
    return observerList.contains(p);
  }
  float getValue() const override {
    calls.push_back("value");
    return NumericParam::getValue();
  }
  float getMin() const override {
    calls.push_back("minimum");
    return NumericParam::getMin();
  }
  void setValue(float value, bool edit) override {
    unsigned bits;
    std::memcpy(&bits, &value, 4);
    calls.push_back("set:" + std::to_string(id) + ":" + std::to_string(bits) +
                    ":" + std::to_string(edit));
    NumericParam::setValue(value, edit);
  }
};
struct Renderer : Core::Portable::ColorBitmapRenderer {
  std::vector<std::string> &calls;
  Renderer(Core::Portable::Bitmap &bitmap, std::vector<std::string> &calls)
      : ColorBitmapRenderer(bitmap), calls(calls) {}
  bool drawLine(Core::PointRef a, Core::PointRef b,
                Core::ColorRef color) override {
    calls.push_back("line:" + std::to_string(a.x) + ":" + std::to_string(a.y) +
                    ":" + std::to_string(b.x) + ":" + std::to_string(b.y));
    return ColorBitmapRenderer::drawLine(a, b, color);
  }
};
struct DrawBoundary : presonus::dsp::EQControlDrawBoundary {
  int releases = 0, inits = 0;
  void releaseBuffer() override { ++releases; }
  void initBands(Presonus::EQControl &) override { ++inits; }
};
int main() {
  int target, count, index, present, primary, kind, x, y, width, height;
  float value, minimum;
  while (std::cin >> target >> count >> index >> present >> value >> minimum >>
         primary >> kind >> x >> y >> width >> height) {
    std::vector<std::string> calls;
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = minimum;
    info.maxValue = 100;
    TraceParam p(info, calls, 0), p5(info, calls, 1);
    p.setValueFast(value);
    calls.clear();
    Presonus::EQControl eq(presonus::dsp::EQControlBiquadPortTag{});
    Core::Portable::View view(Core::Rect(0, 0, width, height));
    eq.bindPortableView(view);
    eq.bindPortablePrimaryParameter(primary ? &p : nullptr);
    Core::LinearInterpolator freq(20.f, 20000.f), fx(10.f, 110.f),
        gain(-12.f, 12.f), gy(20.f, 220.f);
    eq.bindPortableInterpolators(freq, fx, gain, gy);
    eq.portableParameterState().resize(count);
    eq.portableBandState().resize(count);
    eq.bindPortableTypeParameters(std::vector<Core::Portable::Parameter *>(
        count, present ? &p : nullptr));
    for (int i = 0; i < count; ++i) {
      int enabled, slot5, slot4;
      float frequency;
      std::cin >> enabled >> frequency >> slot5 >> slot4;
      auto &b = eq.portableBandState()[i];
      b.enabled = enabled;
      b.frequency = frequency;
      eq.portableParameterState()[i].slot5 = slot5 ? &p5 : nullptr;
      eq.portableParameterState()[i].slot4 = slot4 ? &p : nullptr;
    }
    if (target == 2) {
      int message;
      std::cin >> message;
      std::vector<Core::Portable::Parameter *> types;
      for (int i = 0; i < count; ++i) {
        Core::Portable::Parameter *slots[6];
        for (auto &slot : slots) {
          int id;
          std::cin >> id;
          slot = id == 0 ? nullptr : (id == 1 ? &p : &p5);
        }
        types.push_back(slots[0]);
        auto &params = eq.portableParameterState()[i];
        params.gain = slots[1];
        params.q = slots[2];
        params.frequency = slots[3];
        params.slot4 = slots[4];
        params.slot5 = slots[5];
        eq.portableBandState()[i].dirty = 7;
        eq.portableBandState()[i].enabled = true;
      }
      eq.bindPortableTypeParameters(types);
      Core::Portable::Control control(Core::Rect(0, 0, width, height),
                                      primary ? &p : &p5);
      eq.bindPortableControl(control);
      p.setValueFast(11.f);
      p5.setValueFast(22.f);
      p.addObserver(eq.portableObserver());
      eq.paramChanged(&p, message);
      // Probe type binding through getType independently after callbacks.
      for (int i = 0; i < count; ++i) {
        int type = eq.getType(i);
        auto &params = eq.portableParameterState()[i];
        auto id = [&](Core::Portable::Parameter *slot) {
          return slot == nullptr ? 0 : (slot == &p ? 1 : 2);
        };
        std::cout << (type == 0 ? 0 : (type == 11 ? 1 : 2)) << ' '
                  << id(params.gain) << ' ' << id(params.q) << ' '
                  << id(params.frequency) << ' ' << id(params.slot4) << ' '
                  << id(params.slot5) << ' ';
      }
      for (auto &b : eq.portableBandState())
        std::cout << static_cast<int>(b.dirty) << ' ';
      for (auto &b : eq.portableBandState())
        std::cout << b.enabled << ' ';
      std::cout << p.hasObserver(eq.portableObserver()) << '\n';
      p.removeObserver(eq.portableObserver());
      continue;
    }
    if (target == 3 || target == 4) {
      DrawBoundary boundary;
      eq.bindPortableDrawBoundary(boundary);
      eq.setBufferedDraw(present != 0);
      if (target == 4) {
        eq.portableParameterState().clear();
        eq.initBands();
        if (kind == 2)
          eq.initBands();
        std::cout << count << ' ' << eq.portableParameterState().size() << ' '
                  << eq.portableBufferPresent() << ' '
                  << eq.portableBufferValid();
        if (width > 0 && height > 0) {
          for (const auto &b : eq.portableBandState())
            std::cout << ' ' << static_cast<int>(b.dirty);
          for (const auto &b : eq.portableBandState())
            std::cout << ' ' << b.enabled;
          for (const auto &curve : eq.portableBandCurves())
            std::cout << ' ' << curve.size();
        }
        bool az = true, pz = true;
        for (float sample : eq.portableAmplitudeCurve())
          az &= sample == 0.f;
        for (int sample : eq.portablePixelCurve())
          pz &= sample == 0;
        std::cout << ' ' << az << ' ' << pz << '\n';
      } else {
        int left, top, right, bottom;
        std::cin >> left >> top >> right >> bottom;
        for (int i = 0; i < width; ++i) {
          float sample;
          std::cin >> sample;
          eq.portableAmplitudeCurve().push_back(sample);
          eq.portablePixelCurve().push_back(static_cast<int>(sample));
        }
        for (auto &b : eq.portableBandState())
          b.on = primary;
        Core::Portable::Bitmap bitmap(8, 80);
        Renderer renderer(bitmap, calls);
        Core::Portable::DrawEvent event(renderer,
                                        Core::Rect(left, top, right, bottom));
        eq.drawCurve(event, Core::Color(255, 0, 0), false);
        std::cout << calls.size();
        for (const auto &call : calls)
          std::cout << ' ' << call;
        std::cout << '\n';
      }
      continue;
    }
    int result = 0;
    if (target == 5)
      result = eq.toXGridPixel(value);
    else if (target == 6)
      result = eq.toYGridPixel(value);
    else if (target == 7)
      result = eq.getBandEnabled(index);
    else if (target == 9)
      result = eq.getType(index);
    else if (target == 8)
      result = eq.getBandForPoint(Core::Point(x, y));
    else if (target == 1)
      result = eq.onTouchInput(Core::Portable::TouchEvent(
          static_cast<Core::Portable::TouchEvent::Type>(kind),
          Core::Point(x, y)));
    else
      return 2;
    std::cout << result << ' ' << calls.size();
    for (const auto &call : calls)
      std::cout << ' ' << call;
    std::cout << '\n';
  }
}
