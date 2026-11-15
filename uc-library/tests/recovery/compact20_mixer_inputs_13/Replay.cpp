#include "core/portable/coreparams.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/TalkbackInputComponent.hpp"
#include <iostream>
#include <stdexcept>
using namespace Core::Portable;
class Probe : public NumericParam {
public:
  using NumericParam::NumericParam;
  int count(IParamObserver *observer) const {
    for (int i = 0; i < observerList.count(); ++i)
      if (observerList[i] != observer)
        throw std::runtime_error("wrong actual observer identity");
    return observerList.count();
  }
};
class Settings : public Component {
public:
  void adopt(Parameter *p) { paramList.add(p); }
};
int main() {
  int present, number;
  while (std::cin >> present >> number) {
    ParamInfo infos[2]{};
    infos[0].tag = 49;
    infos[1].tag = 5;
    Settings settings;
    auto *first = new Probe(infos[0]);
    auto *second = new Probe(infos[1]);
    settings.adopt(first);
    settings.adopt(second);
    Presonus::Mixer::MixerComponentBase mixer;
    mixer.sceneSettings = present ? &settings : nullptr;
    using Talkback = Presonus::Mixer::TalkbackInputComponent;
    Talkback component(
        Presonus::Mixer::ChannelComponent::SourcePortConstruction{});
    Talkback::SourcePortState state;
    state.mixer = &mixer;
    component.bindTalkbackState(state);
    auto *observer = static_cast<IParamObserver *>(&component);
    for (int i = 0; i < number; ++i) {
      int add;
      std::cin >> add;
      component.addRemoveObservers(add != 0);
      std::cout << first->count(observer) << ' ' << second->count(observer)
                << ' ';
    }
    // Use the real explicit remove operation before destruction, preserving
    // borrowed lifetimes.
    while (first->count(observer) || second->count(observer))
      component.addRemoveObservers(false);
    std::cout << '\n';
  }
}
