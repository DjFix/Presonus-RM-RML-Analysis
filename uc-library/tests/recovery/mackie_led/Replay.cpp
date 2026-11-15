#include "presonus/MackieControlComponent.hpp"
#include <iostream>
#include <string>
using namespace Core::Portable;
struct Observer : ParamObserverBase {
  int changedCount{}, editCount{};
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kChanged)
      ++changedCount;
    if (msg == Parameter::kEdit)
      ++editCount;
  }
};
int main() {
  int present, state, unused;
  std::string text;
  while (std::cin >> present >> state >> unused >> text) {
    Presonus::MackieControlComponent component;
    const ParamInfo infos[] = {PARAM_TOGGLE(37, "led", 0, nullptr, 0),
                               PARAM_STRING(38, "text", 0)};
    component.addParameters(infos, 2);
    auto *p = component.getParameterByTag(37);
    Observer observer, controller;
    p->addObserver(&observer);
    p->setController(&controller);
    p->setFeedbackNeeded(true);
    const char *value = text == "~" ? "" : text.c_str();
    component.updateLedState(present ? 37 : -777, state);
    char result[256]{};
    p->toString(result, sizeof(result));
    std::cout << p->getValue();
    std::cout << ' ' << observer.changedCount << ' ' << observer.editCount
              << ' ' << controller.changedCount << ' ' << controller.editCount
              << '\n';
    p->removeObserver(&observer);
    p->setController(nullptr);
  }
}
