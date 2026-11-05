#include "core/portable/corefile.h"
#include "core/portable/gui/coreviewbuilder.h"
#include "presonus/McuVpotControl.hpp"
#include "presonus/panel/GeqUIComponent.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <sstream>
using namespace Core::Portable;
namespace {
bool capture = false, inBase = false, inAttributesBase = false;
std::ostringstream trace;
Parameter *subjects[4]{};
int id(Parameter *p) {
  for (int i = 0; i < 4; ++i)
    if (subjects[i] == p)
      return i;
  std::abort();
}
void event(const std::string &s) {
  if (capture)
    trace << s << ";";
}
struct Subject : NumericParam {
  using NumericParam::NumericParam;
  int count() const { return observerList.count(); }
};
struct Mcu : Presonus::McuVpotControl {
  using McuVpotControl::McuVpotControl;
  int baseInvalidations = 0;
  void image(BitmapReference b) { image_ = b; }
  void invalidate(Core::RectRef r) override {
    if (inBase || inAttributesBase)
      ++baseInvalidations;
    else
      event("invalidate");
    Core::Portable::View::invalidate(r);
  }
};
struct Controller : Component, ComponentViewController<Controller> {
  void *castTo(ITypedObject::TypeID id) override {
    return Component::castTo(id);
  }
  Parameter *a, *b;
  Controller(Parameter *a, Parameter *b) : a(a), b(b) {}
  Parameter *lookupParameter(Core::CStringPtr name) const {
    return std::string(name) == "first"    ? a
           : std::string(name) == "second" ? b
                                           : nullptr;
  }
  Component *lookupChild(Core::CStringPtr) const { return nullptr; }
  void *getObjectForView(Core::CStringPtr name,
                         Core::CStringPtr type) override {
    event(std::string("lookup:") + name);
    return ComponentViewController<Controller>::getObjectForView(name, type);
  }
};
struct Boundary : presonus::gequi_port::Dependencies {
  int geqCount() const override { std::abort(); }
  Presonus::Mixer::GEQComponent *geqAt(int index) const override {
    std::abort();
  }
  Core::Portable::Component &
  parameters(Presonus::Mixer::GEQComponent *) override {
    std::abort();
  }
  Core::Portable::Component &
  parameters(Presonus::Mixer::ChannelComponent *) override {
    std::abort();
  }
  int channelKind(Presonus::Mixer::ChannelComponent *) const override {
    std::abort();
  }
  std::uint32_t
  channelIndex(Presonus::Mixer::ChannelComponent *) const override {
    std::abort();
  }
  Core::Portable::Parameter &
  channelLink(Presonus::Mixer::ChannelComponent *) override {
    std::abort();
  }
  Presonus::Mixer::ChannelComponent *assignedChannel(int geq) override {
    std::abort();
  }
  bool linked(Presonus::Mixer::GEQComponent *) const override { std::abort(); }
  bool linkSlave(Presonus::Mixer::GEQComponent *) const override {
    std::abort();
  }
  bool linked(Presonus::Mixer::ChannelComponent *) const override {
    std::abort();
  }
  void flatten(Presonus::Mixer::GEQComponent *) override { std::abort(); }
  Presonus::Mixer::GEQComponent *
  geqController(Core::Portable::IParamObserver *) override {
    std::abort();
  }
  Presonus::Mixer::ChannelComponent *
  channelController(Core::Portable::IParamObserver *) override {
    std::abort();
  }
  bool channelUpdateLink(Presonus::Mixer::ChannelComponent *) const override {
    std::abort();
  }
  void updateGeqNameList() override { std::abort(); }
};
} // namespace
extern "C" void realAdd(Parameter *, IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE");
extern "C" void wrapAdd(Parameter *p, IParamObserver *o) asm(
    "__wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE");
extern "C" void wrapAdd(Parameter *p, IParamObserver *o) {
  event("add:" + std::to_string(id(p)));
  realAdd(p, o);
}
extern "C" void realRemove(Parameter *, IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrapRemove(Parameter *p, IParamObserver *o) asm(
    "__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrapRemove(Parameter *p, IParamObserver *o) {
  event("remove:" + std::to_string(id(p)));
  realRemove(p, o);
}
extern "C" void realBase(Control *, Parameter *, int) asm(
    "__real__ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi");
extern "C" void wrapBase(Control *c, Parameter *p, int m) asm(
    "__wrap__ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi");
extern "C" void wrapBase(Control *c, Parameter *p, int m) {
  event("base");
  inBase = true;
  realBase(c, p, m);
  inBase = false;
}
extern "C" void realAttributes(ValueBar *, const Attributes &) asm(
    "__real__ZN4Core8Portable8ValueBar13setAttributesERKNS0_10AttributesE");
extern "C" void wrapAttributes(ValueBar *v, const Attributes &a) asm(
    "__wrap__ZN4Core8Portable8ValueBar13setAttributesERKNS0_10AttributesE");
extern "C" void wrapAttributes(ValueBar *v, const Attributes &a) {
  event("attributes-base");
  inAttributesBase = true;
  realAttributes(v, a);
  inAttributesBase = false;
}
extern "C" BitmapReference realBitmap(const Attributes &, Core::CStringPtr) asm(
    "__real__ZN4Core8Portable14ViewAttributes9getBitmapERKNS0_"
    "10AttributesEPKc");
extern "C" BitmapReference
wrapBitmap(const Attributes &a, Core::CStringPtr n) asm(
    "__wrap__ZN4Core8Portable14ViewAttributes9getBitmapERKNS0_"
    "10AttributesEPKc");
extern "C" BitmapReference wrapBitmap(const Attributes &a, Core::CStringPtr n) {
  if (!inAttributesBase)
    event("bitmap");
  return realBitmap(a, n);
}
int main(int argc, char **) {
  if (argc > 1) {
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.minValue = 0;
    info.maxValue = 1;
    Subject main(info), p(info);
    subjects[0] = nullptr;
    subjects[1] = &p;
    subjects[2] = nullptr;
    subjects[3] = &main;
    {
      Mcu m(Core::Rect(0, 0, 20, 30), &main);
      m.setStyleParameter(&p);
      m.setDotParameter(&p);
      if (p.count() != 2)
        return 30;
    }
    if (p.count() != 0 || main.count() != 0)
      return 31;
    {
      Mcu m(Core::Rect(0, 0, 20, 30), &main);
      auto *dying = new Subject(info);
      subjects[1] = dying;
      m.setStyleParameter(dying);
      m.setDotParameter(dying);
      delete dying;
      auto state = m.portableState();
      if (state.styleParameter || state.dotParameter)
        return 32;
    }
    subjects[1] = &p;
    {
      Mcu m(Core::Rect(0, 0, 20, 30), &main);
      main.enable(false);
      m.paramChanged(&main, Parameter::kChanged);
      if (m.isEnabled())
        return 33;
      main.enable(true);
      m.paramChanged(&main, Parameter::kChanged);
      if (!m.isEnabled())
        return 34;
    }
    std::cout << "PASS pinned release-provider actual destruction, alias "
                 "duplicates, detachment, enabled changes; debug assertions "
                 "remain an explicit discrepancy\n";
    return 0;
  }

  FolderPackage package(
      "uc-library/tests/recovery/rolling200-controls01/resources");
  if (BitmapManager::instance().loadBitmaps(package) != 2)
    return 20;
  auto one = BitmapManager::instance().getBitmap("one");
  auto two = BitmapManager::instance().getBitmap("two");
  if (!one.getBitmap() || !two.getBitmap())
    return 21;

  int target, arg, msg;
  long long old, next;
  while (std::cin >> target >> old >> next >> arg >> msg) {
    trace.str("");
    trace.clear();
    capture = false;
    if (target == 0) {
      Boundary b;
      Presonus::Panel::GeqUIComponent ui(b);
      ui.configureSelection(17, 23);
      auto cv = [](std::uint32_t v) {
        return reinterpret_cast<Presonus::Panel::GeqUIComponent::Delegate *>(
            std::uintptr_t(v));
      };
      ui.setDelegate(cv(old));
      ui.setDelegate(cv(next));
      if (ui.selectedBand() != 23)
        return 10;
      std::cout << std::uint32_t(
                       reinterpret_cast<std::uintptr_t>(ui.portableDelegate()))
                << " | | 0 0 0 0 0\n";
      continue;
    }
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.minValue = 0;
    info.maxValue = 1;
    Subject a(info), b(info), main(info);
    subjects[0] = nullptr;
    subjects[1] = &a;
    subjects[2] = &b;
    subjects[3] = &main;
    Mcu m(Core::Rect(0, 0, 20, 30), &main);
    if (target == 4) {
      int dotResult, oldImage, newImage;
      std::cin >> dotResult >> oldImage >> newImage;
      Controller controller(subjects[msg], subjects[dotResult]);
      if (arg)
        m.configurePortableController(&controller);
      auto bitmap = [&](int i) {
        return i == 1 ? one : i == 2 ? two : BitmapReference();
      };
      m.image(bitmap(oldImage));
      Attributes attrs(AttributeAllocator::getDefault());
      if (old)
        attrs.set("valuestyle", old == 1 ? "" : "first");
      if (next)
        attrs.set("dot", next == 1 ? "" : "second");
      if (newImage)
        attrs.set("image", newImage == 1 ? "one" : "two");
      trace.str("");
      trace.clear();
      capture = true;
      m.setAttributes(attrs);
      capture = false;
      auto state = m.portableState();
      int image = state.image == one.getBitmap()   ? 1
                  : state.image == two.getBitmap() ? 2
                                                   : 0;
      std::cout << id(state.styleParameter) << " " << id(state.dotParameter)
                << " " << image << " |" << trace.str() << "| " << a.count()
                << " " << b.count() << "\n";
      continue;
    }

    if (target == 1) {
      m.setStyleParameter(subjects[old]);
      m.setDotParameter(subjects[next]);
    } else if (target == 2)
      m.setDotParameter(subjects[old]);
    else
      m.setStyleParameter(subjects[old]);
    m.baseInvalidations = 0;
    trace.str("");
    trace.clear();
    capture = true;
    if (target == 1)
      m.paramChanged(subjects[arg], msg);
    else if (target == 2)
      m.setDotParameter(subjects[next]);
    else
      m.setStyleParameter(subjects[next]);
    capture = false;
    auto s = m.portableState();
    if (target == 1)
      std::cout << id(s.styleParameter) << " " << id(s.dotParameter);
    else
      std::cout << id(target == 2 ? s.dotParameter : s.styleParameter);
    std::cout << " |" << trace.str() << "| " << a.count() << " " << b.count()
              << " " << main.count() << " " << m.baseInvalidations << " "
              << m.isEnabled() << "\n";
    // Explicit injected kDestroyed cases may clear pointers without a real
    // Parameter destruction; detach remaining test registrations before
    // teardown.
    while (a.count())
      a.removeObserver(&m);
    while (b.count())
      b.removeObserver(&m);
    m.setStyleParameter(nullptr);
    m.setDotParameter(nullptr);
  }
}
