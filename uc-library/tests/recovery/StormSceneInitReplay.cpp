#include "presonus/StormMixSceneComponent.hpp"
#include <array>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using namespace Core::Portable;
struct Recall : presonus::scene_port::Recall {
  bool recall(unsigned int) const override { return false; }
};
struct Scene : Presonus::StormMixSceneComponent {
  using StormMixSceneComponent::StormMixSceneComponent;
  void add(Parameter *p) { paramList.add(p); }
};
struct Observer : ParamObserverBase {
  int changed = 0, other = 0;
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kChanged)
      ++changed;
    else
      ++other;
  }
};
struct Text : StringParam {
  std::vector<std::string> &calls;
  Text(const ParamInfo &info, std::vector<std::string> &calls)
      : StringParam(info), calls(calls) {}
  void fromString(const char *name, bool edit) override {
    calls.push_back(std::to_string(getTag()) + ":" + name + ":" +
                    std::to_string(edit));
    StringParam::fromString(name, edit);
  }
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream fixtures(argv[1]);
  if (!fixtures)
    return 3;
  std::string line;
  int cases = 0;
  while (std::getline(fixtures, line)) {
    std::istringstream row(line);
    unsigned mask;
    row >> mask;
    std::string expected;
    std::getline(row, expected);
    if (!expected.empty())
      expected.erase(0, 1);
    std::array<ParamInfo, 10> infos{};
    Recall recall;
    Observer observer;
    Scene scene(recall);
    std::vector<std::string> calls;
    std::vector<Text *> parameters;
    for (int tag = 9; tag <= 18; ++tag) {
      if (tag >= 10 && tag <= 17 && !(mask & (1U << (tag - 10))))
        continue;
      auto &info = infos[tag - 9];
      info.tag = tag;
      auto *p = new Text(info, calls);
      p->fromString("before", false);
      p->addObserver(&observer);
      p->setController(&observer);
      scene.add(p);
      parameters.push_back(p);
    }
    calls.clear();
    scene.init();
    std::string actual;
    for (auto &call : calls) {
      if (!actual.empty())
        actual += "|";
      actual += call;
    }
    if (actual != expected) {
      std::cerr << mask << " actual=" << actual << " expected=" << expected
                << "\n";
      return 10;
    }
    int count = 0;
    for (unsigned i = 0; i < 8; ++i)
      if (mask & (1U << i))
        ++count;
    if (observer.changed != count || observer.other != 0)
      return 11;
    for (auto *p : parameters) {
      const std::string want =
          p->getTag() < 10 || p->getTag() > 17
              ? "before"
              : "Mix Scene " + std::to_string(p->getTag() - 9);
      if (std::string(p->getText()) != want)
        return 12;
    }
    calls.clear();
    scene.init();
    if (observer.changed != count || observer.other != 0)
      return 13;
    for (auto *p : parameters) {
      p->removeObserver(&observer);
      p->setController(nullptr);
    }
    ++cases;
  }
  if (cases != 256)
    return 14;
  std::cout << cases
            << " native-mask fixtures; actual init/helper/CCL StringParam; "
               "unchanged repeat, non-target and observer/edit checks passed\n";
}
