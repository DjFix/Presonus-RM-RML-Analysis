#include "presonus/mixer/PermissionsComponent.hpp"
#include "core/portable/corecomponent.h"
#include "core/portable/corefile.h"
#include "core/portable/corepersistence.h"
#include "core/portable/corestorage.h"
#include "core/system/coretime.h"
#include "presonus/LinkableComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/uc/ClientSubscription.hpp"
#include <cstdio>
#include <cstring>

namespace Presonus::Mixer {
PermissionsComponent::PermissionsComponent(PermissionsBindings &bindings)
    : bindings_(bindings) {}
PermissionsComponent::~PermissionsComponent() {
  // Only our explicit source-port allocation is owned. Legacy external values
  // stay borrowed. Clear the public projection before actual member cleanup.
  if (selected_ && bindings_.selectedSnapshot == selected_.get())
    bindings_.selectedSnapshot = nullptr;
}
void PermissionsComponent::portableOwnSelected(
    const UC::ClientSubscription *values) {
  auto replacement =
      values ? std::make_unique<UC::ClientSubscription>(
                   UC::ClientSubscription::SourcePortValues{},
                   values->sourcePortApp(), values->sourcePortDevice(),
                   values->sourcePortDisplay())
             : nullptr;
  selected_ = std::move(replacement);
  bindings_.selectedSnapshot = selected_.get();
}
void PermissionsComponent::portableAppendDevice(
    const UC::ClientSubscription *device) {
  devices_.add(device);
}
unsigned char *PermissionsComponent::exportClient() {
  // Native initializes only the first 12 bytes before copying 75. Sanitizing
  // the uninitialized suffix is an intentional source-port adaptation.
  exported_.fill(0);
  Core::CStringBuffer<128> mix;
  getMixString(mix);
  if (std::strcmp(mix.str(), "None") != 0 && !mix.isEmpty()) {
    if (std::strcmp(mix.str(), "FOH") == 0)
      exported_[0] = 1;
    else {
      exported_[0] = 2;
      if (std::strcmp(mix.str(), "All Auxes") == 0) {
        for (int i = 3; i < 7; ++i)
          exported_[i] = 255;
      } else if (std::strstr(mix.str(), "Aux ") == mix.str()) {
        mix.subString(mix, 4);
        Core::CStringBuffer<128> second;
        if (const auto *slash = std::strstr(mix.str(), "/")) {
          const auto index = static_cast<int>(slash - mix.str());
          mix.subString(second, index + 1);
          if (index < mix.length())
            mix.getBuffer()[index] = 0;
          second.subString(second, 4);
        }
        auto add = [&](const char *text) {
          long long number = 0;
          if (std::sscanf(text, "%lld", &number) == 1 && number >= 1 &&
              number <= 32) {
            auto bit = static_cast<unsigned>(number - 1);
            exported_[3 + bit / 8] |=
                static_cast<unsigned char>(1u << (bit % 8));
          }
        };
        add(mix.str());
        add(second.str());
      }
    }
  }
  Core::CStringBuffer<128> other;
  getOtherString(other);
  if (std::strcmp(other.str(), "Ch Rename") == 0)
    exported_[1] = 1;
  else if (std::strcmp(other.str(), "Wheel Only") == 0)
    exported_[2] = 1;
  return exported_.data();
}

void PermissionsComponent::updateOtherPermissionsStrings() {
  auto &list = *bindings_.otherList;
  list.removeAll();
  const auto app = getSelectedDeviceApp();
  if (app == 1 || app == 2) {
    list.appendString("None");
    list.appendString(app == 1 ? "Wheel Only" : "Ch Rename");
  } else {
    list.appendString("");
  }
  list.setValue(0.f, false);
}

void PermissionsComponent::updateMixPermissionsStrings() {
  auto *list = bindings_.mixList;
  if (!list)
    return;
  const auto oldMax = list->getMax();
  list->removeAll();
  const auto app = getSelectedDeviceApp();
  if (app == 0) {
    list->appendString("");
    list->setValue(0.f, false);
    return;
  }
  if (app == 2)
    list->appendString("None");
  if (app == 1 || app == 2) {
    list->appendString(app == 1 ? "None" : "FOH");
    list->appendString("All Auxes");
  }
  // Native captures the initial count but bounds-checks the current vector on
  // each iteration. Linked entries consume two positions, including a missing
  // following slot. Numeric identity comes from the projected channel, not i.
  const auto count = bindings_.mixer->mixChannels.count();
  for (int i = 0; i < count; ++i) {
    if (i >= bindings_.mixer->mixChannels.count())
      continue;
    auto *channel = bindings_.mixer->mixChannels[i];
    if (!channel)
      continue;
    const auto aux = bindings_.auxView(channel);
    Core::CStringBuffer<128> text;
    const auto first = aux.number + 1u;
    if (aux.link->isLinked()) {
      text.appendFormat("%s%d%s%d", "Aux ", static_cast<std::int32_t>(first),
                        "/", static_cast<std::int32_t>(first + 1u));
      ++i;
    } else {
      text.appendFormat("%s%d", "Aux ", static_cast<std::int32_t>(first));
    }
    list->appendString(text.str());
  }
  if (oldMax != list->getMax())
    bindings_.dirty = 1;
  list->setValue(0.f, false);
}

void PermissionsComponent::loadSelectedDevice() {
  if (getSelectedDeviceApp() == 0)
    return;
  bindings_.loading = 1;
  updateMixPermissionsStrings();
  syncMixStrings();
  updateOtherPermissionsStrings();
  Core::Portable::Attributes attributes(
      Core::Portable::AttributeAllocator::getDefault());
  Core::Portable::FileName filename;
  getSelectedFileName(filename);
  if (filename.isEmpty() ||
      !Core::Portable::ArchiveUtils::loadFromFile(attributes, filename.str())) {
    if (!bindings_.defaultPermissions) {
      bindings_.loading = 0;
      return;
    }
    const auto app = getSelectedDeviceApp();
    if (app == 1) {
      bindings_.mixList->fromString("All Auxes", false);
      bindings_.otherList->fromString("None", false);
    } else if (app == 2) {
      bindings_.mixList->fromString("FOH", false);
      bindings_.otherList->fromString("Ch Rename", false);
    }
    syncMixStrings();
  } else {
    auto *savedMix = bindings_.accessCodeParameters->getParameterByTag(2);
    savedMix->resetValue(false);
    Core::Portable::InputStorage storage(attributes);
    bindings_.accessCodeParameters->load(storage);
    Core::CStringBuffer<128> text;
    savedMix->toString(text.getBuffer(), 128);
    const int max = static_cast<int>(bindings_.mixList->getMax());
    for (int i = 0; i <= max; ++i) {
      Core::CStringBuffer<128> entry;
      bindings_.mixList->getStringForValue(entry.getBuffer(), 128, i);
      if (std::strcmp(entry.str(), text.str()) == 0) {
        bindings_.mixList->setValue(static_cast<float>(i), false);
        break;
      }
    }
  }
  bindings_.loading = 0;
}

int PermissionsComponent::getAppType(
    const UC::ClientSubscription &client) const {
  const char *app = client.sourcePortApp().str();
  if (std::strstr(app, "qmix"))
    return 1;
  if (std::strstr(app, "ucapp") || std::strstr(app, "ucremoteapp"))
    return 2;
  return 0;
}
int PermissionsComponent::getSelectedDeviceApp() const {
  return bindings_.selectedSnapshot ? getAppType(*bindings_.selectedSnapshot)
                                    : 0;
}
int PermissionsComponent::getSelectedDeviceType() const {
  if (!bindings_.selectedSnapshot)
    return 0;
  const char *device = bindings_.selectedSnapshot->sourcePortDevice().str();
  if (std::strstr(device, "iPhone"))
    return 1;
  if (std::strstr(device, "iPod"))
    return 2;
  if (std::strstr(device, "iPad"))
    return 3;
  return 0;
}
Core::CStringBuffer<64> PermissionsComponent::createClientInfo(
    const UC::ClientSubscription *client) const {
  Core::CStringBuffer<64> result;
  // Copy the entire observed display value, preserving bytes past its NUL.
  std::memcpy(result.getBuffer(), client->sourcePortDisplay().str(), 64);
  if (std::strlen(result.str()) > 16)
    result.getBuffer()[16] = 0;
  std::strncat(result.getBuffer(), ": ", 2);
  result.getBuffer()[63] = 0;
  const char *device = client->sourcePortDevice().str();
  const auto length = std::strlen(device);
  if (length > 0) {
    const auto available = 63 - std::strlen(result.str());
    if (available > 0) {
      std::strncat(result.getBuffer(), device,
                   length < available ? length : available);
      result.getBuffer()[63] = 0;
    }
  }
  return result;
}
const UC::ClientSubscription *PermissionsComponent::getSelectedDevice() const {
  return bindings_.selectedSnapshot;
}
void PermissionsComponent::syncMixStrings() {
  auto *parameter = bindings_.accessCodeParameters->getParameterByTag(2);
  if (parameter && bindings_.mix->getValue() >= 0.f) {
    Core::CStringBuffer<128> text;
    bindings_.mix->toString(text.getBuffer(), 128);
    parameter->fromString(text.str(), false);
  }
}
void PermissionsComponent::portableIdleAt(std::int64_t scheduleMilliseconds,
                                          std::int64_t comparisonMilliseconds) {
  if (bindings_.dirty) {
    bindings_.dirty = 0;
    bindings_.mix->changed();
    bindings_.other->changed();
    // Unsigned addition preserves native two-word wrap without signed UB.
    bindings_.deadlineMilliseconds = static_cast<std::int64_t>(
        static_cast<std::uint64_t>(scheduleMilliseconds) + 3000u);
  }
  compareDeadlineAt(comparisonMilliseconds);
}
void PermissionsComponent::compareDeadlineAt(
    std::int64_t comparisonMilliseconds) {
  if (bindings_.deadlineMilliseconds != 0 &&
      bindings_.deadlineMilliseconds > comparisonMilliseconds) {
    bindings_.deadlineMilliseconds = 0;
    bindings_.mix->rangeChanged();
    bindings_.other->rangeChanged();
  }
}
void PermissionsComponent::onIdle() {
  if (bindings_.dirty) {
    bindings_.dirty = 0;
    bindings_.mix->changed();
    bindings_.other->changed();
    bindings_.deadlineMilliseconds = static_cast<std::int64_t>(
        static_cast<std::uint64_t>(Core::SystemClock::getMilliseconds()) +
        3000u);
  }
  if (bindings_.deadlineMilliseconds)
    compareDeadlineAt(Core::SystemClock::getMilliseconds());
}
void PermissionsComponent::getFileName(
    Core::Portable::FileName &fileName,
    const Core::CStringBuffer<64> &name) const {
  fileName = "";
  if (name.isEmpty())
    return;
  fileName = bindings_.mixer->getDataDir("permissions");
  fileName.descend(name.str());
  fileName.append(".perms");
}
void PermissionsComponent::loadAccessCode() {
  auto *parameter = bindings_.accessCodeParameters->getParameterByTag(4);
  if (!parameter)
    return;
  auto *code = Core::Portable::StringParam::cast(parameter);
  Core::Portable::Attributes attributes(
      Core::Portable::AttributeAllocator::getDefault());
  Core::Portable::FileName filename;
  getAccessCodeFileName(filename);
  if (Core::Portable::ArchiveUtils::loadFromFile(attributes, filename.str())) {
    if (auto *value = attributes.lookup(parameter->getName())) {
      parameter->fromString(value->getString(), false);
      if (!code->getText().isEmpty())
        return;
    }
  }
  parameter->resetValue(false);
}
void PermissionsComponent::saveSelectedDevice() const {
  if (!bindings_.selectedSnapshot)
    return;
  Core::Portable::Attributes attributes(
      Core::Portable::AttributeAllocator::getDefault());
  Core::Portable::AttributesBuilder builder(attributes);
  Core::Portable::OutputStorage storage(builder);
  bindings_.accessCodeParameters->save(storage);
  Core::Portable::FileName filename;
  getSelectedFileName(filename);
  Core::Portable::ArchiveUtils::saveInBackground(filename.str(), attributes);
}
void PermissionsComponent::getSelectedFileName(
    Core::Portable::FileName &fileName) const {
  if (bindings_.selectedName)
    getFileName(fileName, *bindings_.selectedName);
}

void PermissionsComponent::getMixString(
    Core::CStringBuffer<128> &string) const {
  bindings_.mix->toString(string.getBuffer(), 128);
}

void PermissionsComponent::getOtherString(
    Core::CStringBuffer<128> &string) const {
  bindings_.other->toString(string.getBuffer(), 128);
}

void PermissionsComponent::auxLinkingChanged() {
  bindings_.loadSelectedDevice(bindings_.context, *this);
  bindings_.devicePermissionsChanged(bindings_.ownerContext, *this);
  bindings_.dirty = 1;
}

void PermissionsComponent::setFullPermissions(bool enabled) {
  if (enabled && bindings_.restricted == 0)
    bindings_.mix->fromString("FOH", false);
}
void PermissionsComponent::resetPermissionsPW() {
  bindings_.accessCodeParameters->getParameterByTag(4)->resetValue(false);
  saveAccessCode();
}
void PermissionsComponent::getAccessCodeFileName(
    Core::Portable::FileName &filename) const {
  filename = bindings_.mixer->getDataDir("permissions");
  filename.descend("access");
  filename.append(".code");
}
void PermissionsComponent::saveAccessCode() const {
  auto *parameter = bindings_.accessCodeParameters->getParameterByTag(4);
  if (!parameter)
    return;
  auto *code = Core::Portable::StringParam::cast(parameter);
  Core::Portable::Attributes attributes(
      Core::Portable::AttributeAllocator::getDefault());
  attributes.set(parameter->getName(), code->getText().str());
  Core::Portable::FileName filename;
  getAccessCodeFileName(filename);
  Core::Portable::ArchiveUtils::saveInBackground(filename.str(), attributes);
}
} // namespace Presonus::Mixer
