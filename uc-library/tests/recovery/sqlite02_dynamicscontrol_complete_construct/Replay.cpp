#include "core/gui/corebitmapprimitives.h"
#include "core/portable/corefile.h"
#include "core/portable/gui/coreviewcontroller.h"
#include "core/public/corememstream.h"
#include "presonus/DynamicsControl.hpp"

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <new>
#include <string>
#include <time.h>
#include <vector>

namespace {

using Core::Rect;
using Core::Portable::Bitmap;
using Core::Portable::Control;
using Core::Portable::IParamObserver;
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::TouchEvent;
using Presonus::DynamicsControl;

using Values = std::vector<double>;

const void *watchedAllocation = nullptr;
bool freed = false;
bool useFixedClock = false;
long fixedMilliseconds = 0;
std::array<Parameter *, 4> watchedParameters{};
std::vector<int> removalOrder;
std::vector<int> registrationOrder;
bool controlDestroyed = false;
bool controlConstructed = false;
bool controlCalledIdle = false;
bool controlCalledParamChanged = false;

class ProbeControl : public DynamicsControl {
public:
  using DynamicsControl::DynamicsControl;

  void invalidate(Core::RectRef) override { ++invalidations; }

  int invalidations = 0;
};

void appendRect(Values &values, Core::RectRef rect) {
  values.insert(values.end(),
                {static_cast<double>(rect.left), static_cast<double>(rect.top),
                 static_cast<double>(rect.right),
                 static_cast<double>(rect.bottom)});
}

void recordDelete(const void *p) {
  if (p == watchedAllocation)
    freed = true;
}

ParamInfo info(float min, float max, float value) {
  ParamInfo result{};
  result.type = ParamInfo::kFloat;
  result.minValue = min;
  result.maxValue = max;
  result.defaultValue = value;
  return result;
}

constexpr Core::uint32 kForeground = 0xff304050;
constexpr Core::uint32 kOffline = 0xff1294de;

class Canvas : public Core::Portable::ColorBitmapRenderer {
public:
  Canvas(Bitmap &bitmap, Bitmap &background)
      : ColorBitmapRenderer(bitmap), background_(&background) {}

  bool drawLine(Core::PointRef from, Core::PointRef to,
                Core::ColorRef color) override {
    events.insert(events.end(),
                  {1., double(from.x), double(from.y), double(to.x),
                   double(to.y), double(static_cast<Core::uint32>(color))});
    return ColorBitmapRenderer::drawLine(from, to, color);
  }

  bool drawBitmap(Core::PointRef pos, Bitmap &bitmap, Core::RectRef src,
                  const Core::Portable::BitmapMode *mode) override {
    events.insert(events.end(), {2., &bitmap == background_ ? 0. : 1.,
                                 double(pos.x), double(pos.y)});
    appendRect(events, src);
    return ColorBitmapRenderer::drawBitmap(pos, bitmap, src, mode);
  }

  Values events;

private:
  Bitmap *background_;
};

class Resolver : public Core::Portable::ViewController {
public:
  Resolver(Parameter &threshold, Parameter &ratio, Parameter &expander)
      : threshold_(&threshold), ratio_(&ratio), expander_(&expander) {}

  void *castTo(TypeID id) override {
    return id == kTypeID ? static_cast<Core::Portable::ViewController *>(this)
                         : nullptr;
  }

  Core::Portable::View *createView(Core::CStringPtr) override {
    return nullptr;
  }

  void *getObjectForView(Core::CStringPtr name,
                         Core::CStringPtr type) override {
    if (std::string(type) != "Param")
      std::abort();
    if (std::string(name) == "exp") {
      lookups.push_back(3);
      return expander_;
    }
    if (std::string(name) == "rat") {
      lookups.push_back(2);
      return ratio_;
    }
    if (std::string(name) == "th") {
      lookups.push_back(1);
      return threshold_;
    }
    std::abort();
  }

  Values lookups;

private:
  Parameter *threshold_;
  Parameter *ratio_;
  Parameter *expander_;
};

class BitmapPackage : public Core::Portable::FilePackage {
public:
  BitmapPackage(int imageFrames, int handleFrames)
      : spec_("[{\"name\":\"dynamicsTestImage\",\"file\":\"image.bmp\","
              "\"frames\":" +
              std::to_string(imageFrames) +
              "},{\"name\":\"dynamicsTestHandle\",\"file\":\"handle.bmp\","
              "\"frames\":" +
              std::to_string(handleFrames) + "}]") {}

  bool fileExists(Core::CStringPtr name) override {
    const std::string file(name);
    return file == "bitmaps.json" || file == "image.bmp" ||
           file == "handle.bmp";
  }

  Core::IO::Stream *openStream(Core::CStringPtr name) override {
    const std::string file(name);
    if (file == "bitmaps.json")
      return new Core::IO::MemoryStream(spec_.data(), spec_.size());
    if (file != "image.bmp" && file != "handle.bmp")
      return nullptr;
    auto *stream = new Core::IO::MemoryStream;
    const int width = file == "image.bmp" ? 48 : 5;
    const int height = file == "image.bmp" ? 24 : 10;
    Bitmap source(width, height);
    if (!Bitmap::saveBMPImage(*stream, source))
      std::abort();
    stream->setPosition(0, Core::IO::kSeekSet);
    return stream;
  }

private:
  std::string spec_;
};

void styleControl(DynamicsControl &control) {
  auto *style = new Core::Portable::Style();
  style->setForeColor(Core::Color::fromInt(kForeground));
  control.setStyle(style);
}

} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  recordDelete(p);
  __real__ZdlPv(p);
}

extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  recordDelete(p);
  __real__ZdlPvm(p, n);
}

extern "C" int __real_clock_gettime(clockid_t, timespec *);
extern "C" int __wrap_clock_gettime(clockid_t id, timespec *t) {
  if (useFixedClock && id == CLOCK_MONOTONIC) {
    t->tv_sec = fixedMilliseconds / 1000;
    t->tv_nsec = fixedMilliseconds % 1000 * 1000000;
    return 0;
  }
  return __real_clock_gettime(id, t);
}

extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *observer) {
  for (unsigned i = 0; i < watchedParameters.size(); ++i)
    if (watchedParameters[i] == p)
      removalOrder.push_back(i);
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
      p, observer);
}

extern "C" void __real__ZN4Core8Portable7ControlD2Ev(Control *);
extern "C" void __wrap__ZN4Core8Portable7ControlD2Ev(Control *control) {
  controlDestroyed = true;
  __real__ZN4Core8Portable7ControlD2Ev(control);
}

extern "C" void
__real__ZN4Core8Portable7ControlC2ERKNS_5TRectIiEEPNS0_9ParameterE(
    Control *, Core::RectRef, Parameter *);
extern "C" void
__wrap__ZN4Core8Portable7ControlC2ERKNS_5TRectIiEEPNS0_9ParameterE(
    Control *control, Core::RectRef rect, Parameter *parameter) {
  controlConstructed = parameter == nullptr;
  __real__ZN4Core8Portable7ControlC2ERKNS_5TRectIiEEPNS0_9ParameterE(
      control, rect, parameter);
}

extern "C" void __real__ZN4Core8Portable7Control6onIdleEv(Control *);
extern "C" void __wrap__ZN4Core8Portable7Control6onIdleEv(Control *control) {
  controlCalledIdle = true;
  __real__ZN4Core8Portable7Control6onIdleEv(control);
}

extern "C" void
__real__ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi(Control *,
                                                                 Parameter *,
                                                                 int);
extern "C" void
__wrap__ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi(
    Control *control, Parameter *parameter, int message) {
  controlCalledParamChanged = true;
  __real__ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi(
      control, parameter, message);
}

extern "C" void
__real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *observer) {
  for (unsigned i = 0; i < watchedParameters.size(); ++i)
    if (watchedParameters[i] == p)
      registrationOrder.push_back(i);
  __real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
      p, observer);
}

namespace Presonus {

struct DynamicsControlReplay {
  static Values draw(DynamicsControl &control, const Values &a,
                     Parameter &primary, Parameter &threshold, Parameter &ratio,
                     Parameter &expander) {
    Bitmap image(48, 24), handle(5, 10), canvas(60, 40);
    Canvas graphics(canvas, image);
    const Rect clip(0, 0, 60, 40);
    const auto fill = Core::Color(0x04, 0x03, 0x02);
    graphics.setClip(clip);
    graphics.fillRect(clip, fill);

    styleControl(control);
    control.setSize(Rect(0, 0, 40, 20));
    control.configureSourcePort(static_cast<DynamicsControl::Mode>(a[3]),
                                nullptr);
    attach(control, &threshold, &DynamicsControl::threshold_);
    attach(control, &ratio, &DynamicsControl::ratio_);
    attach(control, &expander, &DynamicsControl::expander_);
    if (a[0] != -9) {
      primary.setValue(a[0]);
      control.setParameter(&primary);
    }
    if (a[1]) {
      image.setFrameCount(a[1]);
      control.background_ = &image;
    }
    if (a[2]) {
      handle.setFrameCount(a[2]);
      control.handle_ = &handle;
    }
    control.offLineColor_ = Core::Color::fromInt(kOffline);
    control.draw(Core::Portable::DrawEvent(graphics, clip));
    const auto pixel = Core::BitmapPrimitives32::toColor(
        canvas.accessForRead().rgbaAt(10, 15));
    if (static_cast<Core::uint32>(pixel) == static_cast<Core::uint32>(fill))
      std::abort();
    control.background_ = nullptr;
    control.handle_ = nullptr;
    Values values(control.drawnPivots_.begin(), control.drawnPivots_.end());
    values.insert(values.end(), graphics.events.begin(), graphics.events.end());
    return values;
  }

  static Values attributes(DynamicsControl &control, const Values &a,
                           Parameter &threshold, Parameter &ratio,
                           Parameter &expander) {
    using namespace Core::Portable;
    BitmapPackage package(a[3], a[4]);
    if (BitmapManager::instance().loadBitmaps(package) != 2)
      std::abort();
    Resolver resolver(threshold, ratio, expander);
    if (a[0])
      control.configureSourcePort(DynamicsControl::Mode::Gate, &resolver);
    styleControl(control);
    DefaultAllocatedAttributes attrs;
    attrs.set("width", static_cast<int>(a[6]));
    attrs.set("height", static_cast<int>(a[7]));
    if (a[3])
      attrs.set("image", "dynamicsTestImage");
    if (a[4])
      attrs.set("handle", "dynamicsTestHandle");
    if (a[5])
      attrs.set("offLineColor", "#de9412");
    if (a[1]) {
      auto *params = attrs.makeAttributes("params");
      const int mask = a[2];
      if (mask & 1)
        params->set("threshold", "th");
      if (mask & 2)
        params->set("ratio", "rat");
      if (mask & 4)
        params->set("expander", "exp");
    }
    watchedParameters = {nullptr, &threshold, &ratio, &expander};
    control.setAttributes(attrs);
    watchedParameters.fill(nullptr);
    Values result;
    appendRect(result, control.getSize());
    result.insert(result.end(),
                  {double(static_cast<Core::uint32>(control.offLineColor_)),
                   control.threshold_ ? 1. : 0., control.ratio_ ? 1. : 0.,
                   control.expander_ ? 1. : 0.,
                   control.background_.isValid() &&
                           control.background_.getBitmap()->isReferenced()
                       ? 1.
                       : 0.,
                   control.handle_.isValid() &&
                           control.handle_.getBitmap()->isReferenced()
                       ? 1.
                       : 0.});
    result.push_back(resolver.lookups.size());
    result.insert(result.end(), resolver.lookups.begin(),
                  resolver.lookups.end());
    result.insert(result.end(), registrationOrder.begin(),
                  registrationOrder.end());
    return result;
  }

  static void appendRanges(Values &values, const DynamicsControl &control) {
    for (const auto *range : {&control.vertical_, &control.horizontal_})
      values.insert(values.end(), {range->getMinRange(), range->getMaxRange(),
                                   range->getMidRange()});
  }

  static void attach(DynamicsControl &control, Parameter *parameter,
                     Parameter *DynamicsControl::*member) {
    control.*member = parameter;
    if (parameter)
      parameter->addObserver(&control);
  }

  static Values constructed(const DynamicsControl &control) {
    Values values;
    appendRect(values, control.getSize());
    values.insert(
        values.end(),
        {control.getParameter() ? 1. : 0., static_cast<double>(control.mode_),
         control.resolver_ ? 1. : 0., control.background_.isValid() ? 1. : 0.,
         control.handle_.isValid() ? 1. : 0., control.threshold_ ? 1. : 0.,
         control.ratio_ ? 1. : 0., control.expander_ ? 1. : 0.,
         static_cast<double>(control.lastInvalidate_), 0.});
    for (auto pivot : control.drawnPivots_)
      values.push_back(pivot);
    values.insert(values.end(),
                  {static_cast<double>(control.offLineColor_.red),
                   static_cast<double>(control.offLineColor_.green),
                   static_cast<double>(control.offLineColor_.blue),
                   static_cast<double>(control.offLineColor_.alpha),
                   control.pendingInvalidate_ ? 1. : 0.});
    appendRanges(values, control);
    values.push_back(controlConstructed);
    return values;
  }

  static Values destructor(const std::string &method, int mask) {
    Bitmap background, handle;
    auto parameterInfo = info(0.f, 1.f, 0.f);
    NumericParam threshold(parameterInfo), ratio(parameterInfo),
        expander(parameterInfo);
    alignas(ProbeControl) std::byte storage[sizeof(ProbeControl)];
    DynamicsControl *control;
    if (method == "deleting_destroy")
      control = new DynamicsControl(Rect());
    else if (method == "base_destroy")
      control = new (storage) ProbeControl(Rect());
    else
      control = new (storage) DynamicsControl(Rect());
    attach(*control, mask & 1 ? &threshold : nullptr,
           &DynamicsControl::threshold_);
    attach(*control, mask & 2 ? &ratio : nullptr, &DynamicsControl::ratio_);
    attach(*control, mask & 4 ? &expander : nullptr,
           &DynamicsControl::expander_);
    control->background_ = &background;
    control->handle_ = &handle;
    watchedParameters = {nullptr, &threshold, &ratio, &expander};
    watchedAllocation = control;
    if (method == "deleting_destroy") {
      Control *subobject = control;
      delete subobject;
    } else if (method == "base_destroy") {
      static_cast<ProbeControl *>(control)->~ProbeControl();
    } else {
      control->~DynamicsControl();
    }
    watchedParameters.fill(nullptr);
    watchedAllocation = nullptr;
    Values values{background.isReferenced() ? 1. : 0.,
                  handle.isReferenced() ? 1. : 0., freed ? 1. : 0.,
                  controlDestroyed ? 1. : 0.};
    for (int index : removalOrder)
      values.push_back(index);
    return values;
  }

  static Values run(const std::string &method, const Values &a) {
    if (method.find("_destroy") != std::string::npos)
      return destructor(method, a[0]);
    auto primaryInfo = info(-2.f, 2.f, 0.f);
    auto thresholdInfo = info(0.f, 1.f, .25f);
    auto ratioInfo = info(0.f, 8.f, 4.f);
    auto expanderInfo = info(0.f, 1.f, 0.f);
    NumericParam primary(primaryInfo), threshold(thresholdInfo),
        ratio(ratioInfo), expander(expanderInfo);
    if (method == "base_construct") {
      ProbeControl control(Rect(a[0], a[1], a[2], a[3]));
      return constructed(control);
    }
    if (method == "complete_construct") {
      DynamicsControl control(Rect(a[0], a[1], a[2], a[3]));
      return constructed(control);
    }
    ProbeControl control(Rect(0, 0, 40, 20));
    if (method == "draw")
      return draw(control, a, primary, threshold, ratio, expander);
    if (method == "set_attributes")
      return attributes(control, a, threshold, ratio, expander);
    if (method == "set_size") {
      control.setSize(Rect(a[0], a[1], a[2], a[3]));
      Values values;
      appendRect(values, control.getSize());
      appendRanges(values, control);
      return values;
    }
    if (method == "calculate_pivot_points") {
      control.configureSourcePort(static_cast<DynamicsControl::Mode>(a[0]),
                                  nullptr);
      if (a[1] >= 0) {
        threshold.setValue(a[1]);
        attach(control, &threshold, &DynamicsControl::threshold_);
      }
      if (a[2] >= 0) {
        ratio.setValue(a[2]);
        attach(control, &ratio, &DynamicsControl::ratio_);
      }
      if (a[3] >= 0) {
        expander.setValue(a[3]);
        attach(control, &expander, &DynamicsControl::expander_);
      }
      control.setSize(Rect(0, 0, a[4], a[5]));
      std::array<int, 4> pivots;
      control.calculatePivotPoints(pivots[0], pivots[1], pivots[2], pivots[3]);
      return Values(pivots.begin(), pivots.end());
    }
    if (method == "on_idle") {
      control.lastInvalidate_ = a[0];
      fixedMilliseconds = a[1];
      control.pendingInvalidate_ = a[2];
      useFixedClock = true;
      control.onIdle();
      useFixedClock = false;
      return {static_cast<double>(control.lastInvalidate_),
              control.pendingInvalidate_ ? 1. : 0.,
              static_cast<double>(control.invalidations),
              controlCalledIdle ? 1. : 0.};
    }
    if (method == "on_touch_input") {
      primary.setValue(a[3]);
      if (a[0])
        control.setParameter(&primary);
      control.enable(a[1] != 0);
      TouchEvent event(static_cast<TouchEvent::Type>(a[2]), Core::Point());
      return {control.onTouchInput(event) ? 1. : 0., primary.getValue()};
    }
    if (method == "param_changed") {
      control.setSize(Rect(0, 0, 40, 20));
      control.setParameter(&primary);
      attach(control, &threshold, &DynamicsControl::threshold_);
      attach(control, &ratio, &DynamicsControl::ratio_);
      attach(control, &expander, &DynamicsControl::expander_);
      for (unsigned i = 0; i < 4; ++i)
        control.drawnPivots_[i] = a[i + 2];
      control.pendingInvalidate_ = a[6];
      watchedParameters = {&primary, &threshold, &ratio, &expander};
      controlCalledParamChanged = false;
      control.paramChanged(watchedParameters[a[0]], a[1]);
      watchedParameters.fill(nullptr);
      Values result{control.threshold_ ? 1. : 0., control.ratio_ ? 1. : 0.,
                    control.expander_ ? 1. : 0.,
                    control.pendingInvalidate_ ? 1. : 0.,
                    controlCalledParamChanged ? 1. : 0.};
      for (int index : removalOrder)
        result.push_back(index);
      return result;
    }
    std::abort();
  }
};

} // namespace Presonus

int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  Values inputs;
  for (int i = 2; i < argc; ++i)
    inputs.push_back(std::stod(argv[i]));
  std::cout << std::setprecision(17);
  for (double value : Presonus::DynamicsControlReplay::run(argv[1], inputs))
    std::cout << value << ' ';
  std::cout << '\n';
}
