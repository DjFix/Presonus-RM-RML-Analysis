#include "presonus/mixer/PermissionsComponent.hpp"
#include "core/portable/corecomponent.h"
#include "core/portable/corefile.h"
#include "core/portable/corepersistence.h"
#include "core/portable/corestorage.h"
#include "core/system/coretime.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/uc/ClientSubscription.hpp"
#include <cstring>

namespace Presonus::Mixer {
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
  if (parameter && bindings_.mix->getValue() != 0.f) {
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
