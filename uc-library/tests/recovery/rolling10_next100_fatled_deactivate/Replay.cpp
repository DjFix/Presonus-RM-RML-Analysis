#include "core/portable/corecomponent.h"
#include "presonus/panel/FATLEDOverridePage.hpp"
#include <iostream>
#include <vector>
struct Observer : Core::Portable::Component {
  std::vector<int> events;
  void paramChanged(Core::Portable::Parameter *, int msg) override {
    events.push_back(msg);
  }
};
int main(int argc, char **argv) {
  bool direct = argc > 1;
  int present, calls;
  float initial, min, max;
  while (std::cin >> present >> initial >> min >> max >> calls) {
    const Core::Portable::ParamInfo info =
        PARAM_FLOAT(0, "override", min, max, min, 0, nullptr, nullptr, 0, 0);
    Core::Portable::NumericParam parameter(info);
    parameter.setValue(initial, false);
    Observer observer;
    parameter.addObserver(&observer);
    parameter.setController(&observer);
    parameter.setFeedbackNeeded(true);
    Presonus::Panel::FATLEDOverridePage page(
        Presonus::Panel::FATLEDOverridePage::SourcePortConstruction{},
        present ? &parameter : nullptr);
    if (direct) {
      for (int i = 0; i < calls; ++i) {
        unsigned bits;
        int edit;
        std::cin >> bits >> edit;
        float v;
        static_assert(sizeof(v) == sizeof(bits));
        __builtin_memcpy(&v, &bits, 4);
        parameter.setValue(v, edit);
      }
    } else {
      page.deactivate();
      page.deactivate();
    }
    std::cout << parameter.getValue() << ' ' << observer.events.size();
    for (int e : observer.events)
      std::cout << ' ' << e;
    std::cout << '\n';
    parameter.removeObserver(&observer);
    parameter.setController(nullptr);
  }
}
