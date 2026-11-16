#include "presonus/surface/MonitorPageComponent.hpp"
#include <array>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>
using namespace Core::Portable;
struct Observer : ParamObserverBase {
  int changed = 0;
  void paramChanged(Parameter *, int message) override {
    if (message == Parameter::kChanged)
      ++changed;
  }
};
int main(int argc, char **argv) {
  bool provider = argc == 2 && std::string(argv[1]) == "--provider";
  const char *names[] = {"monitor", "monitorx", "xmonitor",     "route",
                         "routex",  "xroute",   "monitorroute", "route_monitor",
                         "",        "unrelated"};
  int message, nameIndex, tag, operations;
  while (std::cin >> message >> nameIndex >> tag >> operations) {
    std::array<ParamInfo, 24> infos{};
    std::array<std::array<char, 12>, 23> titles{};
    Observer observer;
    Component registry;
    for (int i = 0; i < 23; ++i) {
      infos[i].type = ParamInfo::kFloat;
      infos[i].tag = 100 + i;
      std::strcpy(infos[i].name,
                  100 + i == tag ? names[nameIndex] : "ordinary");
      infos[i].minValue = 0;
      infos[i].maxValue = 1;
      infos[i].defaultValue = i == 10 ? 1.f : 0.f;
      std::snprintf(titles[i].data(), titles[i].size(), "T%d", i + 100);
      infos[i].title = titles[i].data();
    }
    infos[23].type = ParamInfo::kString;
    infos[23].tag = 500;
    std::strcpy(infos[23].name, "monitorlist");
    registry.addParameters(infos.data(), infos.size());
    for (int i = 100; i <= 122; ++i)
      registry.getParameterByTag(i)->addObserver(&observer);
    registry.getParameterByTag(500)->addObserver(&observer);
    Presonus::Surface::MonitorPageComponent target(
        Presonus::Surface::MonitorPageComponent::SourcePortConstruction{},
        registry);
    auto *selected = registry.getParameterByTag(tag);
    if (provider) {
      // Operations are independently observed native application calls, not
      // predicates copied from the reconstructed dispatcher.
      if (operations & 1)
        target.radioSelection(selected, 100, 102);
      if (operations & 2)
        target.radioSelection(selected, 103, 121);
      if (operations & 4)
        target.applyMonitorSelection();
    } else
      target.paramChanged(selected, message);
    std::cout << observer.changed << ' ' << target.monitorSelectionInProgress();
    for (int i = 100; i <= 122; ++i)
      std::cout << ' ' << registry.getParameterByTag(i)->getValue();
    char destination[32]{};
    registry.getParameterByTag(500)->toString(destination, sizeof destination);
    std::cout << ' ' << (destination[0] ? destination : "EMPTY") << '\n';
    for (int i = 100; i <= 122; ++i)
      registry.getParameterByTag(i)->removeObserver(&observer);
    registry.getParameterByTag(500)->removeObserver(&observer);
  }
}
