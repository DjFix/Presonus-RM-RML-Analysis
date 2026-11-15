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
    auto *p = component.getParameterByTag(38);
    Observer observer, controller;
    p->addObserver(&observer);
    p->setController(&controller);
    p->setFeedbackNeeded(true);
    const char *value = text == "~" ? "" : text.c_str();
    component.updateTextDisplay(present ? 38 : -777, value, unused);
    char result[256]{};
    p->toString(result, sizeof(result));
    std::cout << (result[0] ? result : "~");
    std::cout << ' ' << observer.changedCount << ' ' << observer.editCount
              << ' ' << controller.changedCount << ' ' << controller.editCount
              << '\n';
    p->removeObserver(&observer);
    p->setController(nullptr);
  }
}
