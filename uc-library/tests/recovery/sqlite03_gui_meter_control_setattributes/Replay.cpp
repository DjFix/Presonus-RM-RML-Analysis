#include "core/portable/gui/coreviewbuilder.h"
#include "core/portable/gui/coreviewcontroller.h"
#include "presonus/DefaultMeterInterpolator.hpp"
#include "presonus/MeterControl.hpp"

#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
#include <string_view>

namespace {
using namespace Core;
using namespace Core::Portable;
using Presonus::MeterControl;

class InspectMeter : public MeterControl {
public:
  using MeterControl::MeterControl;
  static void borrow(MeterControl &m, Interpolator *p) {
    m.*(&InspectMeter::interpolator) = p;
  }
  static auto active(const MeterControl &m) {
    return m.*(&InspectMeter::interpolator);
  }
  auto active() const { return interpolator; }
  auto peakSubject() const { return peakParameter; }
  unsigned flags() const {
    return reverse | (immediate << 1) | (hidePeak << 2);
  }
};

struct BuilderAccess : ViewBuilder {
  using Build = void (ViewBuilder::*)(View &, const Attributes &,
                                      ViewController *,
                                      AttributeModifier *) const;
  static Build build() { return &BuilderAccess::buildView; }
};

struct Lookup : ViewController {
  Parameter *parameter = nullptr;
  int calls = 0;
  int height = 0;
  const View *view = nullptr;
  void *castTo(TypeID type) override {
    return type == kTypeID ? static_cast<ViewController *>(this) : nullptr;
  }
  View *createView(CStringPtr) override { return nullptr; }
  void *getObjectForView(CStringPtr name, CStringPtr type) override {
    if (std::string_view(type) != kParamType)
      std::abort();
    ++calls;
    height = view->getSize().getHeight();
    return std::string_view(name) == "matched" ? parameter : nullptr;
  }
};

class TrackedInterpolator : public LinearInterpolator {
public:
  static inline unsigned destroyed = 0;
  ~TrackedInterpolator() override { ++destroyed; }
};

Parameter *peakSubject = nullptr;
Parameter *mainSubject = nullptr;
const void *receiver = nullptr;
const void *tracked = nullptr;
unsigned events = 0;

void recordDelete(const void *p) {
  if (p == tracked)
    events = 10 * events + 1;
  if (p == receiver)
    events = 10 * events + 4;
}

void recordRemove(Parameter *p) {
  if (p == peakSubject)
    events = 10 * events + 2;
  if (p == mainSubject)
    events = 10 * events + 3;
}

ParamInfo info() {
  ParamInfo value{};
  value.type = ParamInfo::kFloat;
  value.maxValue = 1.f;
  return value;
}

int interpCode(const Interpolator *p, const Interpolator *borrowed) {
  if (!p)
    return 0;
  if (p == borrowed)
    return 1;
  const std::string_view name = p->getName();
  if (name == "audiometer")
    return 2;
  if (name == "linear")
    return 3;
  if (name == "linrev")
    return 4;
  if (name == "tracked")
    return 5;
  std::abort();
}

const char *peakName(int code) {
  return code == 1   ? ""
         : code == 2 ? "matched"
         : code == 3 ? "missing"
                     : nullptr;
}

const char *interpName(int code) {
  return code == 1   ? ""
         : code == 2 ? "linear"
         : code == 3 ? "missing"
         : code == 4 ? "linrev"
         : code == 5 ? "audiometer"
                     : nullptr;
}

void fill(Attributes &attributes, int height, int peak, int interp, int64 r,
          int64 u, int64 h) {
  attributes.set("width", 19);
  attributes.set("height", height);
  if (const auto *name = peakName(peak))
    attributes.set("peak", name, true);
  if (const auto *name = interpName(interp))
    attributes.set("interpolator", name, true);
  attributes.set("reversed", r);
  attributes.set("unoptimized", u);
  attributes.set("hidepeaks", h);
}

void attributes(bool provider) {
  bool borrowed;
  int count;
  std::cin >> borrowed >> count;
  NumericParam first(info()), second(info());
  LinearInterpolator external;
  InspectMeter meter(Rect(1, 2, 3, 4));
  View providerView(Rect(1, 2, 3, 4));
  if (borrowed)
    InspectMeter::borrow(meter, &external);
  meter.setPeakParameter(&first);
  Lookup lookup;
  lookup.parameter = &second;
  for (int i = 0; i < count; ++i) {
    int height, peak, interp;
    bool withController;
    int64 r, u, h;
    std::cin >> height >> peak >> interp >> withController >> r >> u >> h;
    Attributes attrs(AttributeAllocator::getDefault());
    fill(attrs, height, peak, interp, r, u, h);
    lookup.calls = lookup.height = 0;
    if (provider) {
      providerView.View::setAttributes(attrs);
      lookup.view = &providerView;
      const auto *peakToken = attrs.getString("peak");
      const auto *interpToken = attrs.getString("interpolator");
      const void *param = withController && peakToken && *peakToken
                              ? lookup.getObjectForView(peakToken, kParamType)
                              : nullptr;
      std::unique_ptr<Interpolator> named(
          InterpolatorFactory::create(interpToken));
      std::unique_ptr<Interpolator> fallback(
          InterpolatorFactory::create("audiometer"));
      std::cout << bool(peakToken && *peakToken) << ' '
                << bool(interpToken && *interpToken) << ' '
                << attrs.getInt("reversed") << ' '
                << attrs.getInt("unoptimized") << ' '
                << attrs.getInt("hidepeaks") << ' '
                << (param == &second ? 2 : 0) << ' '
                << interpCode(named.get(), &external) << ' '
                << interpCode(fallback.get(), &external) << ' ';
    } else {
      lookup.view = &meter;
      (ViewBuilder::instance().*BuilderAccess::build())(
          meter, attrs, withController ? &lookup : nullptr, nullptr);
      std::cout << meter.flags() << ' '
                << (meter.peakSubject() == &first    ? 1
                    : meter.peakSubject() == &second ? 2
                                                     : 0)
                << ' ' << interpCode(meter.active(), &external) << ' ';
    }
    const auto &rect = lookup.view->getSize();
    std::cout << rect.getWidth() << ' ' << rect.getHeight() << ' '
              << lookup.calls << ' ' << lookup.height << '\n';
  }
}

[[gnu::noipa]] void destroy(Control *p) { delete p; }

void lifecycle(bool provider, int variant) {
  bool owns, peak, main, borrowed;
  while (std::cin >> owns >> peak >> main >> borrowed) {
    NumericParam primary(info()), secondary(info());
    TrackedInterpolator external;
    alignas(InspectMeter) unsigned char buffer[sizeof(InspectMeter)];
    alignas(MeterControl) unsigned char exactBuffer[sizeof(MeterControl)];
    Control *control;
    MeterControl *meter = nullptr;
    if (provider)
      control = new (buffer) Control(Rect());
    else if (variant == 0)
      control = meter = new MeterControl(Rect());
    else if (variant == 1)
      control = meter = new (exactBuffer) MeterControl(Rect());
    else
      control = meter = new (buffer) InspectMeter(Rect());
    if (main)
      control->setParameter(&primary);
    if (provider && peak)
      secondary.addObserver(control);
    if (meter && peak)
      meter->setPeakParameter(&secondary);
    if (meter && borrowed)
      InspectMeter::borrow(*meter, &external);
    std::unique_ptr<Interpolator> providerInterpolator;
    if (owns) {
      if (provider)
        providerInterpolator.reset(InterpolatorFactory::create("tracked"));
      else {
        Attributes attrs(AttributeAllocator::getDefault());
        attrs.set("interpolator", "tracked", true);
        meter->setAttributes(attrs);
      }
    }
    tracked = provider   ? providerInterpolator.get()
              : owns     ? InspectMeter::active(*meter)
              : borrowed ? &external
                         : nullptr;
    receiver = control;
    mainSubject = &primary;
    peakSubject = &secondary;
    events = 0;
    TrackedInterpolator::destroyed = 0;
    if (provider) {
      providerInterpolator.reset();
      if (peak)
        secondary.removeObserver(control);
      control->Control::~Control();
    } else if (variant == 0) {
      destroy(control);
    } else if (variant == 1) {
      meter->MeterControl::~MeterControl();
    } else {
      // The derived complete destructor calls the MeterControl base variant.
      static_cast<InspectMeter *>(meter)->~InspectMeter();
    }
    std::cout << events << ' ' << TrackedInterpolator::destroyed << '\n';
    tracked = receiver = nullptr;
    peakSubject = mainSubject = nullptr;
  }
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  recordDelete(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  recordDelete(p);
  __real__ZdlPvm(p, size);
}

extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(p,
                                                                            o);
  recordRemove(p);
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 1;
  InterpolatorFactory::add<TrackedInterpolator>("tracked");
  const std::string_view mode(argv[1]);
  if (mode == "attributes" || mode == "provider-attributes") {
    if (mode == "provider-attributes")
      __initMeterControl();
    attributes(mode == "provider-attributes");
  } else if (mode == "vertical" || mode == "provider-rect") {
    int left, top, right, bottom;
    while (std::cin >> left >> top >> right >> bottom) {
      const Rect rect(left, top, right, bottom);
      if (mode == "vertical")
        std::cout << MeterControl(rect).isVertical() << '\n';
      else {
        const View view(rect);
        const auto &r = view.getSize();
        std::cout << r.left << ' ' << r.top << ' ' << r.right << ' ' << r.bottom
                  << '\n';
      }
    }
  } else if (mode == "provider-lifecycle") {
    lifecycle(true, -1);
  } else if (mode == "D0" || mode == "D1" || mode == "D2") {
    lifecycle(false, mode[1] - '0');
  } else {
    return 2;
  }
}
