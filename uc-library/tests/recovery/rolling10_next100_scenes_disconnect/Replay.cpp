#include "presonus/surface/ScenesPageComponent.hpp"
#include <cassert>
#include <iostream>
#include <string>
#include <vector>
using namespace Core::Portable;
struct Observer : IParamObserver {
  void *castTo(int) override { return nullptr; }
  std::vector<int> events;
  void paramChanged(Parameter *p, int msg) override {
    events.push_back(p->getTag() * 100 + msg);
  }
};
int main(int argc, char **argv) {
  std::string mode = argc > 1 ? argv[1] : "replay";
  int mask, repeats, n;
  while (std::cin >> mask >> repeats >> n) {
    const ParamInfo ni = PARAM_FLOAT(1, "number", 0.f, 100.f, 0.f, 2.f, nullptr,
                                     nullptr, 1.f, 0);
    const ParamInfo si = PARAM_STRING(2, "text", 0);
    NumericParam number(ni);
    StringParam text(si);
    ParamList list;
    auto *a = static_cast<AliasParam *>(list.addAlias(3, "aliasA"));
    auto *b = static_cast<AliasParam *>(list.addAlias(4, "aliasB"));
    a->setOriginal(mask & 1 ? &number : nullptr);
    b->setOriginal(mask & 2 ? static_cast<Parameter *>(&text) : nullptr);
    Parameter *pool[] = {nullptr, &number, &text, a, b};
    Core::Vector<Parameter *> extra;
    for (int i = 0, id; i < n; ++i) {
      std::cin >> id;
      assert(id >= 0 && id < 5);
      extra.add(pool[id]);
    }
    if (mode == "providers") {
      for (int i = 0; i < n; ++i)
        std::cout << (extra[i] && AliasParam::cast(extra[i]) != nullptr) << ' ';
      std::cout << '\n';
      continue;
    }
    Observer observer;
    a->addObserver(&observer);
    b->addObserver(&observer);
    if (mode == "oracle") {
      int calls;
      std::cin >> calls;
      for (int i = 0, index; i < calls; ++i) {
        std::cin >> index;
        assert(index >= 0 && index < n);
        auto *alias = AliasParam::cast(extra[index]);
        assert(alias);
        alias->setOriginal(nullptr);
      }
    } else {
      Presonus::Surface::ScenesPageComponent page({}, extra);
      for (int i = 0; i < repeats; ++i)
        page.disconnectMappables();
    }
    std::cout << (a->getOriginal() != nullptr) << ' '
              << (b->getOriginal() != nullptr) << ' ' << observer.events.size();
    for (auto e : observer.events)
      std::cout << ' ' << e;
    // An original parameter change must reach only aliases still connected.
    observer.events.clear();
    number.setValue(9.f, true);
    text.fromString("new", true);
    std::cout << ' ' << observer.events.size();
    for (auto e : observer.events)
      std::cout << ' ' << e;
    std::cout << '\n';
    a->removeObserver(&observer);
    b->removeObserver(&observer);
  }
}
