#include "presonus/mixer/AutoFilterGroupManager.hpp"
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>

namespace {
using namespace Presonus::Mixer;
using namespace Core::Portable;

struct ProbeParameter : NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
  void emitChange() { signal(Parameter::kChanged); }
};

struct TestChannel : ChannelComponent {
  using ChannelComponent::ChannelComponent;
  ProbeParameter *attach(const ParamInfo &info) {
    auto parameter = std::make_unique<ProbeParameter>(info);
    paramList.add(parameter.get());
    return parameter.release();
  }
};

constexpr char name[] = "Offline group roster";

std::string exercise(unsigned count, unsigned warm) {
  ParamInfo info{};
  info.tag = 25;
  info.type = ParamInfo::kFloat;
  info.maxValue = 1;
  const ChannelComponent::SourcePortConstruction construction;
  std::array<TestChannel, 3> channels{TestChannel(construction),
                                      TestChannel(construction),
                                      TestChannel(construction)};
  std::array<ProbeParameter *, 3> params{channels[0].attach(info),
                                         channels[1].attach(info),
                                         channels[2].attach(info)};
  Core::Vector<ChannelComponent *> roster;
  for (unsigned i = 0; i < count; ++i)
    if (!roster.add(&channels[i]))
      throw std::bad_alloc();
  MixerComponentBase mixer;
  mixer.sipSoloChannels = &roster;

  if (warm) {
    AutoFilterGroupManager first(name, mixer);
    if (first.portableOwnedComponents().count() != static_cast<int>(count))
      throw std::logic_error("warm fixture failed");
  }
  std::ostringstream observations;
  {
    AutoFilterGroupManager manager(name, mixer);
    const auto &owners = manager.portableOwnedComponents();
    auto &queue = manager.portableUpdateChannels();
    if (std::strcmp(manager.getName(), name) != 0 || queue.count() != 0 ||
        owners.count() != static_cast<int>(count))
      throw std::logic_error("constructor state mismatch");
    observations << owners.count();
    for (unsigned i = 0; i < params.size(); ++i)
      if (params[i]->observers() != (i < count ? 1 : 0))
        throw std::logic_error("registration mismatch");
    for (unsigned i = 0; i < count; ++i) {
      owners.at(i)->paramChanged(params[i], Parameter::kChanged);
      const auto *observedChannel = queue.at(static_cast<int>(i));
      unsigned selected = 0;
      while (selected < channels.size() &&
             observedChannel != &channels[selected])
        ++selected;
      observations << ' ' << selected;
    }
    for (unsigned i = 0; i < count; ++i) {
      params[i]->emitChange();
      if (queue.at(static_cast<int>(count + i)) != &channels[i])
        throw std::logic_error("pinned parameter dispatch mismatch");
    }
  }
  for (const auto *param : params)
    if (param->observers() != 0)
      throw std::logic_error("observer escaped manager lifetime");
  AutoFilterGroupManager legacy(
      AutoFilterGroupManager::SourcePortConstruction{});
  if (!legacy.portableOwnedComponents().isEmpty() ||
      !legacy.portableUpdateChannels().isEmpty())
    throw std::logic_error("legacy constructor altered");

  Core::Vector<ChannelComponent *> invalid;
  if (!invalid.add(&channels[0]) || !invalid.add(nullptr))
    throw std::bad_alloc();
  mixer.sipSoloChannels = &invalid;
  bool failed = false;
  try {
    AutoFilterGroupManager rejected(name, mixer);
  } catch (const std::invalid_argument &) {
    failed = true;
  }
  if (!failed || params[0]->observers())
    throw std::logic_error("partial construction retained an observer");
  return observations.str();
}
} // namespace

int main() {
  unsigned count = 0, warm = 0;
  while (std::cin >> count >> warm) {
    if (count > 3 || (warm != 0 && warm != 9))
      return 1;
    std::cout << exercise(count, warm) << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
