#include "core/portable/corecomponent.h"
#ifndef PROVIDER_ONLY
#include "presonus/panel/JoinNetworkPage.hpp"
#endif
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
struct Tree : Core::Portable::Component {
  void add(Core::Portable::Parameter *p) { paramList.add(p); }
};
struct Observer : Core::Portable::ParamObserverBase {
  std::vector<int> events;
  void paramChanged(Core::Portable::Parameter *p, int msg) override {
    if (p->getTag() != 8)
      std::abort();
    events.push_back(msg);
  }
};
int main(int argc, char **argv) {
  bool provider = argc > 1 && std::string(argv[1]) == "provider";
  unsigned index, repeats;
  const std::string inputs[] = {"", "network", "HD wifi", std::string(200, 'x'),
                                "\xc3\xa9\xe7\xbd\x91"};
  while (std::cin >> index >> repeats) {
    if (index >= 5 || repeats < 1 || repeats > 2)
      return 2;
    Core::Portable::ParamInfo info{}, other{};
    info.type = other.type = Core::Portable::ParamInfo::kString;
    info.tag = 8;
    other.tag = 9;
    Tree tree;
    auto *p = new Core::Portable::StringParam(info);
    auto *q = new Core::Portable::StringParam(other);
    tree.add(q);
    tree.add(p);
    p->fromString(inputs[index].c_str(), false);
    q->fromString("keep", false);
    Observer observer;
    p->addObserver(&observer);
#ifndef PROVIDER_ONLY
    Presonus::Panel::JoinNetworkPage page(tree);
#endif
    for (unsigned i = 0; i < repeats; ++i) {
      if (provider)
        tree.getParameterByTag(8)->fromString("", false);
#ifndef PROVIDER_ONLY
      else
        page.recall();
#endif
    }
    char text[256], unchanged[256];
    p->toString(text, 256);
    q->toString(unchanged, 256);
    if (std::strcmp(unchanged, "keep") || p->isEditing())
      return 3;
    std::cout << p->getTag() << ' ' << std::strlen(text) << ' '
              << observer.events.size();
    for (int e : observer.events)
      std::cout << ' ' << e;
    std::cout << '\n';
    p->removeObserver(&observer);
  }
}
