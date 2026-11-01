#include "presonus/mixer/MasterSectionComponent.hpp"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
namespace {
using Core::Portable::ListParam;
std::string selected(ListParam &list) {
  char buffer[128]{};
  list.toString(buffer, sizeof(buffer));
  return buffer;
}
std::string numbered(const std::string &prefix, int i) {
  return prefix.substr(0, 127) + std::to_string(i);
}
} // namespace
namespace Presonus::Mixer {
void MasterSectionComponent::populateRouteList(int tag) {
  if (auto *list = ListParam::cast(b.parameters.getParameterByTag(tag)))
    b.populateRoutes(*list);
}
void MasterSectionComponent::updateControlRoom() {
  const float remote = p(0).getValue();
  const int solos = b.countSolos(-1);
  if (p(11).getValue() == 0.f && p(13).getValue() == 2.f) {
    const std::uint32_t sum =
        static_cast<std::uint32_t>(static_cast<int>(remote)) +
        static_cast<std::uint32_t>(solos);
    std::int32_t total;
    std::memcpy(&total, &sum, sizeof(total));
    if (total > 0)
      p(2).setValue(1.f, true);
    if (total == 0)
      p(1).setValue(1.f, true);
  }
  b.dirty = true;
}
void MasterSectionComponent::localSoloChanged() {
  if (b.isSlave()) {
    auto *input = b.parameters.getParameterByTag(16);
    input->setValue(
        static_cast<float>(static_cast<std::uint32_t>(b.countSolos(0))), true);
    auto *mix = b.parameters.getParameterByTag(17);
    mix->setValue(
        static_cast<float>(static_cast<std::uint32_t>(b.countSolos(4))), true);
  }
  if (b.isMaster()) {
    Presonus::UC::MessageAttributes message("CascadeSoloInfo");
    message.set(
        "InputSoloCount",
        static_cast<Core::int64>(static_cast<std::uint32_t>(b.countSolos(0))));
    message.set(
        "MixSoloCount",
        static_cast<Core::int64>(static_cast<std::uint32_t>(b.countSolos(4))));
    b.sendSolo(message, 0x4a4d, b.slaveID());
  }
  updateControlRoom();
}
void MasterSectionComponent::remoteSoloChanged(int inputs, int mixes,
                                               int other) {
  if (p(13).getValue() != 1.f || b.solosBlocked())
    return;
  const bool active = mixes != 0 || (b.isSubgroupMerge() && other != 0);
  if (inputs > 0)
    b.clearSolos();
  else if (active)
    b.clearSIPSolos();
}
void MasterSectionComponent::buildRemoteMonitorSelectList() {
  auto *list = ListParam::cast(b.parameters.getParameterByTag(26));
  if (!list)
    return;
  list->removeAll();
  for (const char *s : {"Main", "Solo", "Mono", "Digital", "Tape"})
    list->appendString(s);
  for (std::size_t i = 0; i < b.channels.size(); ++i)
    if (b.channels[i].present)
      list->appendString(
          numbered(b.labels[0], static_cast<int>(i + 1)).c_str());
  list->rangeChanged();
}
void MasterSectionComponent::rebuildMonitorSelectList() {
  auto *list = ListParam::cast(b.parameters.getParameterByTag(25));
  if (!list)
    return;
  const auto previous =
      list->getValue() >= 0.f ? selected(*list) : std::string();
  list->removeAll();
  for (int i : {3, 1, 2, 4})
    list->appendString(b.labels[i].c_str());
  for (std::size_t i = 0; i < b.channels.size();) {
    const auto channel = b.channels[i];
    if (!channel.present) {
      ++i;
      continue;
    }
    auto label = numbered(b.labels[0], static_cast<int>(i + 1));
    if (channel.linked && channel.linked->getValue() > 0.f) {
      label += b.pairSeparator.substr(
          0, 127 - std::min<std::size_t>(127, label.size()));
      label += std::to_string(i + 2);
      i += 2;
    } else
      ++i;
    list->appendString(label.c_str());
  }
  list->fromString(previous.c_str(), true);
  if (list->getValue() < 0.f)
    list->setValue(0.f, true);
  list->rangeChanged();
}
void MasterSectionComponent::onMonitorSelectChanged() {
  for (int i : {4, 3, 2, 5, 6})
    p(i).setValue(0.f, false);
  auto *mode = b.parameters.getParameterByTag(24);
  if (!mode || !(mode->getValue() > 0.f))
    return;
  auto *list = ListParam::cast(b.parameters.getParameterByTag(25));
  if (!list || !(list->getValue() >= 0.f))
    return;
  std::string label = selected(*list).substr(0, 31);
  if (label.rfind(b.labels[0], 0) == 0) {
    if (b.labels[0].size() < label.size())
      label.erase(0, b.labels[0].size());
    auto split = label.find(b.pairSeparator);
    const bool pair = split != std::string::npos && split > 0;
    if (pair && split < label.size())
      label.resize(split);
    long long index = 0;
    std::sscanf(label.c_str(), "%lld", &index);
    // Defined port domain: parsed channel numbers with index-1 representable.
    const float first = static_cast<float>(index - 1);
    p(14).setValue(first, false);
    p(15).setValue(pair ? static_cast<float>(index) : first, false);
    p(5).setValue(1.f, false);
  } else if (label.rfind(b.labels[2], 0) == 0)
    p(4).setValue(1.f, false);
  else if (label.rfind(b.labels[1], 0) == 0)
    p(3).setValue(1.f, false);
  else if (label.rfind(b.labels[3], 0) == 0)
    p(2).setValue(1.f, false);
  else if (label.rfind(b.labels[4], 0) == 0)
    p(6).setValue(1.f, false);
}
void MasterSectionComponent::addProperty(
    presonus::mixer_port::MasterProperty &property, int index, float value) {
  if (b.cache.at(index) == value)
    return;
  if (property.count <= 59) {
    property.entries.push_back({index, value});
    ++property.count;
  }
  b.cache.at(index) = value;
}
void MasterSectionComponent::addControlRmProperty(
    Presonus::Dsp::MultiParamProperty &property, int index, float value) {
  addProperty(b.property(property), index, value);
}
void MasterSectionComponent::doUpdates() {
  presonus::mixer_port::MasterProperty property;
  float main = p(1).getNormalized(), solo = p(2).getNormalized(),
        digital = p(3).getNormalized(), tape = p(4).getNormalized(),
        aux = p(5).getNormalized(), mono = p(6).getNormalized();
  float inherited = 0.f;
  if (main > 0.f && mono == 0.f)
    if (auto *global = b.globalComponent())
      if (auto *parameter = global->getParameterByTag(45))
        if (parameter->getValue() > 0.f)
          inherited = main;
  const auto gain = [this](int i) {
    const float value = p(i).getValue();
    return value < -144.f ? [] {
      std::uint32_t bits = 0x33877f3f;
      float value;
      std::memcpy(&value, &bits, 4);
      return value;
    }()
                          : std::pow(10.f, value * .05f);
  };
  const float g0 = gain(7), g1 = gain(8), g2 = gain(9), g3 = gain(10);
  addProperty(property, 1, main);
  addProperty(property, 2, solo * g2);
  addProperty(property, 0, digital * g3);
  addProperty(property, 3, tape * g3);
  addProperty(property, 4, aux);
  addProperty(property, 5, mono);
  addProperty(property, 6, inherited);
  addProperty(property, 7, g0);
  addProperty(property, 8, g1);
  addProperty(property, 9, p(11).getValue());
  addProperty(property, 10, p(12).getValue());
  addProperty(property, 11, p(14).getValue());
  addProperty(property, 12, p(15).getValue());
  if (property.count > 0)
    b.submitProperty(property);
}
void MasterSectionComponent::onIdle() {
  b.targetedIdle();
  if (b.timer.isLongEnoughYet())
    p(11).setValue(1.f, false);
}
} // namespace Presonus::Mixer
