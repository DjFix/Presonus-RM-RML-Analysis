#include "core/public/corestringbuffer.h"
#include "presonus/mixer/FilterGroupManager.hpp"
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Core::Portable;
struct Observer : ParamObserverBase {
  Component &root;
  std::vector<std::string> events;
  explicit Observer(Component &r) : root(r) {}
  void paramChanged(Parameter *p, int msg) override {
    std::ostringstream out;
    for (int i = 0; i < root.countChildren(); ++i)
      for (int j = 0; j < root.getChild(i)->countParameters(); ++j)
        if (root.getChild(i)->getParameterAt(j) == p) {
          out << i << ' ' << j << ' ' << msg;
          for (int k = 0; k < root.countChildren(); ++k)
            out << ' '
                << std::quoted(
                       static_cast<const char *>(root.getChild(k)->getName()));
        }
    events.push_back(out.str());
  }
};
int main(int argc, char **argv) {
  const bool provider = argc > 1 && std::string(argv[1]) == "--provider";
  int n;
  while (std::cin >> n) {
    Presonus::Mixer::FilterGroupManager root("filters");
    Observer observer(root);
    std::vector<std::vector<ParamInfo>> descriptors(n);
    for (int i = 0; i < n; ++i) {
      std::string name;
      int count;
      std::cin >> std::quoted(name) >> count;
      auto *child = new Component(name.c_str());
      descriptors[i].resize(count);
      for (int j = 0; j < count; ++j) {
        descriptors[i][j] = {};
        descriptors[i][j].type = ParamInfo::kFloat;
        descriptors[i][j].tag = j;
        descriptors[i][j].maxValue = 1;
      }
      child->addParameters(descriptors[i].data(), count);
      for (int j = 0; j < count; ++j)
        child->getParameterAt(j)->addObserver(&observer);
      root.addChild(child);
    }
    if (provider) {
      auto list = std::make_unique<Core::Vector<Component *>>();
      std::string op;
      while (std::cin >> op && op != "done") {
        if (op == "resize") {
          int count;
          std::cin >> count;
          list->resize(count);
          std::cout << list->count();
        } else if (op == "format") {
          int value;
          std::cin >> value;
          Core::CString32 text;
          text.appendFormat("ch%d", value);
          std::cout << std::quoted(static_cast<const char *>(text));
        } else if (op == "add") {
          int i;
          std::cin >> i;
          list->add(root.getChild(i));
          std::cout << list->count();
        } else if (op == "set") {
          int i;
          std::string name;
          std::cin >> i >> std::quoted(name);
          root.getChild(i)->setName(name.c_str());
          std::cout << 1;
        } else if (op == "count") {
          int i;
          std::cin >> i;
          std::cout << root.getChild(i)->countParameters();
        } else if (op == "at") {
          int i, j;
          std::cin >> i >> j;
          auto *p = root.getChild(i)->getParameterAt(j);
          if (!p)
            throw std::runtime_error("missing parameter");
          std::cout << p->getTag();
        } else if (op == "changed") {
          int i, j;
          std::cin >> i >> j;
          root.getChild(i)->getParameterAt(j)->changed();
          std::cout << std::quoted(observer.events.back());
        } else if (op == "destroy") {
          list.reset();
          std::cout << 1;
        } else
          throw std::runtime_error("unknown provider operation");
        std::cout << '\n' << std::flush;
      }
    } else {
#ifndef PROVIDER_ONLY
      root.resetChannelNames();
#else
      throw std::runtime_error("provider only executable");
#endif
      std::cout << n;
      for (int i = 0; i < n; ++i)
        std::cout << ' '
                  << std::quoted(static_cast<const char *>(
                         root.getChild(i)->getName()));
      std::cout << '\n' << observer.events.size() << '\n';
      for (const auto &event : observer.events)
        std::cout << event << '\n';
    }
    // Remove test observers while both their receivers and descriptors live.
    for (int i = 0; i < n; ++i)
      for (int j = 0; j < root.getChild(i)->countParameters(); ++j)
        root.getChild(i)->getParameterAt(j)->removeObserver(&observer);
  }
}
