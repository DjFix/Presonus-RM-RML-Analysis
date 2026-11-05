#include "presonus/mixer_dsp/EQControl.hpp"
#include <array>
#include <cassert>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <new>
#include <string>

extern "C" void originalC1(void *, const Core::Rect &) asm(
    "_ZN8Presonus9EQControlC1ERKN4Core5TRectIiEE");
extern "C" void originalC2(void *, const Core::Rect &) asm(
    "_ZN8Presonus9EQControlC2ERKN4Core5TRectIiEE");
namespace {
struct Lifetime : Core::Portable::ParamObserverBase {
  int destroyed = 0;
  void paramChanged(Core::Portable::Parameter *p, int message) override {
    assert(message == Core::Portable::Parameter::kDestroyed);
    ++destroyed;
    p->removeObserver(this);
  }
};
void printProviders(
    const Core::Portable::Control &control,
    const Core::LinearInterpolator &gain, const Core::LinearInterpolator &y,
    const presonus::dsp::EQControlFrequencyInterpolator &frequency,
    const Core::LinearInterpolator &x,
    const Core::Portable::ParamList &parameters) {
  auto rectangle = control.getSize();
  std::cout << "{\"rectangle\":[" << rectangle.left << ',' << rectangle.top
            << ',' << rectangle.right << ',' << rectangle.bottom
            << "],\"touch\":" << control.wantsTouch()
            << ",\"focus\":" << control.hasFocus()
            << ",\"null_parameter\":" << (control.getParameter() == nullptr)
            << ",\"interpolators\":[";
  int index = 0;
  for (const Core::Interpolator *p :
       std::array<const Core::Interpolator *, 4>{&gain, &y, &frequency, &x}) {
    if (index++)
      std::cout << ',';
    std::cout << '[' << p->getMinRange() << ',' << p->getMaxRange() << ','
              << p->getMidRange();
    if (index != 3)
      std::cout << ',' << p->normalizedToRange(.25f) << ','
                << p->normalizedToRange(.75f);
    std::cout << ']';
  }
  std::cout << "],\"feedback\":" << parameters.isFeedbackNeeded()
            << ",\"params\":[";
  for (int i = 0; i < parameters.count(); ++i) {
    if (i)
      std::cout << ',';
    auto *p = parameters.at(i);
    auto *numeric = static_cast<Core::Portable::NumericParam *>(p);
    auto *interpolator = numeric->getInterpolator();
    std::cout << "{\"type\":" << p->getType() << ",\"tag\":" << p->getTag()
              << ",\"name\":" << std::quoted(p->getName()) << ",\"values\":["
              << p->getMin() << ',' << p->getMax() << ',' << p->getDefault()
              << ',' << p->getValue() << "],\"flags\":[" << p->isBipolar()
              << ',' << p->isStorable() << ',' << !p->isPublic() << ','
              << p->isLinkable() << ',' << p->isMutable() << ','
              << p->isReadOnly() << ',' << p->isUserFlag1() << ','
              << p->isUserFlag2() << "],\"owns_info\":" << p->isOwnInfo()
              << ",\"null_controller\":" << (p->getController() == nullptr)
              << ",\"interpolator\":";
    if (interpolator)
      std::cout << '[' << interpolator->getMinRange() << ','
                << interpolator->getMaxRange() << ','
                << interpolator->getMidRange() << ']';
    else
      std::cout << "null";
    std::cout << '}';
  }
  std::cout << "]}";
}
} // namespace
int main() {
  std::cout << std::setprecision(10);
  char mode;
  int variant, l, t, r, b;
  while (std::cin >> mode >> variant >> l >> t >> r >> b) {
    Core::Rect rectangle(l, t, r, b);
    if (mode == 'A') {
      presonus::dsp::EQControlFrequencyInterpolator port;
      auto rejectsBootstrap = [&] {
        assert(!port.sourceRangeSupported());
        for (float value : {0.f, .5f, 1.f}) {
          bool forward = false, inverse = false;
          try {
            port.normalizedToRange(value);
          } catch (const std::domain_error &) {
            forward = true;
          }
          try {
            port.rangeToNormalized(value);
          } catch (const std::domain_error &) {
            inverse = true;
          }
          assert(forward && inverse);
        }
      };
      rejectsBootstrap();
      assert(port.getMinRange() == 0 && port.getMaxRange() == 1 &&
             port.getMidRange() == 1);
      int samples = 0;
      for (auto range : std::array<std::array<float, 2>, 8>{{{36, 465},
                                                             {90, 1200},
                                                             {380, 5000},
                                                             {1400, 18000},
                                                             {20, 20000},
                                                             {24, 1000},
                                                             {100, 20000},
                                                             {40, 16000}}}) {
        presonus::dsp::EqLogSourceInterpolator reference;
        reference.setRange(range[0], range[1], 0);
        port.setRange(range[0], range[1], 0);
        assert(port.sourceRangeSupported());
        for (int i = 0; i <= 256; ++i) {
          float n = i / 256.f;
          float value = reference.normalizedToRange(n);
          assert(port.normalizedToRange(n) == value);
          assert(port.rangeToNormalized(value) ==
                 reference.rangeToNormalized(value));
          ++samples;
        }
        bool rejected = false;
        try {
          port.setRange(-1, 100, 0);
        } catch (const std::invalid_argument &) {
          rejected = true;
        }
        assert(rejected);
        assert(port.getMinRange() == range[0] &&
               port.getMaxRange() == range[1]);
        rejectsBootstrap();
      }
      port.setRange(0, 1, 1);
      assert(port.getMinRange() == 0 && port.getMaxRange() == 1 &&
             port.getMidRange() == 1);
      rejectsBootstrap();
      std::cout << "{\"adapter_samples\":" << samples << "}\n";
      continue;
    }
    if (mode == 'P') {
      // Independent provider replay receives the decoded original ELF table,
      // not production source initializers or reconstructed expected values.
      std::array<Core::Portable::ParamInfo, 3> infos{};
      std::array<std::string, 3> units, curves;
      for (int i = 0; i < 3; ++i) {
        auto &info = infos[i];
        std::string name;
        std::cin >> info.type >> info.tag >> name >> info.minValue >>
            info.maxValue >> info.midValue >> info.defaultValue >>
            info.deltaValue >> info.flags >> units[i] >> curves[i];
        assert(name.size() < sizeof(info.name));
        std::strcpy(info.name, name.c_str());
        info.unitName = units[i] == "-" ? "" : units[i].c_str();
        info.curveName = curves[i] == "-" ? "" : curves[i].c_str();
      }
      Core::Portable::Control control(rectangle, nullptr);
      control.wantsTouch(true);
      Core::LinearInterpolator gain(0, 1), y(0, 1), x(0, 1);
      presonus::dsp::EQControlFrequencyInterpolator frequency;
      Core::Portable::ParamList parameters;
      parameters.add(infos.data(), 3, false);
      printProviders(control, gain, y, frequency, x, parameters);
      std::cout << '\n';
      continue;
    }
    assert(mode == 'S');
    Lifetime life;
    void *storage = ::operator new(sizeof(Presonus::EQControl));
    (variant == 1 ? originalC1 : originalC2)(storage, rectangle);
    auto *eq = static_cast<Presonus::EQControl *>(storage);
    const auto *state = eq->portableConstructorState();
    assert(state);
    for (int i = 0; i < 3; ++i)
      state->hpfParameters.at(i)->addObserver(&life);
    std::cout << "{\"table\":[";
    for (int i = 0; i < 3; ++i) {
      if (i)
        std::cout << ',';
      const auto &info = state->hpfInfo[i];
      std::cout << "{\"type\":" << info.type << ",\"tag\":" << info.tag
                << ",\"name\":" << std::quoted(info.name) << ",\"values\":["
                << info.minValue << ',' << info.maxValue << ',' << info.midValue
                << ',' << info.defaultValue << ',' << info.deltaValue
                << "],\"flags\":" << info.flags
                << ",\"unit\":" << std::quoted(info.unitName)
                << ",\"curve\":" << std::quoted(info.curveName)
                << ",\"null_optional_fields\":"
                << (!info.stringList && !info.title && !info.shortTitle) << '}';
    }
    std::cout << "],\"providers\":";
    printProviders(state->control, state->gain, state->y, state->frequency,
                   state->x, state->hpfParameters);
    const auto &c = state->offlineColor;
    std::cout << ",\"state\":{\"handle\":" << state->handleDiameter
              << ",\"color\":[" << int(c.red) << ',' << int(c.green) << ','
              << int(c.blue) << ',' << int(c.alpha)
              << "],\"requested\":" << eq->portableRequestedBandCount()
              << ",\"buffered\":" << eq->portableBufferedDraw()
              << ",\"present\":" << eq->portableBufferPresent()
              << ",\"valid\":" << eq->portableBufferValid()
              << ",\"clock\":" << eq->portableLastCurveTime()
              << ",\"empty_containers\":"
              << (eq->portableBandState().empty() &&
                  eq->portableParameterState().empty() &&
                  eq->portableBandCurves().empty() &&
                  eq->portableAmplitudeCurve().empty() &&
                  eq->portablePixelCurve().empty() &&
                  eq->portableBackgroundPainters().isEmpty())
              << ",\"null_borrowed_slots\":"
              << (state->borrowedBindings == std::array<const void *, 3>{})
              << ",\"null_bitmap\":" << (eq->portableBitmap() == nullptr)
              << "},\"range\":[" << eq->portableCurveMinimum() << ','
              << eq->portableCurveMaximum() << ']';
    // Exercise bindings without introducing dependence on pending band helpers.
    assert(!eq->isAnyBandOn() && eq->getBandForPoint(Core::Point()) == -1);
    assert(eq->getFrequency(0) == 0 && eq->getGain(0) == 0 && eq->getQ(0) == 0);
    assert(eq->gainToY(.5f) == 1);
    eq->setSize(rectangle);
    eq->paramChanged(state->hpfParameters.at(0),
                     Core::Portable::Parameter::kChanged);
    assert(eq->getType(0) == 0 && !eq->getBandEnabled(0));
    eq->~EQControl();
    ::operator delete(storage);
    assert(life.destroyed == 3);
    Presonus::EQControl partial(presonus::dsp::EQControlBiquadPortTag{});
    assert(!partial.portableConstructorState());
    assert(partial.portableCurveMinimum() == 20.f &&
           partial.portableCurveMaximum() == 20000.f);
    std::cout << ",\"destroyed_parameters\":" << life.destroyed << "}\n";
  }
}
