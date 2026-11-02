#include "presonus/panel/RackPanelComponent.hpp"
#include <cstring>
#include <iostream>
#include <map>
#include <memory>
#include <string>
using namespace Core::Portable;
namespace {
bool recording = false;
std::map<Parameter *, std::string> names;
std::string name(Parameter *p) { return p ? names.at(p) : "null"; }
std::uint32_t bits(float v) {
  std::uint32_t b;
  std::memcpy(&b, &v, 4);
  return b;
}
float value(std::uint32_t b) {
  float v;
  std::memcpy(&v, &b, 4);
  return v;
}
struct Param : NumericParam {
  Param(ParamInfo *i, std::string label) : NumericParam(*i, true) {
    names[this] = label;
  }
  void seed(std::uint32_t b) { value = ::value(b); }
  void setValue(float v, bool edit) override {
    if (recording)
      std::cout << "set " << name(this) << ' ' << bits(v) << ' ' << edit
                << '\n';
    NumericParam::setValue(v, edit);
  }
};
Param *make(int tag, const std::string &label) {
  auto *info = new ParamInfo{};
  info->type = ParamInfo::kFloat;
  info->tag = tag;
  info->maxValue = 1.f;
  return new Param(info, label);
}
struct ComponentFixture : Component {
  void add(Param *p) { paramList.add(p); }
};
struct ControlFixture : Presonus::Panel::Control {
  int id;
  explicit ControlFixture(int id) : Control(id), id(id) {}
  bool setParameter(Parameter *p, int mode) override {
    if (recording)
      std::cout << "bind " << id << ' ' << name(p) << ' ' << mode << '\n';
    return true;
  }
};
struct Observer : ParamObserverBase {
  void paramChanged(Parameter *p, int msg) override {
    if (recording && msg == Parameter::kChanged)
      std::cout << "changed " << name(p) << '\n';
  }
};
struct Fixture : presonus::rackpanel_port::Dependencies {
  ComponentFixture monitor;
  std::vector<presonus::rackpanel_port::Channel> channelList;
  std::vector<std::unique_ptr<ComponentFixture>> ownedChannels;
  std::vector<std::unique_ptr<ControlFixture>> controls;
  std::vector<std::unique_ptr<Presonus::Panel::LEDControl>> leds;
  presonus::panel_binding::ControlGroupState state[4];
  std::unique_ptr<Presonus::Panel::ControlGroup> groups[4];
  int clients = 0;
  Fixture() {
    for (int i = 0; i < 4; ++i) {
      state[i].tagOf = [](void *, const Presonus::Panel::Control *c) {
        return presonus::panel::ControlAccess::tag(
            *const_cast<Presonus::Panel::Control *>(c));
      };
      groups[i] = std::make_unique<Presonus::Panel::ControlGroup>(state[i]);
    }
    for (int i = 0; i < 64; ++i)
      controls.push_back(std::make_unique<ControlFixture>(i));
    for (int i : {100, 101}) {
      leds.push_back(std::make_unique<Presonus::Panel::LEDControl>(i, 0, -1));
      groups[0]->add(leds.back().get());
    }
  }
  Presonus::Panel::ControlGroup &group(int i) override { return *groups[i]; }
  Component &monitorParameters() override { return monitor; }
  const std::vector<presonus::rackpanel_port::Channel> &
  channels() const override {
    return channelList;
  }
  int numClients() const override { return clients; }
  void removeDelegate(Presonus::Panel::RackPanelComponent &) override {
    std::cout << "removeDelegate\n";
  }
  void blink(Presonus::Panel::LEDControl &led, int mode) override {
    std::cout << "blink " << presonus::panel::ControlAccess::tag(led) << ' '
              << mode << '\n';
    Dependencies::blink(led, mode);
  }
};
struct Target : Presonus::Panel::RackPanelComponent {
  explicit Target(Fixture &f) : RackPanelComponent(f) {}
  void add(Param *p) { paramList.add(p); }
  int notifications = 0;
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kChanged)
      ++notifications;
  }
};
} // namespace
int main(int argc, char **argv) {
  if (argc != 12)
    return 2;
  int a[11];
  for (int i = 0; i < 11; ++i)
    a[i] = static_cast<int>(std::stoll(argv[i + 1]));
  const int method = a[0], n = a[1], m = a[2], k = a[3], mask = a[4],
            tag = a[5], on = a[6], present = a[7], expired = a[8],
            status = a[9];
  const auto initial = static_cast<std::uint32_t>(std::stoull(argv[11]));
  Fixture f;
  Observer observer;
  Target target(f);
  auto *monitor = make(-1, "monitor");
  f.monitor.add(monitor);
  monitor->seed(initial);
  target.savedMonitorValue = value(initial);
  target.monitorRadioParameter = present ? monitor : nullptr;
  for (int t : {2, 3})
    target.add(make(t, "self:" + std::to_string(t)));
  if (present)
    for (int t : {20, 24})
      f.monitor.add(make(t, "source:" + std::to_string(t)));
  const int channelCount = std::max(n, std::max(m, k));
  for (int i = 0; i < channelCount; ++i) {
    auto c = std::make_unique<ComponentFixture>();
    for (int t : {307, 311, 312, 314, 315}) {
      auto *p = make(t, "ch" + std::to_string(i) + ":" + std::to_string(t));
      c->add(p);
      if (t == 314)
        p->addObserver(&observer);
    }
    if (i < n)
      f.channelList.push_back({c.get(), 10 + i});
    f.ownedChannels.push_back(std::move(c));
  }
  for (int i = 0; i < n; ++i)
    target.meterLEDs.push_back(f.controls[i].get());
  for (int i = 0; i < m; ++i)
    target.clipLEDs.push_back(f.controls[16 + i].get());
  for (int i = 0; i < k; ++i)
    target.phantomLEDs.push_back(f.controls[32 + i].get());
  if (method == 7) {
    target.phantomLEDs.clear();
    for (int i = 0; i < n; ++i)
      target.phantomLEDs.push_back(f.controls[32 + i].get());
  }
  for (int i = 0; i < n; ++i)
    if (mask & (1 << i)) {
      presonus::panel::ControlAccess::tag(*f.controls[i]) = 10 + i;
      f.groups[method == 5 ? 3 : 1]->add(f.controls[i].get());
    }
  if (method == 9) {
    // Only monitor control is exposed for this path; status LEDs are unrelated.
    f.state[0].controls.removeAll();
    presonus::panel::ControlAccess::tag(*f.controls[60]) = tag;
    presonus::panel::ControlAccess::parameter(*f.controls[60]) = monitor;
    f.groups[0]->add(f.controls[60].get());
  }
  monitor->addObserver(&target);
  target.observedParameter = present ? monitor : nullptr;
  Presonus::DelayTimer timer(1.f);
  presonus::timing::DelayTimerAccess::set(timer,
                                          {0, 1, expired ? 1 : 0, 1.f, false});
  target.panelStatus = status;
  f.clients = on;
  recording = true;
  switch (method) {
  case 1: {
    bool result = target.checkMonitorRestore(timer);
    std::cout << "return " << result << '\n';
    break;
  }
  case 2:
    target.monitorSource(tag, on);
    break;
  case 3:
    target.updatePanelStatus();
    break;
  case 4:
    target.attachMeterLEDs();
    break;
  case 5:
    target.attach48vControls();
    break;
  case 6:
    target.cleanup();
    target.notifications = 0;
    monitor->changed();
    std::cout << "attached " << (target.notifications != 0) << '\n';
    break;
  case 7:
    target.attach48vLEDs();
    break;
  case 8:
    target.detachLEDs();
    break;
  case 9:
    target.setupMonitorRadioButton(tag);
    std::cout << "saved " << bits(target.savedMonitorValue) << '\n'
              << "monitor " << (target.monitorRadioParameter != nullptr)
              << '\n';
    break;
  case 10:
    target.attachDigipots();
    break;
  default:
    return 3;
  }
  recording = false;
  monitor->removeObserver(&target);
  for (auto &c : f.ownedChannels)
    c->getParameterByTag(314)->removeObserver(&observer);
  return 0;
}
