#include "presonus/mixer/MasterSectionComponent.hpp"
#include "presonus/mixer/MixerComponent.hpp"
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>

using namespace Presonus::Mixer;
using namespace Core::Portable;

namespace {
class ObservedSolo : public NumericParam {
public:
  ObservedSolo(const ParamInfo &info, MixerComponentBase &mixer, int i)
      : NumericParam(info), mixer(mixer), i(i) {
    NumericParam::setValue(1.f, false);
  }
  void setValue(ParamValue value, bool edit) override {
    std::cout << "set:" << i << ':' << value << ':' << edit << ':'
              << mixer.sceneRecallBlocksTag14 << ':'
              << mixer.sipMuteSnapshotPending << '\n';
    NumericParam::setValue(value, edit);
  }

private:
  MixerComponentBase &mixer;
  int i;
};
class MixerServices : public presonus::mixer_component_port::MixerServices {
public:
  explicit MixerServices(MixerComponentBase &mixer) : mixer(mixer) {}
  void serverParamChanged(MixerComponent &, Parameter *, int) override {}
  Component &parameterComponent(ChannelComponent &channel) const override {
    return channel;
  }
  Presonus::LinkableComponent *linkIdentity(ChannelComponent *) const override {
    return nullptr;
  }
  const IStorageFilter *storageFilter(int selector, bool edit) override {
    if (edit)
      throw std::runtime_error("unexpected edit flag");
    std::cout << "restore:" << selector << ':' << mixer.sceneRecallBlocksTag14
              << ':' << mixer.sipMuteSnapshotPending << '\n';
    return nullptr;
  }
  void load(const InputStorage &storage) override {
    loaded = storage.getAttributes().contains("mute");
  }
  void save(OutputStorage &) override {}
  bool muteExcluded(const ChannelComponent &) const override { return false; }
  Parameter &muteSource(ChannelComponent &) override {
    throw std::runtime_error("unexpected mute read");
  }
  Parameter &muteDestination(ChannelComponent &) override {
    throw std::runtime_error("unexpected mute write");
  }
  Parameter &selection(ChannelComponent &) override {
    throw std::runtime_error("unexpected selection");
  }
  const char *
  presetType(const Presonus::Panel::PresetComponent &) const override {
    return nullptr;
  }
  void command(const char *, const char *, int) override {}

  bool loaded = false;

private:
  MixerComponentBase &mixer;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 6)
    return 2;
  const bool refresh = std::string(argv[1]) == "10";
  const bool active = argv[2][0] == '1';
  const bool initial = argv[3][0] == '1';
  const bool snapshot = argv[4][0] == '1';
  const int count = std::stoi(argv[5]);
  MixerComponentBase mixer;
  mixer.sceneRecallBlocksTag14 = initial;
  mixer.sipMuteSnapshotPending = snapshot;
  MixerServices services(mixer);
  presonus::mixer_component_port::MixerState providerState;
  providerState.panicMutes.set("mute", 1);
  MixerComponent receiver(providerState, services);
  mixer.sipMuteRestorer = &receiver;
  mixer.sipMuteSnapshot = &providerState.panicMutes;

  ParamInfo info{};
  info.minValue = 0.f;
  info.maxValue = 1.f;
  std::vector<presonus::mixer::ChannelState> state(count);
  std::vector<std::unique_ptr<ObservedSolo>> parameters;
  std::vector<std::unique_ptr<ChannelComponent>> channels;
  Core::Vector<ChannelComponent *> sipChannels;
  for (int i = 0; i < count; ++i) {
    parameters.push_back(std::make_unique<ObservedSolo>(info, mixer, i));
    state[i].solo = parameters.back().get();
    channels.push_back(std::make_unique<ChannelComponent>(
        ChannelComponent::SourcePortConstruction{}, state[i]));
    sipChannels.add(channels.back().get());
  }
  mixer.sipSoloChannels = &sipChannels;

  NumericParam masterParam(info);
  Component masterComponent;
  Presonus::DelayTimer timer(0.f);
  presonus::mixer_port::MasterBindings bindings{masterComponent, {}, timer};
  bindings.slots.fill(&masterParam);
  bindings.isSlave = [&] {
    std::cout << "master:" << mixer.sceneRecallBlocksTag14 << ':'
              << mixer.sipMuteSnapshotPending << '\n';
    return false;
  };
  bindings.isMaster = [] { return false; };
  bindings.countSolos = [](int) { return 0; };
  MasterSectionComponent master(bindings);
  mixer.soloMasterSection = &master;

  if (refresh)
    mixer.refreshSip();
  else
    mixer.activateSIP(active);
  std::cout << "flags:" << mixer.sceneRecallBlocksTag14 << ':'
            << mixer.sipMuteSnapshotPending << "\nsolos:";
  for (const auto &parameter : parameters)
    std::cout << parameter->getValue();
  std::cout << '\n';
  return services.loaded == (!refresh && !active && snapshot) &&
                 bindings.dirty == (refresh && initial)
             ? 0
             : 1;
}
