#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/MasterSectionComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <iostream>
#include <memory>
#include <string>
#include <vector>

using Core::Portable::Component;
using Core::Portable::NumericParam;
using Core::Portable::ParamInfo;
using Core::Portable::ParamValue;
using Presonus::Mixer::ChannelComponent;
using Presonus::Mixer::MasterSectionComponent;
using Presonus::Mixer::MixerComponentBase;

namespace {
class ObservedValue : public NumericParam {
public:
  ObservedValue(const ParamInfo &info, int index)
      : NumericParam(info), index(index) {
    NumericParam::setValue(1.f, false);
  }
  void setValue(ParamValue value, bool edit) override {
    std::cout << 'p' << index << ':' << value << ':' << edit << '\n';
    NumericParam::setValue(value, edit);
  }

private:
  int index;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string sequence(argv[1]);
  ParamInfo info{};
  info.minValue = 0.f;
  info.maxValue = 2.f;
  std::vector<presonus::mixer::ChannelState> state(sequence.size());
  std::vector<std::unique_ptr<ChannelComponent>> storage;
  std::vector<std::unique_ptr<ObservedValue>> parameters;
  Core::Vector<ChannelComponent *> channels;
  for (std::size_t i = 0; i < sequence.size(); ++i) {
    if (sequence[i] != 'z') {
      parameters.push_back(std::make_unique<ObservedValue>(info, i));
      state[i].solo = parameters.back().get();
    }
    storage.push_back(std::make_unique<ChannelComponent>(
        ChannelComponent::SourcePortConstruction{}, state[i]));
    channels.add(storage.back().get());
  }

  bool clearedBeforeMaster = false;
  NumericParam slot(info);
  Component component;
  Presonus::DelayTimer timer(0.f);
  presonus::mixer_port::MasterBindings bindings{component, {}, timer};
  bindings.slots.fill(&slot);
  bindings.isSlave = [&] {
    clearedBeforeMaster = true;
    for (const auto &p : parameters)
      clearedBeforeMaster &= p->getValue() == 0.f;
    std::cout << "master\n";
    return false;
  };
  bindings.isMaster = [] { return false; };
  bindings.countSolos = [](int) { return 0; };
  MasterSectionComponent master(bindings);

  MixerComponentBase mixer;
  mixer.soloMasterSection = &master;
  mixer.sceneChannels = &channels;
  mixer.clearSolos();
  return clearedBeforeMaster && bindings.dirty ? 0 : 1;
}
