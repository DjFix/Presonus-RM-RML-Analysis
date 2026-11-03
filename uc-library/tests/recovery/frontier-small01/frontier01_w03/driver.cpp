#include "presonus/frontier01/frontier01_w03.hpp"
#include <iostream>
#include <string>
#include <vector>

using namespace Core;
using namespace Core::Portable;
namespace {
// Exercise real protected catalog insertion on the actual singleton. A member
// pointer taken in derived scope still invokes the real BitmapManager method.
struct Pot : Presonus::PotControl {
  Pot() : PotControl(Rect(1, 2, 30, 40)) {}
  void prepare(int flags, int oldI, int oldS, int oldL,
               const std::vector<Bitmap *> &b, int previousFrames) {
    options = flags;
    image_ = b[oldI];
    focusStrip_ = b[oldS];
    focusSlice_ = b[oldL];
    frameCount_ = previousFrames;
  }
};
template <class Base> struct Flags : Base {
  using Base::Base;
  int flags() const { return this->options; }
};
struct BitmapCounter : Bitmap {
  int count() const { return useCount; }
};
struct CountCatalog : BitmapManager {
  static BitmapCounter *add(const char *name, int frames) {
    auto *d = new BitmapDescriptor;
    auto *b = new BitmapCounter;
    b->setFrameCount(frames);
    d->setBitmap(b);
    auto method = &CountCatalog::addBitmap;
    (BitmapManager::instance().*method)(name, d);
    return b;
  }
};
const ParamInfo lifecycleInfo =
    PARAM_FLOAT(703, "w03-live", 0, 127, 0, 1, nullptr, nullptr, 0, 0);
struct ObservedParameter : NumericParam {
  ObservedParameter() : NumericParam(lifecycleInfo) {}
  int observers() const { return observerList.count(); }
  bool observing(IParamObserver *p) const { return observerList.contains(p); }
};
template <class Radio, class Fader> int parameterLifecycle() {
  ObservedParameter parameter;
  const Rect rect(1, 2, 30, 40);
  auto record = [&](int stage, Radio *radio, Fader *fader) {
    std::cout << stage << ' ' << parameter.observers() << ' '
              << (radio && radio->getParameter() == &parameter) << ' '
              << (fader && fader->getParameter() == &parameter) << ' '
              << (radio && parameter.observing(radio)) << ' '
              << (fader && parameter.observing(fader)) << ' '
              << (radio && radio->isEnabled()) << ' '
              << (fader && fader->isEnabled()) << '\n';
  };
  if (parameter.observers() != 0)
    return 10;
  record(0, nullptr, nullptr);
  {
    Radio radio(rect, &parameter, 17);
    if (radio.getParameter() != &parameter || parameter.observers() != 1 ||
        !parameter.observing(&radio))
      return 11;
    record(1, &radio, nullptr);
    {
      Fader fader(rect, &parameter);
      if (fader.getParameter() != &parameter || parameter.observers() != 2 ||
          !parameter.observing(&radio) || !parameter.observing(&fader))
        return 12;
      record(2, &radio, &fader);
      parameter.enable(false);
      if (radio.isEnabled() || fader.isEnabled())
        return 13;
      record(3, &radio, &fader);
      parameter.enable(true);
      if (!radio.isEnabled() || !fader.isEnabled())
        return 14;
      record(4, &radio, &fader);
    }
    if (parameter.observers() != 1 || !parameter.observing(&radio))
      return 15;
    record(5, &radio, nullptr);
    parameter.enable(false);
    if (radio.isEnabled())
      return 16;
    record(6, &radio, nullptr);
  }
  if (parameter.observers() != 0)
    return 17;
  record(7, nullptr, nullptr);
  parameter.enable(true); // actual source signal with no remaining observers
  record(8, nullptr, nullptr);
  return 0;
}
int bitmapIndex(Bitmap *p, const std::vector<Bitmap *> &b) {
  for (std::size_t i = 0; i < b.size(); ++i)
    if (p == b[i])
      return static_cast<int>(i);
  return -1;
}
} // namespace
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const std::string mode(argv[1]);
  const Rect rect(1, 2, 30, 40);
  if (mode == "provider-lifecycle")
    return parameterLifecycle<RadioButton, Slider>();
  if (mode == "portable-lifecycle")
    return parameterLifecycle<Presonus::FocusHelperButton,
                              Presonus::McuVpotControl>();
  if (mode == "construct") {
    int value;
    while (std::cin >> value) {
      Flags<Control> control(rect, nullptr);
      Presonus::PotControl pot(rect);
      const auto p = pot.portableState();
      Flags<RadioButton> radio(rect, nullptr, value);
      Presonus::FocusHelperButton focus(rect, nullptr, value);
      Flags<Slider> slider(rect, nullptr);
      Flags<Presonus::McuVpotControl> mcu(rect, nullptr);
      auto m = mcu.portableState();
      if (!(pot.getSize() == rect) || !(focus.getSize() == rect) ||
          !(mcu.getSize() == rect) || pot.getParameter() != nullptr ||
          focus.getParameter() != nullptr || mcu.getParameter() != nullptr)
        return 4;
      std::cout << control.flags() << ' ' << p.options << ' ' << p.focusMode
                << ' ' << p.previousValue << ' ' << p.frameCount << ' '
                << (p.image == nullptr && p.strip == nullptr &&
                    p.slice == nullptr)
                << ' ' << radio.getValue() << ' ' << focus.getValue() << ' '
                << focus.portableActive() << ' '
                << static_cast<int>(focus.portableViewName()[0]) << ' '
                << slider.flags() << ' ' << mcu.flags() << ' ' << m.value << ' '
                << (m.image == nullptr && m.strip == nullptr &&
                    m.slice == nullptr)
                << '\n';
    }
  } else if (mode == "focus") {
    int kind, value;
    while (std::cin >> kind >> value) {
      Attributes a(AttributeAllocator::getDefault());
      if (kind == 1)
        a.set("viewName", "target-name");
      if (kind == 2)
        a.set("viewName", "");
      if (kind == 3)
        a.set("viewName", 123);
      a.set("radiovalue", value);
      Presonus::FocusHelperButton p(rect, nullptr, 99);
      RadioButton provider(rect, nullptr, 99);
      provider.setAttributes(a);
      p.setAttributes(a);
      auto *ptr = a.getString("viewName");
      if (p.getValue() != provider.getValue())
        return 3;
      std::cout << (p.portableViewName() == ptr ||
                    (!ptr && !*p.portableViewName()))
                << ' ' << p.portableActive() << ' '
                << (p.portableViewName()[0] != 0) << '\n';
    }
  } else if (mode == "pot") {
    auto *b1 = CountCatalog::add("w03-one", 7);
    auto *b2 = CountCatalog::add("w03-two", 13);
    std::vector<Bitmap *> b = {nullptr, b1, b2};
    const char *names[] = {"", "w03-one", "w03-two"};
    int flags, opt, oi, os, ol, ni, ns, nl, previous;
    while (std::cin >> flags >> opt >> oi >> os >> ol >> ni >> ns >> nl >>
           previous) {
      {
        Pot p;
        p.prepare(flags, oi, os, ol, b, previous);
        Attributes a(AttributeAllocator::getDefault());
        const char *options[] = {"", "textinput", "onoffmode",
                                 "textinput onoffmode", "unknown"};
        a.set("options", options[opt]);
        a.set("image", names[ni]);
        a.set("focusStrip", names[ns]);
        a.set("focusSlice", names[nl]);
        p.setAttributes(a);
        auto s = p.portableState();
        std::cout << s.options << ' ' << bitmapIndex(s.image, b) << ' '
                  << bitmapIndex(s.strip, b) << ' ' << bitmapIndex(s.slice, b)
                  << ' ' << s.focusMode << ' ' << s.frameCount << ' '
                  << s.previousValue << ' ' << b1->count() << ' '
                  << b2->count();
      }
      std::cout << ' ' << b1->count() << ' ' << b2->count() << '\n';
    }
  } else if (mode == "find") {
    int depth, leaf, wrong, present;
    while (std::cin >> depth >> leaf >> wrong >> present) {
      Attributes root(AttributeAllocator::getDefault());
      Attributes *at = &root;
      for (int i = 0; i < depth; ++i)
        at = at->makeAttributes("nested");
      if (wrong)
        at->set("nested", 42);
      if (present)
        at->set("wanted", 0);
      Presonus::FileMuteGroup group;
      std::cout << group.findAttribute(leaf == 2 ? nullptr
                                                 : (leaf ? at : &root),
                                       "nested", "wanted")
                << '\n';
    }
  } else
    return 2;
}
