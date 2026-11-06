#include "presonus/dice/packet_services.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/LEDNotifyTask.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/panel/RackPanelComponent.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
using namespace Presonus::Panel;
using Core::Portable::Parameter;
namespace {
std::vector<std::string> events;
std::uint64_t ticks;
bool capture = false;
RackPanelComponent *rack = nullptr;
PanelTask *appendTask = nullptr;
unsigned mutate = 0;
void emit(const std::string &e) {
  if (capture)
    events.push_back(e);
}
std::uint32_t bits(float f) {
  std::uint32_t b;
  std::memcpy(&b, &f, 4);
  return b;
}
struct Param : Core::Portable::NumericParam {
  static const Core::Portable::ParamInfo &makeInfo(int tag) {
    auto *info = new Core::Portable::ParamInfo{};
    info->tag = tag;
    info->maxValue = 1;
    return *info;
  }
  explicit Param(int tag) : NumericParam(makeInfo(tag), true) {}
  void setValue(float v, bool edit = false) override {
    emit("set:" + std::to_string(getTag()) + ":" + std::to_string(bits(v)) +
         ":" + std::to_string(edit));
    if (getTag() == 17 && mutate)
      rack->permissionFlags = mutate;
    NumericParam::setValue(v, edit);
  }
};
struct Controller : Core::Portable::ParamObserverBase {
  void paramChanged(Parameter *p, int message) override {
    if (message == Parameter::kEdit) {
      emit("edit:" + std::to_string(p->getTag()));
      if (appendTask) {
        assert(rack->tasks.add(appendTask));
        appendTask = nullptr;
      }
    }
  }
};
struct Component : Core::Portable::Component {
  Param *add(int tag) {
    auto *p = new Param(tag);
    paramList.add(p);
    return p;
  }
};
struct ControlProbe : Control {
  int id;
  ControlProbe(int id) : Control(id), id(id) {}
  bool setParameter(Parameter *p, int mode) override {
    emit("control:" + std::to_string(id) + ":" + std::to_string(p != nullptr));
    return Control::setParameter(p, mode);
  }
  void broadcastValue(int v) override {
    emit("value:" + std::to_string(id) + ":" + std::to_string(v));
  }
};
} // namespace
extern "C" std::int64_t
wrapTicks() asm("__wrap__ZN8presonus4dice19packetClockRawTicksEv");
extern "C" std::int64_t
realTicks() asm("__real__ZN8presonus4dice19packetClockRawTicksEv");
extern "C" std::int64_t wrapTicks() {
  emit("clock");
  std::int64_t value;
  std::memcpy(&value, &ticks, 8);
  return value;
}
int main(int argc, char **argv) {
  if (argc > 1 && std::string(argv[1]) == "provider") {
    // Exercise the actual production CCL gateway, not its deterministic
    // wrapper.
    const auto a = realTicks();
    const auto b = realTicks();
    assert(a > 0 && b >= a);
    Component c;
    auto *p = c.add(1);
    Controller controller;
    p->setController(&controller);
    capture = true;
    p->performEdit();
    capture = false;
    assert(events == std::vector<std::string>{"edit:1"});
    events.clear();
    capture = true;
    p->setValue(1.f, true);
    capture = false;
    assert(p->getValue() == 1.f);
    assert(events.size() == 2 && events[0] == "set:1:1065353216:1" &&
           events[1] == "edit:1");
    p->setController(nullptr);
    std::cout
        << "actual CCL clock and Parameter::performEdit controller passed\n";
    return 0;
  }
  int target, n, m, k, mask, flags, nt, nq, append, mutation;
  std::uint64_t start, delay;
  while (std::cin >> target >> ticks >> start >> delay >> flags >> mask >> n >>
         m >> k >> nt >> nq >> append >> mutation) {
    events.clear();
    capture = false;
    mutate = mutation;
    Presonus::Mixer::MixerComponentBase mixer;
    presonus::panel_binding::PanelRegistrarPortState state;
    PanelRegistrar registrar(state);
    struct RackProbe : RackPanelComponent {
      using RackPanelComponent::RackPanelComponent;
      void removeOne() { paramList.remove(getParameterByTag(1)); }
    };
    RackProbe panel(mixer, registrar);
    rack = &panel;
    Component network;
    if (mask & 2)
      network.add(12);
    if (mask & 4)
      network.add(17);
    panel.networkParameters = (mask & 1) ? &network : nullptr;
    if (!(mask & 8))
      panel.removeOne();
    panel.permissionFlags = flags;
    panel.permissionStartupMilliseconds = &start;
    std::vector<std::unique_ptr<ControlProbe>> controls;
    for (auto spec : {std::pair<int, int>{n, 0}, {m, 16}, {k, 32}})
      for (int i = 0; i < spec.first; ++i) {
        auto c = std::make_unique<ControlProbe>(spec.second + i);
        if (spec.second == 0)
          panel.meterLEDs.push_back(c.get());
        if (spec.second == 16)
          panel.clipLEDs.push_back(c.get());
        if (spec.second == 32)
          panel.phantomLEDs.push_back(c.get());
        controls.push_back(std::move(c));
      }
    Component standalone;
    auto *p = standalone.add(1);
    Controller controller;
    p->setController(&controller);
    std::vector<std::unique_ptr<PanelTask>> tasks;
    for (int i = 0; i < nt; ++i) {
      int kind, present;
      std::uint64_t duration, started;
      std::cin >> kind >> present >> duration >> started;
      if (kind)
        tasks.push_back(std::make_unique<LEDNotifyTask>(present ? p : nullptr,
                                                        duration, started));
      else
        tasks.push_back(std::make_unique<PanelTask>());
    }
    for (int i = 0; i < nq; ++i) {
      int id;
      std::cin >> id;
      assert(panel.tasks.add(tasks.at(id).get()));
    }
    appendTask = append ? tasks.at(append).get() : nullptr;
    capture = true;
    int result = -1;
    if (target == 1 || target == 2)
      result = tasks[0]->idle();
    else if (target == 3)
      panel.assignStaticIP();
    else if (target == 4)
      panel.assignDynamicIP();
    else if (target == 6)
      panel.checkNetworkReset();
    else if (target == 13)
      panel.idleTasks();
    capture = false;
    // Print exact side effects followed by observable queue identity/state.
    std::cout << events.size();
    for (const auto &e : events)
      std::cout << ' ' << e;
    std::cout << " | " << panel.permissionFlags << ' ' << result << ' '
              << panel.tasks.count();
    std::vector<LEDNotifyTask *> created;
    for (auto *t : panel.tasks) {
      int id = -1;
      for (int i = 0; i < nt; ++i)
        if (t == tasks[i].get())
          id = i;
      if (id < 0) {
        id = 100 + created.size();
        created.push_back(static_cast<LEDNotifyTask *>(t));
      }
      std::cout << ' ' << id;
    }
    std::cout << ' ' << created.size();
    for (auto *t : created)
      std::cout << ' ' << (t->parameter != nullptr) << ' ' << t->delay << ' '
                << t->start;
    std::cout << '\n';
    p->setController(nullptr);
    appendTask = nullptr;
    rack = nullptr;
  }
}
