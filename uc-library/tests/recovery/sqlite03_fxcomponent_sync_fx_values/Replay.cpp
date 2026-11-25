#include "presonus/dsp/SLReverbController.hpp"
#include "presonus/mixer/FXComponent.hpp"
#include "presonus/mixer/ReverbComponent.hpp"
#include <bit>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
using Core::Portable::Component;
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using presonus::dsp::ReverbPortState;
using Presonus::Dsp::SLReverbController;
using Presonus::Mixer::FXComponent;
using Presonus::Mixer::ReverbComponent;

struct Entry {
  int tag;
  std::uint32_t bits;
  int mapped;
};

struct Boundary : presonus::mixer_fx::AppBoundary {
  void setControllerDirty() override { std::abort(); }
  std::uint32_t getTypeNumber() override { std::abort(); }
  void updateTypeName() override { std::abort(); }
  void handleTypeChange(bool) override { std::abort(); }
};

struct TracedType : NumericParam {
  explicit TracedType(const ParamInfo &info) : NumericParam(info) {}
  float getValue() const override {
    std::cout << "read-type\n";
    return NumericParam::getValue();
  }
};

struct TracedReverb : SLReverbController {
  explicit TracedReverb(ReverbPortState &state) : SLReverbController(state) {}
  float setValue(int index, float value) override {
    std::cout << "set " << index << ' ' << std::bit_cast<std::uint32_t>(value)
              << '\n';
    return SLReverbController::setValue(index, value);
  }
};

struct TracedFx : FXComponent {
  TracedFx(presonus::mixer_fx::State &state, int mode,
           const std::vector<Entry> &entries)
      : FXComponent(state), owner(state.parameterOwner), mode(mode),
        entries(entries) {}

  std::int32_t getEffectTypeInternal(Presonus::EffectType type) override {
    std::cout << "effect " << static_cast<std::int32_t>(type) << '\n';
    return mode == 2 ? 12 : FXComponent::getEffectTypeInternal(type);
  }

  int mapIDs(int tag) override {
    if (entries.at(index).tag != tag)
      throw std::logic_error("wrong parameter tag or iteration order");
    std::cout << "map " << tag << '\n';
    if (mode == 2)
      return entries.at(index).mapped;
    return mode == 1 ? mapping.mapIDs(tag) : FXComponent::mapIDs(tag);
  }

  float mapValues(Parameter *parameter) override {
    if (owner.getParameterAt(index) != parameter)
      throw std::logic_error("wrong value parameter");
    std::cout << "value " << index++ << '\n';
    const auto value = FXComponent::mapValues(parameter);
    return mode == 2 ? -value : value;
  }

  Component &owner;
  const int mode;
  const std::vector<Entry> &entries;
  int index = 0;
  ReverbComponent mapping{ReverbComponent::SourcePortConstruction{}};
};

ParamInfo makeInfo(int tag, std::uint32_t bits) {
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.tag = tag;
  info.minValue = -1024.f;
  info.maxValue = 1024.f;
  info.defaultValue = std::bit_cast<float>(bits);
  std::snprintf(info.name, sizeof(info.name), "parameter%d", tag);
  return info;
}

void replay(int mode, std::uint32_t typeBits,
            const std::vector<Entry> &entries) {
  const auto liveInfo = makeInfo(90, std::bit_cast<std::uint32_t>(-331.f));
  const auto recalledInfo = makeInfo(91, typeBits);
  NumericParam live(liveInfo);
  TracedType recalled(recalledInfo);
  std::vector<ParamInfo> descriptors;
  for (const auto &entry : entries)
    descriptors.push_back(makeInfo(entry.tag, entry.bits));
  Component owner("fx-parameters");
  owner.addParameters(descriptors.data(), static_cast<int>(descriptors.size()));
  ReverbPortState reverbState;
  reverbState.valueCount = [] { return 57; };
  const std::uint32_t preset = 9;
  std::memcpy(reverbState.memory.data() + 0x2c, &preset, sizeof(preset));
  TracedReverb controller(reverbState);
  Presonus::DspComponent dsp("offline-reverb", &controller);
  Boundary boundary;
  presonus::mixer_fx::LoadState load{dsp, live, live, live};
  presonus::mixer_fx::State state{owner, live, recalled, boundary};
  if (mode == 1)
    state.syncDsp = &dsp;
  if (mode == 2)
    state.load = &load;
  TracedFx fx(state, mode, entries);
  fx.syncFxValues();
  if (owner.countParameters() != static_cast<int>(entries.size()) ||
      live.getValue() != -331.f || state.dirty || state.recalledTypePending ||
      load.loading)
    throw std::logic_error("FX state changed unexpectedly");
  for (std::size_t i = 0; i < entries.size(); ++i)
    if (std::bit_cast<std::uint32_t>(owner.getParameterAt(i)->getValue()) !=
        entries[i].bits)
      throw std::logic_error("parameter value changed");
  std::cout << "state " << std::to_integer<int>(reverbState.memory[0x1c]);
  for (std::size_t offset = 0x2c; offset < 0x80;
       offset += sizeof(std::uint32_t)) {
    std::uint32_t word;
    std::memcpy(&word, reverbState.memory.data() + offset, sizeof(word));
    std::cout << ' ' << word;
  }
  std::cout << '\n';
}
} // namespace

int main() {
  int mode, count;
  std::uint32_t typeBits;
  while (std::cin >> mode >> typeBits >> count) {
    std::vector<Entry> entries;
    for (int i = 0; i < count; ++i) {
      Entry entry{};
      if (!(std::cin >> entry.tag >> entry.bits >> entry.mapped))
        return 1;
      entries.push_back(entry);
    }
    replay(mode, typeBits, entries);
  }
  return std::cin.eof() ? 0 : 1;
}
