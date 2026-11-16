#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/mixer/ParamLink.hpp"
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string>
struct Root : Core::Portable::Component {
  void add(Core::Portable::Parameter *p) { paramList.add(p); }
};
struct Param : Core::Portable::NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
};
struct Target : Param {
  using Param::Param;
  int stringCalls = 0;
  std::string last;
  void fromString(const char *s, bool edit) override {
    ++stringCalls;
    last = s;
    NumericParam::fromString(s, edit);
  }
};
struct Witness : Core::Portable::ParamObserverBase {
  int changes = 0;
  void paramChanged(Core::Portable::Parameter *, int reason) override {
    if (reason == Core::Portable::Parameter::kChanged)
      ++changes;
  }
};
int stringCases() {
  for (const auto &text : {std::string(), std::string("7.25"),
                           std::string("4.5") + std::string(80, ' ')}) {
    Core::Portable::ParamInfo stringInfo{};
    stringInfo.type = Core::Portable::ParamInfo::kString;
    std::strcpy(stringInfo.name, "source");
    Core::Portable::StringParam source(stringInfo);
    source.fromString(text.c_str(), false);
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = -100;
    info.maxValue = 100;
    std::strcpy(info.name, "gain");
    Root root;
    auto *target = new Target(info);
    root.add(target);
    Presonus::MixerClientComponentBase identity;
    Presonus::Mixer::ParamLink link(&source, "gain", true);
    link.portableBindClientRoot(identity, root);
    Witness witness;
    source.addObserver(&witness);
    link.connect(&identity);
    std::cout << "SROW " << witness.changes << ' ' << target->stringCalls << ' '
              << std::quoted(target->last) << ' ' << target->getValue() << '\n';
    source.removeObserver(&witness);
    link.connect(nullptr);
  }
  return 0;
}
int main(int argc, char **) {
  if (argc > 1)
    return stringCases();
  int src, flag, found, client, old;
  while (std::cin >> src >> flag >> found >> client >> old) {
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = -100;
    info.maxValue = 100;
    std::strcpy(info.name, "gain");
    Param source(info), previous(info);
    source.setValue(4.5f, false);
    Root root;
    Param *target = new Param(info);
    if (found)
      root.add(target); // CCL owns registered parameter.
    Presonus::MixerClientComponentBase identity;
    Presonus::Mixer::ParamLink link(src ? &source : nullptr, "gain", flag);
    link.portableBindClientRoot(identity, root);
    if (old) {
      link.portableSetTarget(&previous);
      previous.addObserver(&link);
    }
    link.connect(client ? &identity : nullptr);
    std::cout << "ROW " << (link.portableTarget() != nullptr) << ' '
              << previous.observers() << ' ' << target->observers() << ' '
              << target->getValue() << ' ' << source.getValue() << '\n';
    link.connect(nullptr);
    if (!found)
      delete target;
  }
}
