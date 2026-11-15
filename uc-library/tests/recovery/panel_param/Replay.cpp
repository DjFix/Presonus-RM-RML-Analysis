#include "presonus/panel/PanelComponent.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
using Core::Portable::Component;
using Core::Portable::Parameter;
struct Panel : Presonus::Panel::PanelComponent {
  Panel() = default;
  explicit Panel(presonus::panel_port::PanelCore &c) : PanelComponent(c) {}
};
struct Owner : presonus::panel_port::PanelCore {
  Panel *panel = nullptr;
  void paramChanged(Parameter *p, int msg) override {
    assert(panel);
    panel->paramChanged(p, msg);
  }
};
struct Observer : Core::Portable::ParamObserverBase {
  Panel &panel;
  bool direct;
  Parameter *expected = nullptr;
  int count = 0;
  Observer(Panel &p, bool d) : panel(p), direct(d) {}
  void paramChanged(Parameter *p, int msg) override {
    assert(p == expected && msg == Parameter::kChanged);
    ++count;
    if (direct)
      panel.portableState().component.Component::paramChanged(p, msg);
    else
      panel.paramChanged(p, msg);
  }
};
int main(int argc, char **argv) {
  assert(argc == 8);
  bool direct = std::atoi(argv[1]), injected = std::atoi(argv[2]);
  bool storable = std::atoi(argv[3]), dirty = std::atoi(argv[4]);
  int message = static_cast<int>(std::strtol(argv[5], nullptr, 10));
  bool feedback = std::atoi(argv[6]), nullParameter = std::atoi(argv[7]);
  Owner owner;
  Panel owned, borrowed(owner);
  Panel &panel = injected ? borrowed : owned;
  owner.panel = &panel;
  auto &s = panel.portableState();
  auto *identity = &s.component;
  auto *allocation = s.ownedComponent.get();
  s.active = true;
  s.embeddedHandlerState = {9, 8, 7, 6, 5};
  auto words = s.embeddedHandlerState;
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.name[0] = 'p';
  Core::Portable::NumericParam parameter(info);
  parameter.setStorable(storable);
  s.component.setNeedsSave(dirty);
  Observer observer(panel, direct);
  observer.expected = &parameter;
  auto *p = nullParameter ? nullptr : &parameter;
  assert(!nullParameter || message != Parameter::kChanged);
  if (feedback) {
    parameter.setController(&observer);
    parameter.setFeedbackNeeded(true);
    parameter.addObserver(&observer);
    parameter.changed();
    parameter.removeObserver(&observer);
    parameter.setController(nullptr);
    assert(observer.count == 2);
  } else if (direct)
    s.component.Component::paramChanged(p, message);
  else if (injected)
    owner.paramChanged(p, message);
  else
    panel.paramChanged(p, message);
  assert(identity == &s.component && allocation == s.ownedComponent.get());
  assert(s.active && words == s.embeddedHandlerState && !s.mixer &&
         !s.registrar);
  assert(s.component.feedbackNeeded());
  bool expectedDirty =
      dirty || (storable && (feedback || message == Parameter::kChanged));
  assert(s.component.needsSave() == expectedDirty);
  std::cout << s.component.needsSave() << ',' << observer.count
            << ",state-preserved\n";
}
