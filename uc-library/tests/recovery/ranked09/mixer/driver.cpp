#include "presonus/mixer/OutputComponent.hpp"
#include "presonus/trial08/MixerComponentBase.hpp"
#include <cstring>
#include <iostream>
#include <string>
// Test-only opaque identity objects; production needs no Delegate definition.
class Presonus::Mixer::MixerComponentBase::Delegate {};
// Test-only opaque token; property state is resolved through the required
// binding.
class Presonus::Dsp::MultiParamProperty {};
int main() {
  using Mixer = Presonus::Mixer::MixerComponentBase;
  int count, target, sentinel;
  std::string mode;
  while (std::cin >> mode) {
    if (mode == "missing") {
      Mixer state;
      try {
        state.getLinkableChannelPair(nullptr);
        return 3;
      } catch (const std::logic_error &) {
        std::cout << "missing-binding-threw\n";
      }
      continue;
    }
    if (mode == "pair") {
      Mixer state;
      int type, index, inputs, mixes, error;
      std::cin >> type >> index >> inputs >> mixes >> error;
      // Opaque pointer identities only; no Channel object dereference occurs.
      alignas(16) unsigned char tokens[8][16]{};
      auto token = [&](int i) -> Presonus::Mixer::ChannelComponent * {
        return i == -1 ? nullptr
                       : reinterpret_cast<Presonus::Mixer::ChannelComponent *>(
                             &tokens[i]);
      };
      for (int i = 0; i < inputs; ++i)
        state.inputChannels.add(token(i));
      for (int i = 0; i < mixes; ++i)
        state.mixChannels.add(token(i + 4));
      Core::ConstVector<Presonus::Mixer::ChannelComponent *>::getError() =
          token(error);
      int queries = 0;
      state.channelIdentity = [&](Presonus::Mixer::ChannelComponent *p) {
        if (p != token(7))
          throw std::runtime_error("channel query identity");
        ++queries;
        return std::pair<std::int32_t, std::int32_t>{type, index};
      };
      auto result = state.getLinkableChannelPair(token(7));
      int decoded = -1;
      for (int i = 0; i < 8; ++i)
        if (result == token(i))
          decoded = i;
      std::cout << decoded << ' ' << queries << '\n';
      continue;
    }
    if (mode == "solo") {
      presonus::mixer::ChannelState channel;
      presonus::input_port::Property property;
      presonus::output_port::Bindings binding{channel};
      std::uint32_t bits;
      for (auto &v : channel.soloCoefficients) {
        std::cin >> bits;
        std::memcpy(&v, &bits, 4);
      }
      for (auto &v : binding.cachedSolo) {
        std::cin >> bits;
        std::memcpy(&v, &bits, 4);
      }
      std::cin >> property.count;
      for (auto &entry : property.entries)
        entry = {-7, 0x12345678};
      Presonus::Dsp::MultiParamProperty token;
      binding.resolveProperty = [&](Presonus::Dsp::MultiParamProperty &value)
          -> presonus::input_port::Property & {
        if (&value != &token)
          throw std::runtime_error("opaque property identity");
        return property;
      };
      Presonus::Mixer::OutputComponent output(binding);
      output.soloUpdate(token);
      std::cout << property.count;
      for (float value : binding.cachedSolo) {
        std::memcpy(&bits, &value, 4);
        std::cout << ' ' << bits;
      }
      for (const auto &entry : property.entries)
        std::cout << ' ' << entry.tag << ' ' << entry.value;
      std::cout << '\n';
      continue;
    }
    if (mode != "delegate")
      return 2;
    std::cin >> count >> target >> sentinel;
    Mixer state;
    Mixer::Delegate identities[8];
    int value;
    for (int i = 0; i < count; ++i) {
      std::cin >> value;
      state.delegates.add(&identities[value]);
    }
    Core::ConstVector<Mixer::Delegate *>::getError() =
        sentinel == -1 ? nullptr : &identities[sentinel];
    state.removeDelegate(identities[target]);
    std::cout << state.delegates.count();
    // Includes the native/provider-cleared unused slot after successful
    // removal.
    for (int i = 0; i < count; ++i) {
      auto *pointer = state.delegates.getItems()[i];
      std::cout << ' ' << (pointer ? int(pointer - identities) : -1);
    }
    std::cout << '\n';
  }
}
