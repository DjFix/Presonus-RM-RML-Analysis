#include "core/portable/coreparams.h"
#include "presonus/mixer/GEQComponent.hpp"
#include <iostream>
#include <utility>
#include <vector>
using namespace Core::Portable;
BEGIN_PARAMINFO(baseInfo)
PARAM_FLOAT_(0, "band", -100, 100, 0, .001, "", "", 0, 0, "Band", nullptr)
END_PARAMINFO
struct Observer : ParamObserverBase {
  std::vector<std::pair<int, int>> events;
  void paramChanged(Parameter *p, int msg) override {
    events.emplace_back(p->getTag(), msg);
  }
};
static bool present(int c, int t) {
  return c == 2 || (c == 1 && (t == 0 || t == 15 || t == 30)) ||
         (c == 3 && t % 3 == 0);
}
static void setup(Component &owner, int c, std::vector<ParamInfo> &infos,
                  Observer &observer) {
  infos.reserve(33);
  for (int t = -1; t <= 31; ++t) {
    if (t >= 0 && t <= 30 && !present(c, t))
      continue;
    infos.push_back(baseInfo[0]);
    auto &i = infos.back();
    i.tag = t;
    i.defaultValue = float(t % 5 - 2);
    owner.addParameters(&i, 1);
    auto *p = NumericParam::cast(owner.getParameterByTag(t));
    p->setValueFast(t % 2 ? i.defaultValue : i.defaultValue + 3);
    p->setController(&observer);
  }
  observer.events.clear();
}
int main(int argc, char **) {
  bool inventory = argc > 1;
  for (int c = 0; c < 4; ++c) {
    Observer expected, actual;
    std::vector<ParamInfo> ei, ai;
    Component provider;
    Presonus::Mixer::GEQComponent owner(
        Presonus::Mixer::GEQComponent::SourcePortConstruction{});
    setup(provider, c, ei, expected);
    setup(owner, c, ai, actual);
    if (inventory) {
      std::cout << c;
      for (int t = 0; t < 31; ++t)
        std::cout << ' ' << (provider.getParameterByTag(t) != nullptr);
      std::cout << '\n';
      continue;
    }
    int count;
    std::cin >> count;
    for (int i = 0; i < count; ++i) {
      int tag, edit;
      std::cin >> tag >> edit;
      auto *p = provider.getParameterByTag(tag);
      if (!p || edit != 1)
        return 2;
      p->resetValue(true);
    }
    owner.flatten();
    for (int t = -1; t <= 31; ++t) {
      auto *e = provider.getParameterByTag(t), *a = owner.getParameterByTag(t);
      if (bool(e) != bool(a))
        return 3;
      if (e && e->getValue() != a->getValue())
        return 4;
    }
    if (expected.events != actual.events)
      return 5;
    std::cout << c << ' ' << actual.events.size();
    for (auto [tag, msg] : actual.events)
      std::cout << ' ' << tag << ' ' << msg;
    std::cout << '\n';
    // Clear borrowed observers before their destruction; Component retains
    // parameter ownership.
    for (int i = 0; i < provider.countParameters(); ++i)
      provider.getParameterAt(i)->setController(nullptr);
    for (int i = 0; i < owner.countParameters(); ++i)
      owner.getParameterAt(i)->setController(nullptr);
  }
}
