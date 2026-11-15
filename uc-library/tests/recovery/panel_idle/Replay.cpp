#include "presonus/panel/PanelComponent.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <vector>
using Core::Portable::Component;
struct Panel : Presonus::Panel::PanelComponent {
  Panel() = default;
  explicit Panel(presonus::panel_port::PanelCore &c) : PanelComponent(c) {}
};
struct Child : Component {
  std::vector<int> &trace;
  int id;
  Child(std::vector<int> &t, int n) : trace(t), id(n) {}
  void onIdle() override {
    trace.push_back(id);
    Component::onIdle();
  }
};
// This override deliberately routes through the port. A virtual Core call in
// PanelComponent would recurse for injected owners; the qualified base call
// must preserve the provider traversal while bypassing this adapter override.
struct Owner : presonus::panel_port::PanelCore {
  Panel *panel = nullptr;
  void onIdle() override {
    assert(panel);
    panel->onIdle();
  }
};
int main(int argc, char **argv) {
  assert(argc == 5);
  bool direct = std::atoi(argv[1]), injected = std::atoi(argv[2]);
  int count = std::atoi(argv[3]);
  bool dirty = std::atoi(argv[4]);
  Owner owner;
  Panel owned, borrowed(owner);
  Panel &panel = injected ? borrowed : owned;
  owner.panel = &panel;
  auto &s = panel.portableState();
  auto *identity = &s.component;
  auto *allocation = s.ownedComponent.get();
  s.active = true;
  s.embeddedHandlerState = {12, 34, -56, 78, 90};
  auto words = s.embeddedHandlerState;
  s.component.setNeedsSave(dirty);
  std::vector<int> trace;
  for (int i = 0; i < count; ++i) {
    auto *child = new Child(trace, i * 2);
    child->addChild(new Child(trace, i * 2 + 1));
    s.component.addChild(child);
  }
  if (direct)
    s.component.Component::onIdle();
  else if (injected)
    owner.onIdle();
  else
    panel.onIdle();
  assert(identity == &s.component && allocation == s.ownedComponent.get());
  assert(s.active && words == s.embeddedHandlerState && !s.mixer &&
         !s.registrar);
  assert(s.component.needsSave() == dirty && s.component.feedbackNeeded());
  assert(s.component.countChildren() == count);
  assert(trace.size() == static_cast<unsigned>(count * 2));
  for (unsigned i = 0; i < trace.size(); ++i) {
    assert(trace[i] == static_cast<int>(i));
    std::cout << trace[i] << ',';
  }
  std::cout << "state-preserved\n";
}
