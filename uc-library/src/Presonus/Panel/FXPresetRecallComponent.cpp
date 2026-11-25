#include "presonus/panel/FXPresetRecallComponent.hpp"
#include "core/portable/corefile.h"
#include "core/portable/corepersistence.h"
#include "core/portable/corestorage.h"
#include "presonus/mixer/FXComponent.hpp"
#include "presonus/mixer/FxPresetFilter.hpp"
namespace Presonus::Panel {
namespace {
// RM 13731 table 0x31a914 / 0x31a938; labels independently observed
// through the bound original updateFxName instruction stream.
constexpr const char *reverbTypes[] = {
    "AMBIENCE",  "SMALL ROOM", "BRIGHT ROOM", "SMALL HALL", "BRIGHT HALL",
    "WARM HALL", "GATED HALL", "LARGE HALL",  "PLATE"};
constexpr const char *delayTypes[] = {"MONO DELAY", "FILTER DELAY",
                                      "STEREO DELAY", "PINGPONG DLY"};
} // namespace

FXPresetRecallComponent::FXPresetRecallComponent(
    presonus::fx_preset_recall_port::FxRecallServices &services,
    Core::Portable::Parameter &slot, Core::Portable::Parameter &loaded,
    Core::Portable::Parameter &typeName, Core::Portable::Parameter &presetName,
    Core::Portable::Parameter &type, const char *category, int effectSlot)
    : services(services), slot(slot), loaded(loaded), typeName(typeName),
      presetName(presetName), type(type), category(category),
      effectSlot(effectSlot) {}
void FXPresetRecallComponent::onIdle() { Core::Portable::Component::onIdle(); }
int FXPresetRecallComponent::getSlotNum() const {
  return static_cast<int>(slot.getValue());
}
void FXPresetRecallComponent::cacheUpdated(PresetNameCache &) {}
void FXPresetRecallComponent::cacheUpdated(PresetNameCache &, int index,
                                           const char *name, const char *) {
  if (index != getSlotNum())
    return;
  presetName.fromString(name, false);
  updateFxName();
}
bool FXPresetRecallComponent::isSlotEmpty(unsigned int index) const {
  Core::Portable::FileName path;
  getFileName(index, path);
  return !Core::Portable::FileUtils::fileExists(path);
}
bool FXPresetRecallComponent::isChildParameter(
    const Core::Portable::Parameter &parameter) const {
  for (int i = 0; i < countParameters(); ++i)
    if (getParameterAt(i) == &parameter)
      return true;
  return false;
}
void FXPresetRecallComponent::paramChanged(Core::Portable::Parameter *parameter,
                                           int message) {
  switch (message) {
  case 2:
    if (parameter == &slot)
      updateFxName();
    break;
  case 3:
    if (parameter == &loaded)
      slot.setValue(parameter->getValue(), true);
    if (parameter == &type)
      updateFxName();
    break;
  case 5:
    parameter->removeObserver(this);
    break;
  default:
    break;
  }
}
bool FXPresetRecallComponent::getFileName(
    unsigned int index, Core::Portable::FileName &path) const {
  path = services.presetPath(index, category);
  return true;
}
void FXPresetRecallComponent::getFxName(Core::Portable::Parameter &parameter,
                                        unsigned int index) const {
  Core::CString64 name;
  services.presetInfo(name.getBuffer(), 64, index, category);
  parameter.fromString(name, false);
}
void FXPresetRecallComponent::init() {
  if (auto *cache = services.lookupCache(category))
    if (!cache->delegates.contains(this))
      cache->delegates.add(this);
  updateFxName();
}
bool FXPresetRecallComponent::recallFxPreset() {
  auto *effect =
      effectRoster && effectSlot >= 0 && effectSlot < effectRoster->count()
          ? effectRoster->at(effectSlot)
          : nullptr;
  const auto index = static_cast<unsigned int>(getSlotNum());
  if (isSlotEmpty(index))
    return false;

  Core::Portable::Attributes attributes(
      Core::Portable::AttributeAllocator::getDefault());
  Core::Portable::FileName filename;
  getFileName(index, filename);
  if (!Core::Portable::ArchiveUtils::loadFromFile(attributes, filename))
    return false;

  static const Mixer::FxPresetFilter filter;
  const Core::Portable::InputStorage storage(attributes, &filter);
  if (!effect || !effect->load(storage))
    return false;

  loaded.setValue(slot.getValue(), false);
  updateFxName();
  return true;
}

void FXPresetRecallComponent::updateFxName() {
  getFxName(presetName, static_cast<unsigned int>(getSlotNum()));
  const unsigned int index = static_cast<unsigned int>(getSlotNum());
  if (static_cast<float>(index) == loaded.getValue())
    typeName.fromString((effectSlot > 1
                             ? delayTypes
                             : reverbTypes)[static_cast<int>(type.getValue())],
                        false);
  else if (isSlotEmpty(static_cast<unsigned int>(getSlotNum())))
    typeName.fromString("", false);
  else
    typeName.fromString("(Recall)", false);
}
} // namespace Presonus::Panel
