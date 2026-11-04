#include "presonus/StormMixSceneComponent.hpp"
#include "presonus/StormMuteGroupComponent.hpp"
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/panel/MixerLCD.hpp"
#include "presonus/panel/StormFrontPanelComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <vector>
struct Recall final : presonus::scene_port::Recall {
  bool recall(unsigned) const override {
    throw std::runtime_error("unused scene provider");
  }
};
struct MuteServices final : presonus::storm_mute_port::Services {
  void refreshSip() override {
    throw std::runtime_error("unused mute provider");
  }
  void activate(unsigned) override {
    throw std::runtime_error("unused mute provider");
  }
  Core::Portable::Component *connectedClient() override {
    throw std::runtime_error("unused mute provider");
  }
  void muteGroupStored(int) override {
    throw std::runtime_error("unused mute provider");
  }
  bool load(presonus::storm_mute_port::Group &) override {
    throw std::runtime_error("unused mute provider");
  }
};
struct ChannelServices final : presonus::mixer::ChannelApplicationServices {
  bool isLinked(const Presonus::Mixer::ChannelComponent &) const override {
    throw std::runtime_error("unused channel boundary");
  }
  void removeLink(Presonus::Mixer::ChannelComponent &) override {
    throw std::runtime_error("unused channel boundary");
  }
  Presonus::Mixer::ChannelComponent *
  linkablePair(Presonus::Mixer::ChannelComponent &) override {
    throw std::runtime_error("unused channel boundary");
  }
  void faderLocateDirty(Presonus::Mixer::ChannelComponent &) override {
    throw std::runtime_error("unused channel boundary");
  }
  void coefficientsChanged(Presonus::Mixer::ChannelComponent &, bool) override {
    throw std::runtime_error("unused channel boundary");
  }
};
using presonus::stormpanel_port::Handle;
struct Adapter final : presonus::stormpanel_port::Dependencies {
  std::vector<std::vector<long long>> events;
  struct Book final : presonus::panel::portable::Book {
    void command(unsigned) override {
      throw std::runtime_error("book command outside domain");
    }
  } book;
  presonus::panel::portable::State state{book};
  Presonus::Panel::MixerLCD lcd{state};
  Presonus::Mixer::ChannelComponent *expectedChannel = nullptr;
  int scenario;
  explicit Adapter(int scenario) : scenario(scenario) {}
  void emit(std::initializer_list<long long> e) { events.emplace_back(e); }
  void cleanup() override { emit({1, 1, 0, 0}); }
  void presetRecalled() override { emit({2, 1, 0, 0}); }
  void fatChannelUpdate() override { emit({3, 1, 0, 0}); }
  void fatMeterUpdate(Presonus::Mixer::ChannelComponent &channel) override {
    if (&channel != expectedChannel)
      throw std::runtime_error("channel forwarding mismatch");
    emit({4, 1, 1, 0});
  }
  Handle findGroup(int g) override {
    emit({5, g, 0, 0});
    return g;
  }
  Handle byTag(Handle g, int t) override {
    emit({6, static_cast<int>(g), t, 0});
    return g * 100 + t;
  }
  void setControl(Handle c, int value, int options) override {
    emit({7, static_cast<int>(c / 100), static_cast<int>(c % 100), options,
          value});
  }
  int count(Handle) override {
    const int values[] = {-1, 0, 1, 10};
    int n = values[scenario];
    emit({8, n, 0, 0});
    return n;
  }
  Handle at(Handle, int i) override {
    emit({9, i, 0, 0});
    return i;
  }
  Handle asLED(Handle c) override {
    emit({10, static_cast<int>(c), 0, 0});
    return c == 1 ? 0 : c;
  }
  int tag(Handle c) override {
    const int tags[] = {0, 1, 2, 7, 8, 3, 4, 5, 6, 9};
    return tags[c];
  }
  void setBlinkMode(Handle c, bool b) override { emit({11, tag(c), b, 0}); }
  void blinkLED(int g, std::uint32_t t, bool b) override {
    emit({12, g, t, b});
  }
  Presonus::Panel::MixerLCD *constructLCD(std::size_t size) override {
    emit({13, static_cast<long long>(size), 0, 0});
    emit({14, 1, 1, 0});
    return &lcd;
  }
  void addBook(Presonus::Panel::MixerLCD *lcd, std::uint32_t table,
               int book) override {
    if (lcd != &this->lcd)
      throw std::runtime_error("unexpected LCD fixture object");
    emit({15, table, book, 0});
  }
};
int main(int argc, char **argv) {
  if (argc != 5)
    return 2;
  int target = std::stoi(argv[1]);
  int index = std::stoi(argv[2]);
  bool flag = std::stoi(argv[3]) != 0;
  int scenario = std::stoi(argv[4]);
  (void)index;
  Adapter a(scenario);
  Presonus::Panel::StormFrontPanelComponent c(a);
  Recall recall;
  Presonus::StormMixSceneComponent scene(recall);
  MuteServices muteServices;
  presonus::storm_mute_port::State muteState(muteServices);
  Presonus::StormMuteGroupComponent muteGroup(muteState);
  presonus::mixer::ChannelState channelState;
  ChannelServices channelServices;
  Presonus::Mixer::ChannelComponent channel(channelState, channelServices);
  a.expectedChannel = &channel;
  switch (target) {
  case 2:
    c.mixSceneRecalled(scene);
    break;
  case 3:
    c.mixSceneEnterStoreState(scene);
    break;
  case 4:
    c.mixSceneExitStoreState(scene);
    break;
  case 9:
    c.doFatMeterUpdate(channel);
    break;
  case 1:
    c.cleanup();
    break;
  case 5:
    c.setMuteGroupDirty(muteGroup, index, flag);
    break;
  case 6:
    c.setAllMutesGroupDirty(muteGroup, flag);
    break;
  case 7:
    c.doFatChannelUpdate();
    break;
  case 8:
    if (c.createLCD() != &a.lcd)
      throw std::runtime_error("LCD identity mismatch");
    a.emit({16, 1, 0, 0});
    break;
  case 10:
    c.blinkSceneButtons(flag);
    break;
  default:
    return 3;
  }
  std::cout << '[';
  for (std::size_t i = 0; i < a.events.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << '[';
    for (std::size_t j = 0; j < a.events[i].size(); ++j) {
      if (j)
        std::cout << ',';
      std::cout << a.events[i][j];
    }
    std::cout << ']';
  }
  std::cout << "]\n";
}
