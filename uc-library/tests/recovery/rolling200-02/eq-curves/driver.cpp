#include "core/system/coretime.h"
#include "presonus/mixer_dsp/EQControl.hpp"
#include <ctime>
#include <iomanip>
#include <iostream>
#include <memory>
#include <vector>
static bool controlled = false;
static std::int64_t nowNanoseconds;
extern "C" int __real_clock_gettime(clockid_t, timespec *);
extern "C" int __wrap_clock_gettime(clockid_t id, timespec *result) {
  if (!controlled || id != CLOCK_MONOTONIC)
    return __real_clock_gettime(id, result);
  result->tv_sec = nowNanoseconds / 1000000000;
  result->tv_nsec = nowNanoseconds % 1000000000;
  return 0;
}
struct DrawBoundary : presonus::dsp::EQControlDrawBoundary {
  void releaseBuffer() override {}
  void initBands(Presonus::EQControl &eq) override { eq.initBands(); }
};
struct ObservedView : Core::Portable::View {
  using View::invalidate;
  using View::View;
  int invalidations = 0;
  void invalidate(Core::RectRef rectangle) override {
    ++invalidations;
    Core::Portable::View::invalidate(rectangle);
  }
};
int main() {
  std::cout << std::setprecision(10);
  int target;
  while (std::cin >> target) {
    Presonus::EQControl eq(presonus::dsp::EQControlBiquadPortTag{});
    ObservedView view(Core::Rect(0, 0, 8, 80));
    Core::Portable::Control control(Core::Rect(0, 0, 8, 80));
    eq.bindPortableView(view);
    eq.bindPortableControl(control);
    Core::LinearInterpolator fn(20.f, 20000.f), fx(10.f, 110.f),
        gn(-12.f, 12.f), gy(20.f, 220.f);
    eq.bindPortableInterpolators(fn, fx, gn, gy);
    if (target == 1) {
      int count;
      std::cin >> count;
      eq.setNumBands(count);
      std::cout << eq.portableRequestedBandCount() << ' '
                << eq.portableBandState().size() << ' '
                << eq.portableParameterState().size() << ' '
                << eq.portableAmplitudeCurve().size();
      for (auto &band : eq.portableBandState())
        std::cout << ' ' << int(band.dirty);
      std::cout << '\n';
    } else if (target == 2) {
      Core::Rect rect;
      std::cin >> rect.left >> rect.top >> rect.right >> rect.bottom;
      eq.portableBandState().resize(1);
      eq.setSize(rect);
      Core::Rect observed = view.getSize();
      std::cout << observed.left << ' ' << observed.top << ' ' << observed.right
                << ' ' << observed.bottom << ' '
                << eq.portableAmplitudeCurve().size() << '\n';
    } else if (target == 5) {
      std::int64_t last;
      std::cin >> last >> nowNanoseconds;
      eq.portableLastCurveTime() = last;
      eq.portableBandState().resize(1);
      eq.initBands();
      controlled = true;
      const auto providerNow = Core::SystemClock::getTime();
      eq.onIdle();
      controlled = false;
      std::cout << eq.portableLastCurveTime() << ' ' << providerNow << ' '
                << int(eq.portableBandState()[0].dirty) << '\n';
    } else if (target == 3 || target == 4) {
      int type, index, samples, present, buffered;
      float q, frequency, gain, minimum, maximum;
      std::cin >> type >> index >> samples >> present >> q >> frequency >>
          gain >> minimum >> maximum >> buffered;
      int count = 1;
      if (target == 4)
        std::cin >> count;
      if (target == 4)
        view.setSize(Core::Rect(0, 0, samples, 80));
      eq.portableBandState().resize(static_cast<unsigned>(count));
      DrawBoundary boundary;
      eq.bindPortableDrawBoundary(boundary);
      eq.setBufferedDraw(buffered != 0);
      Core::Portable::ParamInfo info{};
      info.type = Core::Portable::ParamInfo::kFloat;
      info.minValue = -200000.f;
      info.maxValue = 200000.f;
      std::vector<std::unique_ptr<Core::Portable::NumericParam>> parameters;
      auto param = [&](float value) {
        parameters.push_back(
            std::make_unique<Core::Portable::NumericParam>(info));
        parameters.back()->setValueFast(value);
        return parameters.back().get();
      };
      std::vector<Core::Portable::Parameter *> types;
      if (samples > 0 && target == 4) {
        std::fill(eq.portableAmplitudeCurve().begin(),
                  eq.portableAmplitudeCurve().end(), 99.f);
        std::fill(eq.portablePixelCurve().begin(),
                  eq.portablePixelCurve().end(), 777);
      }
      for (int i = 0; i < count; ++i) {
        float bt = static_cast<float>(type), bg = gain, bq = q, bf = frequency,
              on = 1, initialFrequency = 0, initialGain = 0, initialCurve = 123;
        int dirty = 1, force = 0, initialOn = 0, initialEnabled = 0;
        if (target == 4)
          std::cin >> bt >> bg >> bq >> bf >> on >> dirty >> force >>
              initialOn >> initialEnabled >> initialFrequency >> initialGain >>
              initialCurve;
        types.push_back(present ? param(bt) : nullptr);
        if (i >= static_cast<int>(eq.portableParameterState().size()))
          eq.portableParameterState().resize(i + 1);
        auto &p = eq.portableParameterState()[i];
        p.gain = param(bg);
        p.q = param(bq);
        p.frequency = param(bf);
        p.slot4 = param(on);
        static_cast<Core::Portable::NumericParam *>(p.slot4)->setMin(0.f);
        auto &band = eq.portableBandState()[i];
        band.dirty = static_cast<std::uint8_t>(dirty);
        band.forceCurve = force != 0;
        band.on = initialOn != 0;
        band.enabled = initialEnabled != 0;
        band.frequency = initialFrequency;
        band.gain = initialGain;
        if (target == 4 && samples > 0)
          std::fill(eq.portableBandCurveStorage()[i].begin(),
                    eq.portableBandCurveStorage()[i].end(), initialCurve);
      }
      eq.bindPortableTypeParameters(types);
      eq.bindPortableCurveRange(minimum, maximum);
      if (target == 3) {
        std::vector<float> curve(static_cast<unsigned>(std::max(samples, 0)),
                                 123.f);
        bool result = eq.getCurve(curve.data(), index, samples);
        std::cout << result;
        for (float sample : curve)
          std::cout << ' ' << sample;
      } else {
        eq.setPortableBufferState(eq.portableBufferPresent(), false);
        view.invalidations = 0;
        eq.rebuildCurves();
        std::cout << eq.portableBufferValid() << ' ' << view.invalidations;
        for (const auto &band : eq.portableBandState())
          std::cout << ' ' << int(band.dirty) << ' ' << band.on << ' '
                    << band.enabled << ' ' << band.frequency << ' ' << band.gain
                    << ' ' << band.x << ' ' << band.y;
        for (float sample : eq.portableAmplitudeCurve())
          std::cout << ' ' << sample;
        for (int pixel : eq.portablePixelCurve())
          std::cout << ' ' << pixel;
      }
      std::cout << '\n';
    } else
      return 2;
  }
}
