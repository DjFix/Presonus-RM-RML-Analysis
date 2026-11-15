#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include "presonus/panel/ScenesComponent.hpp"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
using namespace Presonus::Panel;
struct Sink : PresetNameCache::ObserverSink {
  void changed(PresetNameCache::Delegate *, PresetNameCache &, int,
               const char *, const char *) override {
    std::abort();
  }
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &) override {
    std::abort();
  }
};
struct Services : presonus::panel::PresetApplicationServices {
  PresetNameManager &manager;
  mutable bool construction = true;
  mutable std::string cleanup;
  explicit Services(PresetNameManager &m) : manager(m) {}
  void guard(char code) const {
    assert(!construction);
    cleanup += code;
  }
  int selectedSlot(const PresetComponent &p) const override {
    return p.getParameterByTag(0)
               ? static_cast<int>(p.getParameterByTag(0)->getValue())
               : 0;
  }
  bool slotEmpty(const PresetComponent &, unsigned) const override {
    std::abort();
  }
  void slotFileName(Core::CString256 &, const PresetComponent &,
                    unsigned) const override {
    std::abort();
  }
  const char *presetFolder(const PresetComponent &) const override {
    guard('F');
    return "scene";
  }
  void ensureNameManager() const override {
    guard('E');
    assert(manager.lookupCache("scene"));
  }
  PresetNameCache *lookupCache(const char *f) const override {
    guard('L');
    return manager.lookupCache(f);
  }
  bool hasSelectedSlotParameter(const PresetComponent &) const override {
    std::abort();
  }
  void presetInfo(Core::CString64 &, Core::CString32 &, int,
                  const char *) const override {
    std::abort();
  }
  const char *emptyNameMarker() const override { std::abort(); }
  void updateSelection(PresetComponent &) override { std::abort(); }
  int recallAttributes(PresetComponent &, Core::Portable::Attributes &,
                       bool) override {
    std::abort();
  }
  void notifyDelegate(PresetComponent::Delegate *, const PresetComponent &, int,
                      bool) const override {
    std::abort();
  }
};
struct Dependencies : presonus::frontpanel_port::Dependencies {
  void perform(presonus::frontpanel_port::Action, int, int) override {
    std::abort();
  }
  bool timerLongEnough() const override { std::abort(); }
  bool fadersLocked() const override { std::abort(); }
  const char *activePageName() const override { std::abort(); }
  void paste(void *, const void *, const char *) override { std::abort(); }
};
struct Formatter : Core::Formatter {
  Formatter() : Core::Formatter("scenenum") {}
  void print(Data &d) const override { d.string[0] = 0; }
};
std::string observe(PresetComponent &p, Services &services) {
  assert(services.cleanup.empty());
  assert(&p.services == &services);
  std::ostringstream out;
  out << p.getName() << '|' << p.displayName.str() << '|' << p.countParameters()
      << '|';
  auto *f = p.getParameterByTag(0)->getFormatter();
  out << (f ? f->getName() : "NONE") << '|' << p.delegates.count() << '|'
      << p.delegates.getDelta() << '\n';
  for (int i = 0; i < p.countParameters(); ++i) {
    auto *v = p.getParameterByTag(i);
    const auto &info = *v->info;
    out << info.type << '|' << info.tag << '|' << info.name << '|'
        << info.minValue << '|' << info.maxValue << '|' << info.midValue << '|'
        << info.defaultValue << '|' << info.deltaValue << '|' << info.flags
        << '|' << info.title << '\n';
    if (auto *text = Core::Portable::StringParam::cast(v)) {
      out << text->getText() << '|' << text->getDefaultText() << '\n';
      text->fromString("changed", false);
      text->resetValue(false);
      assert(std::strcmp(text->getText(), text->getDefaultText()) == 0);
    }
  }
  return out.str();
}
int main(int argc, char **argv) {
  assert(argc >= 3);
  std::string kind = argv[1];
  bool present = std::atoi(argv[2]);
  Formatter formatter;
  if (present)
    Core::FormatterRegistry::add(&formatter);
  Sink sink;
  PresetNameCache cache("scene", Core::Portable::FileName("scene"), 1, 0, sink);
  PresetNameCache *items[] = {&cache};
  PresetNameManager manager(items, 1);
  Services services(manager);
  Presonus::Mixer::MixerComponentBase mixer;
  mixer.presetApplicationServices = &services;
  Core::Portable::Component settings;
  presonus::frontpanel_port::State state(settings);
  Dependencies deps;
  FrontPanelComponent front(state, deps);
  if (kind == "base") {
    assert(argc == 6);
    auto p =
        std::make_unique<PresetComponent>(argv[3], argv[4], argv[5], mixer);
    std::cout << observe(*p, services);
    services.construction = false;
    p.reset();
    assert(services.cleanup == "EFL");
    std::cout << "cleanup:" << services.cleanup << '\n';
  } else if (kind == "legacy") {
    auto p = std::make_unique<ScenesComponent>(services, mixer);
    assert(p->sourcePortPanel() == nullptr && &p->sourcePortMixer() == &mixer);
    const Core::Portable::ParamInfo slotInfo = PARAM_INT_(
        0, "slot_num", 0, 98, 0, "", "", 0, 0, "Slot Number", nullptr);
    p->addParameters(&slotInfo, 1);
    services.construction = false;
    assert(!p->store());
    p.reset();
    assert(services.cleanup == "EFL");
    std::cout << "legacy:preserved\n";
  } else {
    auto p = std::make_unique<ScenesComponent>(front, mixer);
    assert(p->sourcePortPanel() == &front && &p->sourcePortMixer() == &mixer);
    std::cout << observe(*p, services);
    services.construction = false;
    assert(!p->store());
    p.reset();
    assert(services.cleanup == "EFL");
    std::cout << "cleanup:" << services.cleanup << '\n';
  }
}
