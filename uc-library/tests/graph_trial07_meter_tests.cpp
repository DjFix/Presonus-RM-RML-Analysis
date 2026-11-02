#include "presonus/MeterControl.hpp"
#include <cstdint>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace Core;
using namespace Core::Portable;
namespace {
std::vector<std::string> trace;
bool recording = false;
Parameter *primaryIdentity = nullptr, *peakIdentity = nullptr;
IParamObserver *observerIdentity = nullptr;
int parameterChoice = 0;
uint32_t bits(float f) {
  uint32_t v;
  std::memcpy(&v, &f, sizeof v);
  return v;
}
float floating(uint32_t v) {
  float f;
  std::memcpy(&f, &v, sizeof f);
  return f;
}
void event(const char *name, std::initializer_list<int64_t> args = {}) {
  if (!recording)
    return;
  std::ostringstream s;
  s << "[\"" << name << '"';
  for (auto v : args)
    s << ',' << v;
  s << ']';
  trace.push_back(s.str());
}
void rectEvent(const char *name, RectRef r) {
  event(name, {r.left, r.top, r.right, r.bottom});
}
void printRect(RectRef r) {
  std::cout << '[' << r.left << ',' << r.top << ',' << r.right << ','
            << r.bottom << ']';
}
struct Param : NumericParam {
  using NumericParam::NumericParam;
  float normalized = .375f;
  bool enabled = true;
  float getNormalized() const override { return normalized; }
  bool isEnabled() const override { return enabled; }
  int observers() const { return observerList.count(); }
};
struct Curve : Interpolator {
  int mode = 1;
  float normalizedToRange(float v) const override {
    event("interpolate", {bits(v)});
    return mode == 1 ? v : v * v;
  }
};
struct Meter : Presonus::MeterControl {
  using MeterControl::drawnPeak;
  using MeterControl::drawnValue;
  using MeterControl::hidePeak;
  using MeterControl::immediate;
  using MeterControl::interpolator;
  using MeterControl::invalidate;
  using MeterControl::parameter;
  using MeterControl::peak;
  using MeterControl::peakDirty;
  using MeterControl::peakParameter;
  using MeterControl::reverse;
  using MeterControl::size;
  using MeterControl::value;
  using MeterControl::valueDirty;
  void invalidate(RectRef r) override { rectEvent("invalidate", r); }
};
struct CaptureGraphics : Graphics {
  bool setOrigin(PointRef) override { return true; }
  bool setClip(RectRef) override { return true; }
  int setMode(int) override { return 0; }
  bool fillRect(RectRef r, ColorRef color) override {
    uint32_t word;
    static_assert(sizeof color == sizeof word);
    std::memcpy(&word, &color, sizeof word);
    event("fill", {r.left, r.top, r.right, r.bottom, word});
    return true;
  }
  bool drawRect(RectRef, ColorRef) override { return true; }
  bool drawLinearGradient(PointRef, PointRef, ColorRef, ColorRef,
                          Direction) override {
    return true;
  }
  bool drawLine(PointRef, PointRef, ColorRef) override { return true; }
  bool drawString(RectRef, CStringPtr, ColorRef, CStringPtr, int) override {
    return true;
  }
  bool drawMultiLineString(RectRef, CStringPtr, ColorRef, CStringPtr,
                           int) override {
    return true;
  }
  int getStringWidth(CStringPtr, CStringPtr) const override { return 0; }
  bool drawBitmap(PointRef, Bitmap &, RectRef, const BitmapMode *) override {
    return true;
  }
  const BitmapFont *getFont(CStringPtr) const override { return nullptr; }
};
Color colorWord(uint32_t word) {
  Color c;
  static_assert(sizeof c == sizeof word);
  std::memcpy(&c, &word, sizeof word);
  return c;
}
} // namespace

// Link-time observation wrappers invoke actual pinned providers. Native
// observer offset 0x44 is normalized to the host's real IParamObserver
// identity, not a claim that the host object has that offset.
extern "C" {
void __real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
void __wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  if (recording && o != observerIdentity)
    std::abort();
  event("add", {p == peakIdentity ? 1 : 2, 68});
  __real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(p, o);
}
void __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
void __wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  if (recording && o != observerIdentity)
    std::abort();
  event("remove", {p == peakIdentity ? 1 : 2, 68});
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(p,
                                                                            o);
}
void __real__ZN4Core8Portable4View6enableEb(View *, bool);
void __wrap__ZN4Core8Portable4View6enableEb(View *p, bool enabled) {
  event("enable", {enabled});
  __real__ZN4Core8Portable4View6enableEb(p, enabled);
}
void __real__ZN4Core8Portable7Control6onIdleEv(Control *);
void __wrap__ZN4Core8Portable7Control6onIdleEv(Control *p) {
  event("base_idle");
  __real__ZN4Core8Portable7Control6onIdleEv(p);
}
void __real__ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi(
    Control *, Parameter *, int);
void __wrap__ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi(
    Control *c, Parameter *p, int msg) {
  event("base_param", {parameterChoice, msg});
  __real__ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi(c, p, msg);
}
}
int main() {
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    auto read = [&]() {
      int64_t v;
      if (!(in >> v))
        std::abort();
      return v;
    };
    auto readRect = [&]() {
      const int l = read(), t = read(), r = read(), b = read();
      return Rect(l, t, r, b);
    };
    const int target = read();
    Rect size = readRect();
    const bool reverse = read(), immediate = read(), hidePeak = read();
    const int ip = read(), primary = read(), oldPeak = read();
    const float value = floating(read()), drawnValue = floating(read()),
                peak = floating(read()), drawnPeak = floating(read());
    Rect dirty = readRect(), peakDirty = readRect();
    const float input = floating(read());
    const Rect a = readRect(), b = readRect(), clip = readRect();
    const int newPeak = read(), choice = read(), msg = read();
    const bool enabled = read();
    const float paramValue = floating(read());
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.maxValue = 1;
    Param p(info), pp(info), other(info);
    primaryIdentity = &p;
    peakIdentity = &pp;
    p.enabled = pp.enabled = enabled;
    p.normalized = pp.normalized = paramValue;
    Meter meter;
    observerIdentity = &meter;
    Curve curve;
    curve.mode = ip;
    meter.size = size;
    meter.reverse = reverse;
    meter.immediate = immediate;
    meter.hidePeak = hidePeak;
    meter.interpolator = ip ? &curve : nullptr;
    meter.parameter = primary ? &p : nullptr;
    meter.setPeakParameter(oldPeak ? &pp : nullptr);
    meter.value = value;
    meter.drawnValue = drawnValue;
    meter.peak = peak;
    meter.drawnPeak = drawnPeak;
    meter.valueDirty = dirty;
    meter.peakDirty = peakDirty;
    Style *style = new Style;
    style->setBackColor(colorWord(0x11223344));
    style->setForeColor(colorWord(0x55667788));
    style->setTextColor(colorWord(0xbbccddee));
    meter.setStyle(style);
    CaptureGraphics graphics;
    trace.clear();
    parameterChoice = choice;
    recording = true;
    Rect result;
    int pixel = 0;
    switch (target) {
    case 0:
      meter.setPeakValue(input);
      break;
    case 1:
      result = meter.subtractRect(a, b);
      break;
    case 2:
      meter.draw(DrawEvent(graphics, clip));
      break;
    case 3:
      result = meter.getLitRect(input);
      break;
    case 4:
      meter.setValue(input);
      break;
    case 5:
      meter.setPeakParameter(newPeak == 1 ? &pp : newPeak == 2 ? &p : nullptr);
      if (pp.observers() != (newPeak == 1 ? 1 : 0) ||
          p.observers() != (newPeak == 2 ? 1 : 0))
        std::abort();
      break;
    case 6:
      result = meter.getPeakRect(input);
      break;
    case 7:
      pixel = meter.normalizedToPixel(input);
      break;
    case 8:
      meter.paramChanged(choice == 1 ? &p : choice == 2 ? &pp : &other, msg);
      break;
    case 9:
      meter.onIdle();
      break;
    default:
      std::abort();
    }
    recording = false;
    std::cout << "{\"return\":";
    if (target == 7)
      std::cout << pixel;
    else
      std::cout << "null";
    std::cout << ",\"rect\":";
    if (target == 1 || target == 3 || target == 6)
      printRect(result);
    else
      std::cout << "null";
    std::cout << ",\"values_bits\":[" << bits(meter.value) << ','
              << bits(meter.drawnValue) << ',' << bits(meter.peak) << ','
              << bits(meter.drawnPeak) << "],\"dirty\":";
    printRect(meter.valueDirty);
    std::cout << ",\"peak_dirty\":";
    printRect(meter.peakDirty);
    std::cout << ",\"peak_param\":"
              << (meter.peakParameter == &pp  ? 1
                  : meter.peakParameter == &p ? 2
                                              : 0)
              << ",\"trace\":[";
    for (size_t i = 0; i < trace.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << trace[i];
    }
    std::cout << "]}\n";
    meter.parameter = nullptr;
    meter.setPeakParameter(nullptr);
    // View::setStyle owns its heap-allocated Style provider.
    meter.setStyle(nullptr);
  }
}
