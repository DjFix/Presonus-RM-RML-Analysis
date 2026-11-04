#include "presonus/mixer/FXBusComponent.hpp"
#include "presonus/mixer/GEQLinkHandler.hpp"
#include "presonus/mixer/GlobalComponent.hpp"
#include "presonus/mixer/RackMixerComponent.hpp"
#include "presonus/mixer/SendOutputComponent.hpp"
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
void state(const presonus::send_output_port::SendState &s) {
  std::cout << s.sendChanged << ' ' << s.output.outputCoeffChanged << ' '
            << s.childChanged << ' ' << s.fxChanged << ' '
            << s.output.updatePending << ' ';
}
int main(int argc, char **argv) {
  if (argc == 3 && std::string(argv[1]) == "path") {
    namespace fs = std::filesystem;
    fs::path root(argv[2]);
    fs::create_directories(root);
    for (const char *device : {"rack", "", "rack/child"}) {
      Presonus::Mixer::MixerComponentBase mixer;
      mixer.applicationDataRoot = root.c_str();
      mixer.deviceDataFolder = device;
      Presonus::Mixer::GlobalComponent global;
      global.bindMixer(mixer);
      auto observed = global.getTempFilePath();
      auto provider = mixer.getDataDir("temp");
      provider.descend("mixer.scene");
      if (std::string(observed.str()) != provider.str())
        return 3;
      auto parent = fs::path(observed.str()).parent_path();
      if (!fs::is_directory(parent) || fs::exists(observed.str()))
        return 4;
      std::cout << std::quoted(device) << ' ' << std::quoted(observed.str())
                << '\n';
    }
    Presonus::Mixer::GlobalComponent unbound;
    try {
      unbound.getTempFilePath();
      return 5;
    } catch (const std::logic_error &) {
    }
    return 0;
  }
  int target, tag, message, count, dirty, mutate;
  std::uint32_t initial;
  while (std::cin >> target >> tag >> message >> count >> initial >> dirty >>
         mutate) {
    presonus::mixer::ChannelState channel;
    presonus::output_port::Bindings output{channel, {}, {}, false,
                                           0,       0,  {}, {}};
    output.outputCoeffChanged = initial;
    output.updatePending = dirty;
    presonus::send_output_port::SendState own{output, initial, initial};
    std::vector<presonus::mixer::ChannelState> channels(count);
    std::vector<std::unique_ptr<presonus::output_port::Bindings>> childBindings;
    std::vector<std::unique_ptr<presonus::send_output_port::SendState>>
        childStates;
    std::vector<presonus::send_output_port::SendState *> children;
    for (int i = 0; i < count; ++i) {
      auto b = std::make_unique<presonus::output_port::Bindings>(
          presonus::output_port::Bindings{
              channels[i], {}, {}, false, 0, 0, {}, {}});
      b->outputCoeffChanged = initial;
      b->updatePending = dirty;
      auto s = std::make_unique<presonus::send_output_port::SendState>(
          presonus::send_output_port::SendState{*b, initial, initial});
      s->fxChanged = initial;
      children.push_back(s.get());
      childStates.push_back(std::move(s));
      childBindings.push_back(std::move(b));
    }
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kInt;
    info.tag = tag;
    Core::Portable::NumericParam parameter(info);
    own.fxChanged = initial;
    int calls = 0, observedTag = 0, observedMessage = 0;
    std::vector<std::uint32_t> observedStates;
    output.channelParamChanged = [&](Core::Portable::Parameter *p, int msg) {
      if (p != &parameter)
        throw 1;
      auto capture = [&](const auto &s) {
        observedStates.push_back(s.sendChanged);
        observedStates.push_back(s.output.outputCoeffChanged);
        observedStates.push_back(s.childChanged);
        observedStates.push_back(s.fxChanged);
        observedStates.push_back(s.output.updatePending);
      };
      capture(own);
      for (auto *child : children)
        capture(*child);
      ++calls;
      observedTag = p->getTag();
      observedMessage = msg;
      if (mutate) {
        info.tag = mutate == 1 ? 410 : 14;
        own.sendChanged = own.childChanged = 9;
        output.outputCoeffChanged = 9;
        output.updatePending = false;
      }
    };
    Presonus::Mixer::OutputComponent base(output);
    if (target == 30) {
      base.paramChanged(&parameter, message);
    } else if (target == 20) {
      Presonus::Mixer::SendOutputComponent send(base, own, children);
      send.paramChanged(&parameter, message);
    } else {
      Presonus::Mixer::FXBusComponent send(base, own, children);
      send.paramChanged(&parameter, message);
    }
    state(own);
    for (auto *child : children)
      state(*child);
    std::cout << calls << ' ' << observedTag << ' ' << observedMessage;
    for (auto value : observedStates)
      std::cout << ' ' << value;
    std::cout << '\n';
  }
}
